"""
Controller service - FastAPI application for managing distributed test execution.
"""
import contextlib
import logging
import os
import threading
import time
from typing import List
from uuid import uuid4

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel

from src.shared.models import TestTask
from src.shared.redis_client import RedisClient
from src.controller.reaper import Reaper


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Initialize Redis client with environment variables
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_client = RedisClient(host=redis_host, port=redis_port)
reaper = Reaper(redis_client)


# Request/Response models
class SubmitRequest(BaseModel):
    """Request model for submitting test tasks."""
    test_paths: List[str]


class SubmitResponse(BaseModel):
    """Response model for task submission."""
    job_id: str
    count: int


class MetricsResponse(BaseModel):
    """Response model for system metrics."""
    pending: int
    workers: int


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Starts background services on startup and cleans up on shutdown.
    """
    # Start reaper background thread
    def reaper_loop():
        logger.info("Reaper service started")
        while True:
            try:
                reaper.reap_zombies()
            except Exception as e:
                logger.error(f"Reaper error: {e}")
            time.sleep(10)
    
    reaper_thread = threading.Thread(target=reaper_loop, daemon=True)
    reaper_thread.start()
    
    logger.info("Controller service started")
    yield
    
    logger.info("Controller service shutting down")


# Initialize FastAPI app
app = FastAPI(
    title="Distributed Test Automation Framework",
    description="Controller service for managing distributed test execution",
    version="0.1.0",
    lifespan=lifespan
)


@app.post("/submit", response_model=SubmitResponse)
async def submit_tests(request: SubmitRequest) -> SubmitResponse:
    """
    Submit test tasks for distributed execution.
    
    Args:
        request: SubmitRequest containing list of test paths
        
    Returns:
        SubmitResponse with job_id and count of submitted tasks
    """
    job_id = str(uuid4())
    redis = redis_client.get_connection()
    
    logger.info(f"Submitting job {job_id} with {len(request.test_paths)} tests")
    
    for shard_id, test_path in enumerate(request.test_paths):
        # Create test task
        task = TestTask(
            job_id=job_id,
            test_path=test_path,
            shard_id=shard_id
        )
        
        # Push to pending queue
        redis.lpush("tasks:pending", task.model_dump_json())
    
    logger.info(f"Job {job_id} submitted successfully")
    
    return SubmitResponse(
        job_id=job_id,
        count=len(request.test_paths)
    )


@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics() -> MetricsResponse:
    """
    Get current system metrics.
    
    Returns:
        MetricsResponse with pending task count and active worker count
    """
    redis = redis_client.get_connection()
    
    pending_count = redis.llen("tasks:pending")
    worker_count = redis.zcard("cluster:heartbeats")
    
    return MetricsResponse(
        pending=pending_count,
        workers=worker_count
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
