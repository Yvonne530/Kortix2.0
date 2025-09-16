# 修改 backend/services/supabase.py
from optimization.database.connection_pool import OptimizedDBConnection

class DBConnection:
    def __init__(self):
        self.optimized_connection = OptimizedDBConnection()
        self._client = None
    
    async def initialize(self):
        """初始化数据库连接"""
        await self.optimized_connection.initialize()
    
    @property
    async def client(self):
        """保持向后兼容性"""
        if not self._client:
            # 这里可以保持原有的supabase客户端作为备用
            pass
        return self.optimized_connection
    
    async def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询"""
        return await self.optimized_connection.execute_with_retry(query, params)