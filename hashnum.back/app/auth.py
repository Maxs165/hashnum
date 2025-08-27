import time, uuid
from typing import Optional, Tuple
from fastapi import HTTPException, Header, Request, Depends, Response, APIRouter
from pydantic import BaseModel
from jose import jwt, JWTError
from .config import settings
from .jobs import redis


def _signing_key() -> Tuple[str, str]:
    if settings.JWT_PRIVATE_KEY and settings.JWT_PUBLIC_KEY:
        return settings.JWT_PRIVATE_KEY, settings.JWT_PUBLIC_KEY
    return settings.JWT_SECRET, settings.JWT_SECRET


PRIVATE, PUBLIC = _signing_key()

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
ACCESS_TYP = "access"
REFRESH_TYP = "refresh"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def _make_jwt(sub: str, typ: str, ttl: int, extra: Optional[dict] = None) -> Tuple[str, str, int]:
    now = int(time.time())
    jti = str(uuid.uuid4())
    payload = {
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": now + ttl,
        "jti": jti,
        "sub": sub,
        "typ": typ,
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(
        payload,
        PRIVATE,
        algorithm=settings.JWT_ALG,
    )
    return token, jti, payload["exp"]


def _set_cookie(resp, name: str, value: str, max_age: int):
    kwargs = dict(
        key=name,
        value=value,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        path="/",
        secure=settings.COOKIE_SECURE,
    )
    if settings.COOKIE_DOMAIN and settings.COOKIE_DOMAIN != "localhost":
        kwargs["domain"] = settings.COOKIE_DOMAIN

    resp.set_cookie(**kwargs)


def _add_to_blocklist(jti: str, ttl: int):
    redis.setex(f"jwt:bl:{jti}", ttl, "1")


def _is_blocklisted(jti: str) -> bool:
    return redis.exists(f"jwt:bl:{jti}") == 1


def _decode_and_validate(token: str, expect_typ: Optional[str] = None) -> dict:
    try:
        payload = jwt.decode(
            token,
            PUBLIC,
            algorithms=[settings.JWT_ALG],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
        if expect_typ and payload.get("typ") != expect_typ:
            raise JWTError("invalid token typ")
        jti = payload.get("jti")
        if jti and _is_blocklisted(jti):
            raise JWTError("token revoked")
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


async def verify_jwt(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
    else:
        token = request.cookies.get(ACCESS_COOKIE)

    if not token:
        raise HTTPException(status_code=401, detail="Missing access token")

    payload = _decode_and_validate(token, expect_typ=ACCESS_TYP)
    return payload.get("sub") or ""


router = APIRouter(prefix="", tags=["auth"])


class LoginForm(BaseModel):
    username: str
    password: str


@router.post("/token", response_model=TokenResponse)
def issue_token(
    body: Optional[LoginForm] = None,
    request: Request = None,
    response: Response = None,
):
    if body:
        if not (body.username == settings.ADMIN_USER and body.password == settings.ADMIN_PASSWORD):
            raise HTTPException(401, "Invalid credentials")
        sub = body.username
        access, jti_a, exp_a = _make_jwt(sub, ACCESS_TYP, settings.ACCESS_TTL_S)
        refresh, jti_r, exp_r = _make_jwt(sub, REFRESH_TYP, settings.REFRESH_TTL_S)
        _set_cookie(response, ACCESS_COOKIE, access, settings.ACCESS_TTL_S)
        _set_cookie(response, REFRESH_COOKIE, refresh, settings.REFRESH_TTL_S)
        redis.setex(f"jwt:refresh:{sub}", settings.REFRESH_TTL_S, jti_r)
        return TokenResponse(access_token=access, expires_in=settings.ACCESS_TTL_S)

    refresh = request.cookies.get(REFRESH_COOKIE)
    if not refresh:
        raise HTTPException(401, "No refresh token")
    payload = _decode_and_validate(refresh, expect_typ=REFRESH_TYP)
    sub = payload.get("sub")
    last_jti = redis.get(f"jwt:refresh:{sub}")
    if last_jti and last_jti.decode() != payload.get("jti"):
        raise HTTPException(401, "Refresh token rotated")

    _add_to_blocklist(payload["jti"], settings.REFRESH_TTL_S)
    new_refresh, jti_r2, _ = _make_jwt(sub, REFRESH_TYP, settings.REFRESH_TTL_S)
    redis.setex(f"jwt:refresh:{sub}", settings.REFRESH_TTL_S, jti_r2)
    _set_cookie(response, REFRESH_COOKIE, new_refresh, settings.REFRESH_TTL_S)

    access, jti_a, exp_a = _make_jwt(sub, ACCESS_TYP, settings.ACCESS_TTL_S)
    _set_cookie(response, ACCESS_COOKIE, access, settings.ACCESS_TTL_S)
    return TokenResponse(access_token=access, expires_in=settings.ACCESS_TTL_S)


@router.post("/logout")
def logout(response: Response, request: Request):
    rt = request.cookies.get(REFRESH_COOKIE)
    if rt:
        try:
            payload = _decode_and_validate(rt, expect_typ=REFRESH_TYP)
            _add_to_blocklist(payload["jti"], settings.REFRESH_TTL_S)
            if payload.get("sub"):
                redis.delete(f"jwt:refresh:{payload['sub']}")
        except HTTPException:
            pass
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(name, domain=settings.COOKIE_DOMAIN, path="/")
    return {"ok": True}
