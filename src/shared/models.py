"""
Shared data models for the Distributed Test Automation Framework.
"""
from enum import Enum
from typing import Optional
from uuid import uuid4
import time

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Enumeration of possible task statuses."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TestTask(BaseModel):
    """Model representing a test task to be executed."""
    job_id: str
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    test_path: str
    shard_id: int
    created_at: float = Field(default_factory=time.time)


class TestResult(BaseModel):
    """Model representing the result of a test execution."""
    task_id: str
    worker_id: str
    status: TaskStatus
    output: str
    duration: float


class WorkerHeartbeat(BaseModel):
    """Model representing a worker heartbeat signal."""
    worker_id: str
    status: str = "ONLINE"
    timestamp: float = Field(default_factory=time.time)
    current_task_id: Optional[str] = None
