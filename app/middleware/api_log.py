"""
极简化 API 日志中间件 - 完全非阻塞
支持文件和数据库双重存储
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Callable, Dict, List

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.db.models.api_log import ApiLog

logger = logging.getLogger(__name__)

# 确保日志目录存在
LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs"
)
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "api_logs.jsonl")

# 创建独立的异步数据库引擎，专门用于日志记录
# 这样可以避免与主应用的数据库连接池冲突
log_async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=3,  # 使用较小的连接池
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=3600,  # 每小时回收连接
    pool_timeout=3,  # 获取连接的超时时间
)

# 创建独立的异步会话工厂
log_async_session_factory = async_sessionmaker(
    bind=log_async_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# 全局日志队列 - 避免在中间件实例之间共享状态
_log_queue: List[Dict[str, Any]] = []
_is_worker_running = False

# 日志写入模式
LOG_FILE_ENABLED = True  # 启用文件日志
LOG_DB_ENABLED = True  # 启用数据库日志
BATCH_SIZE = 50  # 批量写入数据库的日志数量
CAPTURE_RESPONSE_BODY = True  # 是否捕获响应体
MAX_RESPONSE_SIZE = 1024 * 1024  # 最大响应体大小 (1MB)


async def _save_logs_to_db(logs: List[Dict[str, Any]]) -> None:
    """将日志保存到数据库中 (异步非阻塞)"""
    if not logs:
        return

    try:
        # 使用异步会话保存日志
        async with log_async_session_factory() as session:
            for log_data in logs:
                try:
                    # 创建日志对象
                    api_log = ApiLog(
                        id=(
                            uuid.UUID(log_data["id"])
                            if isinstance(log_data["id"], str)
                            else log_data["id"]
                        ),
                        method=log_data.get("method"),
                        path=log_data.get("path"),
                        query_params=log_data.get("query_params"),
                        headers=log_data.get("headers"),
                        client_ip=log_data.get("client_ip"),
                        user_agent=log_data.get("user_agent"),
                        request_body=log_data.get("request_body"),
                        status_code=log_data.get("status_code"),
                        response_body=log_data.get("response_body"),
                        process_time=log_data.get("duration_ms"),
                        user_id=(
                            uuid.UUID(log_data["user_id"])
                            if "user_id" in log_data and log_data["user_id"]
                            else None
                        ),
                        error=log_data.get("error"),
                    )
                    session.add(api_log)
                except Exception as e:
                    logger.error(f"创建日志对象时出错: {str(e)}")

            # 批量提交
            try:
                await session.commit()
                logger.debug(f"成功将 {len(logs)} 条日志写入数据库")
            except Exception as e:
                await session.rollback()
                logger.error(f"提交日志到数据库时出错: {str(e)}")
    except Exception as e:
        logger.exception(f"保存日志到数据库时出错: {str(e)}")


async def _log_worker():
    """
    后台工作线程，处理日志队列
    完全独立于请求处理流程
    """
    global _log_queue, _is_worker_running

    try:
        db_batch = []  # 数据库写入批次

        while True:
            # 如果队列为空，等待一小段时间
            if not _log_queue:
                # 如果有待写入数据库的批次，则先写入
                if LOG_DB_ENABLED and db_batch:
                    await _save_logs_to_db(db_batch)
                    db_batch = []
                await asyncio.sleep(0.1)
                continue

            # 批量处理日志记录，提高效率
            logs_to_process = _log_queue.copy()
            _log_queue.clear()

            # 文件日志处理
            if LOG_FILE_ENABLED:
                try:
                    # 批量写入文件
                    with open(LOG_FILE, "a", encoding="utf-8") as f:
                        for log in logs_to_process:
                            try:
                                f.write(json.dumps(log, ensure_ascii=False) + "\n")
                            except:
                                pass  # 忽略单条日志的序列化错误

                    logger.debug(f"成功写入 {len(logs_to_process)} 条日志到文件")
                except Exception as e:
                    logger.error(f"写入日志文件时出错: {str(e)}")

            # 数据库日志处理
            if LOG_DB_ENABLED:
                # 累积到批次中
                db_batch.extend(logs_to_process)

                # 如果批次足够大，执行数据库写入
                if len(db_batch) >= BATCH_SIZE:
                    await _save_logs_to_db(db_batch)
                    db_batch = []

            # 为防止CPU资源争用，短暂休眠
            await asyncio.sleep(0.01)
    except Exception as e:
        logger.exception(f"日志工作线程异常: {str(e)}")
    finally:
        _is_worker_running = False


class ApiLogMiddleware:
    """极简化API日志中间件 - 不阻塞主请求流程"""

    def __init__(self, app: FastAPI) -> None:
        """初始化中间件"""
        self.app = app

        # 启动工作线程
        global _is_worker_running
        if not _is_worker_running:
            _is_worker_running = True
            asyncio.create_task(_log_worker())

    async def __call__(
        self, scope: Dict[str, Any], receive: Callable, send: Callable
    ) -> None:
        """ASGI 中间件接口"""
        # 跳过非HTTP请求
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # 记录开始时间
        start_time = time.time()

        # 创建基本日志记录
        request_id = str(uuid.uuid4())
        path = scope.get("path", "Unknown")
        method = scope.get("method", "Unknown")

        # 尝试提取更多请求信息
        headers = {}
        client_ip = None
        query_params = {}
        user_agent = None
        request_body = None

        # 安全地提取头信息
        try:
            headers_raw = scope.get("headers", [])
            headers = {k.decode("utf8"): v.decode("utf8") for k, v in headers_raw}
            client_ip = scope.get("client", ("0.0.0.0", 0))[0]
            user_agent = headers.get("user-agent")

            # 提取查询参数
            query_string = scope.get("query_string", b"").decode("utf8")
            if query_string:
                query_params = dict(
                    item.split("=") for item in query_string.split("&") if "=" in item
                )
        except Exception as e:
            logger.debug(f"提取请求元数据时出错: {str(e)}")

        # 准备基本日志条目
        log_entry = {
            "id": request_id,
            "timestamp": time.time(),
            "method": method,
            "path": path,
            "request_time": start_time,
            "client_ip": client_ip,
            "user_agent": user_agent,
            "query_params": query_params,
            "headers": headers,
        }

        # 创建请求体捕获包装函数
        request_body_chunks = []
        body_complete = False

        async def receive_wrapper():
            nonlocal body_complete
            
            # 调用原始 receive 函数
            message = await receive()
            
            # 捕获请求体
            if message["type"] == "http.request":
                # 收集请求体
                chunk = message.get("body", b"")
                if chunk:
                    request_body_chunks.append(chunk)
                
                # 检查是否是最后一个请求块
                if not message.get("more_body", False):
                    body_complete = True
                    full_body = b"".join(request_body_chunks)
                    
                    # 尝试解析为JSON
                    try:
                        json_body = json.loads(full_body)
                        log_entry["request_body"] = json_body
                    except json.JSONDecodeError:
                        # 非JSON请求体
                        content_type = headers.get("content-type", "")
                        log_entry["request_body"] = {
                            "_content_type": content_type,
                            "_size": len(full_body),
                            "_preview": full_body[:200].decode("utf-8", errors="replace") if len(full_body) > 0 else ""
                        }
            
            return message
        
        # 定义包装发送函数
        original_send = send
        response_chunks = []

        async def wrapped_send(message):
            if message["type"] == "http.response.start":
                # 记录状态码
                log_entry["status_code"] = message.get("status", 0)
                # 记录响应头
                headers = [(k.decode("utf-8"), v.decode("utf-8")) for k, v in message.get("headers", [])]
                log_entry["response_headers"] = dict(headers)

            elif message["type"] == "http.response.body":
                # 收集响应体(最大限制为1MB以避免内存问题)
                if CAPTURE_RESPONSE_BODY:
                    body = message.get("body", b"")
                    if body and len(response_chunks) < 5 and sum(len(chunk) for chunk in response_chunks) < MAX_RESPONSE_SIZE:
                        response_chunks.append(body)
                
                # 如果这是最后一个响应块
                if not message.get("more_body", False):
                    # 记录响应完成时间
                    log_entry["response_time"] = time.time()
                    log_entry["duration_ms"] = int((time.time() - start_time) * 1000)
                    
                    # 处理响应体(如果有)
                    if CAPTURE_RESPONSE_BODY and response_chunks:
                        full_body = b"".join(response_chunks)
                        try:
                            # 尝试解析为JSON
                            response_json = json.loads(full_body)
                            log_entry["response_body"] = response_json
                        except json.JSONDecodeError:
                            # 非JSON响应，记录类型信息和大小
                            content_type = log_entry.get("response_headers", {}).get("content-type", "")
                            log_entry["response_body"] = {
                                "_content_type": content_type,
                                "_size": len(full_body),
                                "_preview": full_body[:200].decode("utf-8", errors="replace") if len(full_body) > 0 else ""
                            }

                    # 将日志入队 - 完全非阻塞
                    global _log_queue
                    _log_queue.append(log_entry.copy())

            # 继续发送响应
            return await original_send(message)

        # 调用下一个中间件或应用处理程序
        try:
            await self.app(scope, receive_wrapper, wrapped_send)
        except Exception as e:
            # 记录异常但不影响异常传播
            log_entry["error"] = str(e)
            log_entry["response_time"] = time.time()
            log_entry["duration_ms"] = int((time.time() - start_time) * 1000)
            _log_queue.append(log_entry.copy())
            raise
