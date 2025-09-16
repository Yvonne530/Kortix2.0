# backend/optimization/cache/file_cache.py
import pickle
import json
from typing import Optional, Any
import asyncio
from utils.logger import logger

class FileCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.memory_cache = {}
        self.max_memory_size = 100 * 1024 * 1024  # 100MB
        self.current_memory_size = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        # L1: 内存缓存
        if key in self.memory_cache:
            logger.debug(f"Cache hit (memory): {key}")
            return self.memory_cache[key]
        
        # L2: Redis缓存
        try:
            cached = await self.redis.get(f"file_cache:{key}")
            if cached:
                result = pickle.loads(cached)
                # 回填到内存缓存
                await self._add_to_memory_cache(key, result)
                logger.debug(f"Cache hit (redis): {key}")
                return result
        except Exception as e:
            logger.warning(f"Redis cache get error: {e}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """设置缓存"""
        # 添加到内存缓存
        await self._add_to_memory_cache(key, value)
        
        # 添加到Redis缓存
        try:
            serialized = pickle.dumps(value)
            await self.redis.setex(f"file_cache:{key}", ttl, serialized)
            logger.debug(f"Cache set: {key}")
        except Exception as e:
            logger.warning(f"Redis cache set error: {e}")
    
    async def _add_to_memory_cache(self, key: str, value: Any):
        """添加到内存缓存"""
        value_size = len(pickle.dumps(value))
        
        # 如果超过内存限制，清理旧缓存
        while (self.current_memory_size + value_size > self.max_memory_size and 
               self.memory_cache):
            # 删除最旧的缓存项
            oldest_key = next(iter(self.memory_cache))
            old_value = self.memory_cache.pop(oldest_key)
            self.current_memory_size -= len(pickle.dumps(old_value))
        
        self.memory_cache[key] = value
        self.current_memory_size += value_size