"""
Worker node implementation for distributed test execution.
"""
import json
import os
import socket
import threading
import time
from uuid import uuid4

import redis

from src.shared.models import TestTask, TestResult, TaskStatus, WorkerHeartbeat
from src.shared.redis_client import RedisClient
from src.worker import executor


class WorkerNode:
    """
    Worker node that processes test tasks from the distributed queue.
    
    Implements heartbeat mechanism and atomic result processing.
    """
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        """
        Initialize the worker node.
        
        Args:
            redis_host: Redis server host
            redis_port: Redis server port
        """
        # Generate unique worker ID
        self.worker_id = f"worker-{socket.gethostname()}-{uuid4().hex[:8]}"
        
        # Connect to Redis
        redis_client = RedisClient(host=redis_host, port=redis_port)
        self.redis = redis_client.get_connection()
        
        # Worker state
        self.running = True
        
        print(f"Worker initialized: {self.worker_id}")
    
    def start_heartbeat(self) -> None:
        """
        Start the heartbeat thread to signal worker availability.
        
        Runs as a daemon thread, sending periodic heartbeats to Redis.
        """
        def heartbeat_loop():
            while self.running:
                try:
                    timestamp = time.time()
                    heartbeat = WorkerHeartbeat(
                        worker_id=self.worker_id,
                        status="ONLINE",
                        timestamp=timestamp
                    )
                    
                    # Add worker to sorted set with timestamp as score
                    self.redis.zadd(
                        "cluster:heartbeats",
                        {self.worker_id: timestamp}
                    )
                    
                    # Also store detailed heartbeat data
                    self.redis.setex(
                        f"heartbeat:{self.worker_id}",
                        15,  # Expire after 15 seconds
                        heartbeat.model_dump_json()
                    )
                    
                except Exception as e:
                    print(f"Heartbeat error: {e}")
                
                time.sleep(5)
        
        heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        print(f"Heartbeat started for {self.worker_id}")
    
    def run(self) -> None:
        """
        Main worker loop that processes tasks from the queue.
        
        Implements atomic result processing with distributed locking.
        """
        # Start heartbeat mechanism
        self.start_heartbeat()
        
        print(f"Worker {self.worker_id} is ready to process tasks...")
        
        while self.running:
            try:
                # Atomically move task from pending to processing queue
                task_json = self.redis.brpoplpush(
                    "tasks:pending",
                    f"processing:{self.worker_id}",
                    timeout=2
                )
                
                if task_json is None:
                    continue
                
                # Parse task
                task_data = json.loads(task_json)
                task = TestTask(**task_data)
                
                print(f"Processing task {task.task_id}: {task.test_path}")
                
                # Execute the test
                test_result = executor.run_test(task.test_path)
                
                # Construct result object
                result = TestResult(
                    task_id=task.task_id,
                    worker_id=self.worker_id,
                    status=TaskStatus.COMPLETED if test_result["success"] else TaskStatus.FAILED,
                    output=test_result["output"],
                    duration=test_result["duration"]
                )
                
                # Atomic Result Write with distributed lock
                lock_key = f"result:lock:{task.task_id}"
                lock_acquired = self.redis.setnx(lock_key, self.worker_id)
                
                if lock_acquired:
                    # Set lock expiration to prevent deadlocks
                    self.redis.expire(lock_key, 60)
                    
                    # Write result to results queue
                    self.redis.lpush("results", result.model_dump_json())
                    
                    print(f"Result written for task {task.task_id}: {result.status}")
                else:
                    print(f"Result already written for task {task.task_id} by another worker")
                
                # Acknowledge task completion by removing from processing queue
                self.redis.lrem(f"processing:{self.worker_id}", 0, task_json)
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse task JSON: {e}")
            except Exception as e:
                print(f"Error processing task: {e}")
        
        print(f"Worker {self.worker_id} shutting down...")
    
    def stop(self) -> None:
        """Stop the worker gracefully."""
        self.running = False


def main():
    """Entry point for the worker node."""
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    
    worker = WorkerNode(redis_host=redis_host, redis_port=redis_port)
    
    try:
        worker.run()
    except KeyboardInterrupt:
        print("\nReceived shutdown signal...")
        worker.stop()


if __name__ == "__main__":
    main()
