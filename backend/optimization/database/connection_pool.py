# backend/optimization/database/connection_pool.py
import asyncpg
import asyncio
from typing import Optional, List, Dict, Any
from utils.logger import logger
from utils.config import config

class OptimizedDBConnection:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.connection_config = {
            'host': config.SUPABASE_HOST,
            'port': config.SUPABASE_PORT,
            'user': config.SUPABASE_USER,
            'password': config.SUPABASE_PASSWORD,
            'database': config.SUPABASE_DB,
            'min_size': 5,
            'max_size': 20,
            'max_queries': 50000,
            'max_inactive_connection_lifetime': 300,
            'command_timeout': 60,
            'server_settings': {
                'jit': 'off',  # 关闭JIT以提高连接速度
                'application_name': 'suna_optimized'
            }
        }
    
    async def initialize(self):
        """初始化连接池"""
        try:
            self.pool = await asyncpg.create_pool(**self.connection_config)
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self):
        """关闭连接池"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def execute_with_retry(self, query: str, params: tuple = None, 
                                max_retries: int = 3) -> List[Dict[str, Any]]:
        """带重试的查询执行"""
        for attempt in range(max_retries):
            try:
                async with self.pool.acquire() as conn:
                    if params:
                        rows = await conn.fetch(query, *params)
                    else:
                        rows = await conn.fetch(query)
                    
                    # 转换为字典列表
                    return [dict(row) for row in rows]
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 0.1 * (2 ** attempt)  # 指数退避
                    logger.warning(f"Query attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Query failed after {max_retries} attempts: {e}")
                    raise e
    
    async def execute_batch(self, queries: List[tuple]) -> List[List[Dict[str, Any]]]:
        """批量执行查询"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                results = []
                for query, params in queries:
                    if params:
                        rows = await conn.fetch(query, *params)
                    else:
                        rows = await conn.fetch(query)
                    results.append([dict(row) for row in rows])
                return results