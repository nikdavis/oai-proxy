import json
import os
from typing import Any, Dict, List, Optional

import redis
from loguru import logger


class CacheWrapper:
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default
        self.ttl_seconds = ttl_seconds
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self._client: Optional[redis.Redis] = None
        self._connected = False
        self._connect()

    def _connect(self):
        try:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
            self._client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory fallback.")
            self._connected = False
            self._fallback_cache: Dict[str, List[str]] = {}

    def get(self, key: str) -> Optional[List[str]]:
        if self._connected:
            try:
                value = self._client.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        else:
            return self._fallback_cache.get(key)
        return None

    def set(self, key: str, value: List[str]):
        if self._connected:
            try:
                self._client.setex(key, self.ttl_seconds, json.dumps(value))
            except Exception as e:
                logger.error(f"Redis set error: {e}")
                self._fallback_cache[key] = value
        else:
            self._fallback_cache[key] = value

    def clear(self):
        if self._connected:
            try:
                self._client.flushdb()
                logger.info("Redis cache cleared")
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
        else:
            self._fallback_cache.clear()
            logger.info("In-memory cache cleared")