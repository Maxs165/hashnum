import os
from rq import Queue
from redis import Redis
from .runner import run_hashcat_task, RunCallbacks
from .storage import task_paths

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
RQ_NAME = os.getenv("RQ_QUEUE", "tasks")

redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
queue = Queue(RQ_NAME, connection=redis)


def _status_key(task_id: str) -> str:
    return f"crack:{task_id}"


def _append_log(task_id: str, line: str):
    _, _, log_file = task_paths(task_id)
    with log_file.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    redis.rpush(f"log:{task_id}", line)
    redis.ltrim(f"log:{task_id}", -1000, -1)


def _set_status(task_id: str, **vals):
    redis.hset(_status_key(task_id), mapping=vals)


def _get_status(task_id: str) -> dict:
    raw = redis.hgetall(_status_key(task_id))
    return {
        k.decode(): (v.decode() if isinstance(v, (bytes, bytearray)) else v) for k, v in raw.items()
    }


def crack_job(task_id: str, salt: str):
    _set_status(task_id, status="started", progress=0, cracked=0, total=0)
    in_file, out_file, _ = task_paths(task_id)

    def on_log(s: str):
        _append_log(task_id, s)

    def on_progress(p: float, cracked: int, total: int):
        _set_status(task_id, progress=p, cracked=cracked, total=total)

    cb = RunCallbacks(on_log=on_log, on_progress=on_progress)

    try:
        run_hashcat_task(in_file, salt, out_file, cb)
        _set_status(task_id, status="finished")
    except Exception as e:
        _append_log(task_id, f"❌ Ошибка: {e}")
        _set_status(task_id, status="failed", message=str(e))
        raise


def enqueue_crack(task_id: str, salt: str):
    _set_status(task_id, status="queued", progress=0, cracked=0, total=0)
    return queue.enqueue(
        crack_job, task_id, salt, job_timeout=int(os.getenv("JOB_TIMEOUT", "7200"))
    )


def get_status(task_id: str) -> dict:
    d = _get_status(task_id)
    if not d:
        return {"status": "unknown"}
    out = {
        "status": d.get("status", "queued"),
        "progress": float(d.get("progress", 0)),
        "cracked": int(float(d.get("cracked", 0) or 0)),
        "total": int(float(d.get("total", 0) or 0)),
        "message": d.get("message"),
    }
    return out
