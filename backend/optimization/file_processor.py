import asyncio
import aiofiles
from typing import Dict, Any, List, Optional
from pathlib import Path
import hashlib
import pickle
from utils.logger import logger

class AsyncFileProcessor:
    def __init__(self, redis_client):
        self.processors = {
            '.pdf': self._process_pdf_async,
            '.docx': self._process_docx_async,
            '.xlsx': self._process_excel_async,
            '.csv': self._process_csv_async,
            '.txt': self._process_text_async
        }
        self.cache = FileCache(redis_client)
        self.processing_queue = asyncio.Queue(maxsize=100)
        self.worker_tasks = []
    
    async def start_workers(self, num_workers: int = 3):
        """启动文件处理工作进程"""
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.append(task)
    
    async def _worker(self, worker_name: str):
        """文件处理工作进程"""
        logger.info(f"File processing worker {worker_name} started")
        while True:
            try:
                task = await self.processing_queue.get()
                await self._process_file_task(task)
                self.processing_queue.task_done()
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
    
    async def process_file_async(self, file_data: bytes, filename: str, 
                                mime_type: str) -> Dict[str, Any]:
        """异步文件处理入口"""
        # 生成缓存键
        cache_key = self._generate_cache_key(file_data, filename)
        
        # 检查缓存
        if cached_result := await self.cache.get(cache_key):
            logger.debug(f"File {filename} served from cache")
            return cached_result
        
        # 添加到处理队列
        task = {
            'file_data': file_data,
            'filename': filename,
            'mime_type': mime_type,
            'cache_key': cache_key
        }
        
        await self.processing_queue.put(task)
        
        # 等待处理完成（实际实现中可以使用回调或事件）
        return await self._wait_for_processing(task)
    
    async def _process_file_task(self, task: Dict[str, Any]):
        """处理单个文件任务"""
        file_data = task['file_data']
        filename = task['filename']
        mime_type = task['mime_type']
        cache_key = task['cache_key']
        
        try:
            # 并行处理不同格式
            tasks = []
            file_ext = Path(filename).suffix.lower()
            
            if file_ext in self.processors:
                tasks.append(self.processors[file_ext](file_data))
            
            if not tasks:
                raise ValueError(f"Unsupported file format: {file_ext}")
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 合并结果
            final_result = self._merge_results(results, filename)
            
            # 缓存结果
            await self.cache.set(cache_key, final_result, ttl=3600)
            
            logger.info(f"File {filename} processed successfully")
            
        except Exception as e:
            logger.error(f"Error processing file {filename}: {e}")
            raise
    
    def _generate_cache_key(self, file_data: bytes, filename: str) -> str:
        """生成缓存键"""
        content_hash = hashlib.md5(file_data).hexdigest()
        return f"file:{filename}:{content_hash}"