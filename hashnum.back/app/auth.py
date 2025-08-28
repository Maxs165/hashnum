import uuid
from typing import Optional
from fastapi import HTTPException, Header, Request, Response, APIRouter, Depends
from pydantic import BaseModel
from .config import settings
from .jobs import redis

SESSION_COOKIE = "sid"

router = APIRouter(prefix="", tags=["auth"])


class LoginForm(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    ok: bool = True
    expires_in: int


def _session_key(sid: str) -> str:
    return f"sessions:{sid}"


def _set_cookie(resp: Response, name: str, value: str, max_age: int):
    resp.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )


def _del_cookie(resp: Response, name: str):
    resp.delete_cookie(key=name, domain=settings.COOKIE_DOMAIN, path="/")


def _create_session(sub: str) -> tuple[str, int]:
    sid = uuid.uuid4().hex
    ttl = settings.SESSION_TTL_S
    redis.setex(_session_key(sid), ttl, sub)
    return sid, ttl


def _touch_session(sid: str) -> Optional[str]:
    key = _session_key(sid)
    sub = redis.get(key)
    if not sub:
        return None
    redis.expire(key, settings.SESSION_TTL_S)
    return sub.decode() if isinstance(sub, (bytes, bytearray)) else str(sub)


async def verify_session(request: Request) -> str:
    sid = request.cookies.get(SESSION_COOKIE)
    if not sid:
        raise HTTPException(status_code=401, detail="Missing session")
    sub = _touch_session(sid)
    if not sub:
        raise HTTPException(status_code=401, detail="Session expired")
    return sub


@router.post("/token", response_model=TokenResponse)
def issue_or_touch_token(
    body: Optional[LoginForm] = None,
    request: Request = None,
    response: Response = None,
):
    if body:
        if not (body.username == settings.ADMIN_USER and body.password == settings.ADMIN_PASSWORD):
            raise HTTPException(401, "Invalid credentials")
        sid, ttl = _create_session(body.username)
        _set_cookie(response, SESSION_COOKIE, sid, ttl)
        return TokenResponse(expires_in=ttl)

    sid = request.cookies.get(SESSION_COOKIE)
    if not sid:
        raise HTTPException(401, "No session")
    sub = _touch_session(sid)
    if not sub:
        raise HTTPException(401, "Session expired")
    return TokenResponse(expires_in=settings.SESSION_TTL_S)


@router.post("/logout")
def logout(response: Response, request: Request):
    sid = request.cookies.get(SESSION_COOKIE)
    if sid:
        try:
            redis.delete(_session_key(sid))
        except Exception:
            pass
    _del_cookie(response, SESSION_COOKIE)
    return {"ok": True}
