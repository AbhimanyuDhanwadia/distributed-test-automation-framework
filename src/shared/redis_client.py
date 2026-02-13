"""
Redis client wrapper with singleton connection pattern.
"""
import redis
from typing import Optional


class RedisClient:
    """
    Redis client wrapper that implements singleton pattern for connection caching.
    """
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        """
        Initialize Redis client configuration.
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
        """
        self.host = host
        self.port = port
        self.db = db
        self._connection: Optional[redis.Redis] = None
    
    def get_connection(self) -> redis.Redis:
        """
        Get or create a Redis connection (singleton pattern).
        
        Returns:
            redis.Redis: Cached Redis connection instance
        """
        if self._connection is None:
            self._connection = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True
            )
        return self._connection
