from pydantic import BaseModel, Field
from typing import Optional, Literal, Any


class CrackCreate(BaseModel):
    salt: str = Field(..., min_length=1)


class TaskInfo(BaseModel):
    task_id: str


class TaskStatus(BaseModel):
    task_id: str
    status: Literal["queued", "started", "finished", "failed"]
    progress: float = 0.0
    cracked: int = 0
    total: int = 0
    message: Optional[str] = None


class LogChunk(BaseModel):
    lines: list[str]
    cursor: int
