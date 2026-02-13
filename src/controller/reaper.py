"""
Reaper module for detecting and recovering from dead workers.
"""
import logging
import time
from typing import List

import redis

from src.shared.redis_client import RedisClient


logger = logging.getLogger(__name__)


class Reaper:
    """
    Reaper service that detects dead workers and requeues their tasks.
    
    Uses Lua scripts for atomic operations to prevent race conditions.
    """
    
    # Lua script to atomically find and remove dead workers
    LUA_REAP_SCRIPT = """
    local dead = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
    if #dead > 0 then
        redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
    end
    return dead
    """
    
    def __init__(self, redis_client: RedisClient):
        """
        Initialize the reaper with a Redis client.
        
        Args:
            redis_client: RedisClient instance for accessing Redis
        """
        self.redis = redis_client.get_connection()
    
    def reap_zombies(self) -> None:
        """
        Detect dead workers and requeue their tasks.
        
        Workers are considered dead if they haven't sent a heartbeat
        in the last 30 seconds. Their in-progress tasks are moved back
        to the pending queue.
        """
        # Calculate cutoff timestamp (30 seconds ago)
        cutoff_timestamp = time.time() - 30
        
        try:
            # Execute Lua script to atomically find and remove dead workers
            dead_workers = self.redis.eval(
                self.LUA_REAP_SCRIPT,
                1,
                "cluster:heartbeats",
                cutoff_timestamp
            )
            
            if dead_workers:
                logger.warning(f"Detected {len(dead_workers)} dead workers: {dead_workers}")
                
                # Requeue tasks from dead workers
                for worker_id in dead_workers:
                    if isinstance(worker_id, bytes):
                        worker_id = worker_id.decode('utf-8')
                    
                    processing_queue = f"processing:{worker_id}"
                    requeued_count = 0
                    
                    # Move all tasks from worker's processing queue back to pending
                    while True:
                        task = self.redis.rpoplpush(processing_queue, "tasks:pending")
                        if task is None:
                            break
                        requeued_count += 1
                    
                    if requeued_count > 0:
                        logger.info(f"Requeued {requeued_count} tasks from dead worker {worker_id}")
                    
                    # Clean up worker's processing queue
                    self.redis.delete(processing_queue)
                    
        except Exception as e:
            logger.error(f"Error during zombie reaping: {e}")
