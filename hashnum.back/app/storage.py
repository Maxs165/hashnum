import os
from pathlib import Path
from typing import Tuple

RUNTIME_DIR = Path(os.getenv("RUNTIME_DIR", "/data"))
UPLOADS_DIR = RUNTIME_DIR / "uploads"
RESULTS_DIR = RUNTIME_DIR / "results"
LOGS_DIR = RUNTIME_DIR / "logs"

for d in (UPLOADS_DIR, RESULTS_DIR, LOGS_DIR):
    d.mkdir(parents=True, exist_ok=True)


def task_paths(task_id: str) -> Tuple[Path, Path, Path]:
    in_file = UPLOADS_DIR / f"{task_id}.txt"
    out_file = RESULTS_DIR / f"{task_id}.csv"
    log_file = LOGS_DIR / f"{task_id}.log"
    return in_file, out_file, log_file
