from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from .auth import verify_session
from .auth import router as auth_router
from .config import settings
import uuid
from .models import CrackCreate, TaskInfo, TaskStatus, LogChunk
from .jobs import enqueue_crack, get_status, redis
from .storage import task_paths


app = FastAPI(title="CrackNum API", version="1.2.0")
origins = (
    settings.CORS_ORIGINS
    if isinstance(settings.CORS_ORIGINS, list)
    else [o.strip() for o in str(settings.CORS_ORIGINS).split(",") if o.strip()]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload", response_model=TaskInfo)
async def upload(file: UploadFile = File(...), _: str = Depends(verify_session)):
    task_id = uuid.uuid4().hex
    in_file, _, _ = task_paths(task_id)
    content = await file.read()
    in_file.write_bytes(content)
    return TaskInfo(task_id=task_id)


@app.post("/crack/{task_id}", response_model=TaskInfo)
async def crack(task_id: str, body: CrackCreate, _: str = Depends(verify_session)):
    in_file, _, _ = task_paths(task_id)
    if not in_file.exists():
        raise HTTPException(404, "task input not found; upload first")
    enqueue_crack(task_id, body.salt)
    return TaskInfo(task_id=task_id)


@app.get("/status/{task_id}", response_model=TaskStatus)
def status(task_id: str, _: str = Depends(verify_session)):
    st = get_status(task_id)
    if st.get("status") == "unknown":
        raise HTTPException(404, "task not found")
    return TaskStatus(task_id=task_id, **st)


@app.get("/logs/{task_id}", response_model=LogChunk)
def logs(task_id: str, cursor: int = 0, _: str = Depends(verify_session)):
    key = f"log:{task_id}"
    total = redis.llen(key)
    cursor = max(0, min(cursor, total))
    lines = [x.decode() for x in redis.lrange(key, cursor, -1)]
    return LogChunk(lines=lines, cursor=total)


@app.get("/download/{task_id}")
def download(task_id: str, _: str = Depends(verify_session)):
    _, out_file, _ = task_paths(task_id)
    if not out_file.exists():
        raise HTTPException(404, "result not ready")
    return FileResponse(path=str(out_file), filename=f"{task_id}.csv", media_type="text/csv")
