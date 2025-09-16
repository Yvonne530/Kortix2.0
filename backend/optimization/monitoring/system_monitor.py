# backend/optimization/monitoring/system_monitor.py
import asyncio
import psutil
import time
from typing import Dict, Any, List
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from utils.logger import logger

class SystemMonitor:
    def __init__(self, port: int = 8001):
        self.port = port
        self.metrics = {
            'request_count': Counter('suna_requests_total', 'Total requests', ['endpoint', 'method']),
            'request_duration': Histogram('suna_request_duration_seconds', 'Request duration', ['endpoint']),
            'active_connections': Gauge('suna_active_connections', 'Active database connections'),
            'memory_usage': Gauge('suna_memory_usage_bytes', 'Memory usage in bytes'),
            'cpu_usage': Gauge('suna_cpu_usage_percent', 'CPU usage percentage'),
            'browser_sessions': Gauge('suna_browser_sessions_active', 'Active browser sessions'),
            'file_processing_queue': Gauge('suna_file_processing_queue_size', 'File processing queue size')
        }
        
        self.health_checks = {
            'database': self._check_database_health,
            'redis': self._check_redis_health,
            'browser_pool': self._check_browser_pool_health,
            'file_processor': self._check_file_processor_health
        }
    
    async def start_monitoring(self):
        """启动监控服务"""
        # 启动Prometheus指标服务器
        start_http_server(self.port)
        logger.info(f"Monitoring server started on port {self.port}")
        
        # 启动系统指标收集
        asyncio.create_task(self._collect_system_metrics())
        
        # 启动健康检查
        asyncio.create_task(self._run_health_checks())
    
    async def _collect_system_metrics(self):
        """收集系统指标"""
        while True:
            try:
                # 内存使用
                memory = psutil.virtual_memory()
                self.metrics['memory_usage'].set(memory.used)
                
                # CPU使用
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metrics['cpu_usage'].set(cpu_percent)
                
                # 其他自定义指标
                # ...
                
                await asyncio.sleep(10)  # 每10秒收集一次
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(30)
    
    async def _run_health_checks(self):
        """运行健康检查"""
        while True:
            try:
                health_status = {}
                for check_name, check_func in self.health_checks.items():
                    try:
                        health_status[check_name] = await check_func()
                    except Exception as e:
                        health_status[check_name] = {'status': 'unhealthy', 'error': str(e)}
                
                # 记录健康状态
                logger.debug(f"Health check results: {health_status}")
                
                await asyncio.sleep(30)  # 每30秒检查一次
                
            except Exception as e:
                logger.error(f"Error running health checks: {e}")
                await asyncio.sleep(60)
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """检查数据库健康状态"""
        try:
            # 这里添加实际的数据库健康检查逻辑
            return {'status': 'healthy', 'response_time': 0.1}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    async def _check_redis_health(self) -> Dict[str, Any]:
        """检查Redis健康状态"""
        try:
            # 这里添加实际的Redis健康检查逻辑
            return {'status': 'healthy', 'response_time': 0.05}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    async def _check_browser_pool_health(self) -> Dict[str, Any]:
        """检查浏览器池健康状态"""
        try:
            # 这里添加实际的浏览器池健康检查逻辑
            return {'status': 'healthy', 'active_sessions': 0}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}
    
    async def _check_file_processor_health(self) -> Dict[str, Any]:
        """检查文件处理器健康状态"""
        try:
            # 这里添加实际的文件处理器健康检查逻辑
            return {'status': 'healthy', 'queue_size': 0}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}