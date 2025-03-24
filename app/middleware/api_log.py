"""
API日志中间件
"""

import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.api_log import ApiLog
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)


class ApiLogMiddleware:
    """API日志中间件"""

    def __init__(self, app: FastAPI) -> None:
        """
        初始化中间件

        Args:
            app: FastAPI应用实例
        """
        self.app = app

    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable) -> None:
        """
        ASGI 中间件调用接口

        Args:
            scope: ASGI 请求作用域
            receive: ASGI 接收函数
            send: ASGI 发送函数
        """
        if scope["type"] != "http":
            # 非HTTP请求（如WebSocket）直接传递
            await self.app(scope, receive, send)
            return
            
        # 创建请求对象
        request = Request(scope, receive=receive)
        
        # 记录请求开始时间
        start_time = time.time()
        """
        中间件调用

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 响应对象
        """
        # 记录请求开始时间
        start_time = time.time()

        # 提取请求信息
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else None

        # 创建日志记录
        log_entry = {
            "id": str(uuid.uuid4()),
            "method": method,
            "path": path,
            "client_ip": client_ip,
        }

        # 尝试提取查询参数
        try:
            query_params = dict(request.query_params)
            log_entry["query_params"] = query_params
        except Exception as e:
            logger.warning(f"无法提取查询参数: {str(e)}")

        # 尝试提取请求头
        try:
            # 过滤敏感头部
            headers = dict(request.headers)
            sensitive_headers = ["authorization", "cookie", "x-api-key"]
            filtered_headers = {
                k: v if k.lower() not in sensitive_headers else "[FILTERED]"
                for k, v in headers.items()
            }
            log_entry["headers"] = filtered_headers
            log_entry["user_agent"] = headers.get("user-agent")
        except Exception as e:
            logger.warning(f"无法提取请求头: {str(e)}")

        # 尝试提取请求体
        try:
            # 读取请求体（如果有）
            body = await request.body()
            if body:
                # 尝试解析为JSON
                try:
                    body_json = json.loads(body)
                    # 过滤敏感字段
                    sensitive_fields = ["password", "token", "api_key", "secret"]
                    if isinstance(body_json, dict):
                        filtered_body = {
                            k: v if k.lower() not in sensitive_fields else "[FILTERED]"
                            for k, v in body_json.items()
                        }
                        log_entry["request_body"] = filtered_body
                except json.JSONDecodeError:
                    # 如果不是JSON，则存储原始内容的长度
                    log_entry["request_body"] = {"_raw_length": len(body)}
        except Exception as e:
            logger.warning(f"无法提取请求体: {str(e)}")

        # 提取用户ID（如果有）
        try:
            user = request.state.user if hasattr(request.state, "user") else None
            if user:
                log_entry["user_id"] = str(user.id)
        except Exception as e:
            logger.warning(f"无法提取用户ID: {str(e)}")

        # 创建自定义发送函数来捕获响应
        response_body = []
        send_complete = False
        response_status = 200
        response_headers = []
        
        async def send_wrapper(message):
            nonlocal send_complete, response_status, response_headers
            
            if message["type"] == "http.response.start":
                response_status = message["status"]
                response_headers = message["headers"]
                await send(message)
            elif message["type"] == "http.response.body":
                if message.get("body"):
                    response_body.append(message.get("body", b""))
                if not message.get("more_body", False):
                    send_complete = True
                await send(message)
            else:
                await send(message)
        
        # 调用下一个中间件或路由处理函数
        try:
            await self.app(scope, receive, send_wrapper)

            # 记录响应信息
            log_entry["status_code"] = response_status
            
            # 尝试解析响应体
            if response_body:
                full_response_body = b"".join(response_body)
                
                # 尝试解析为JSON
                try:
                    body_json = json.loads(full_response_body)
                    log_entry["response_body"] = body_json
                except json.JSONDecodeError:
                    # 如果不是JSON，则存储原始内容的长度
                    log_entry["response_body"] = {"_raw_length": len(full_response_body)}
            else:
                log_entry["response_body"] = {"_raw_length": 0}

        except Exception as e:
            # 记录错误信息
            log_entry["error"] = str(e)
            logger.exception(f"请求处理出错: {str(e)}")
            raise
        finally:
            # 计算处理时间
            process_time = int((time.time() - start_time) * 1000)  # 毫秒
            log_entry["process_time"] = process_time

            # 异步保存日志
            try:
                await self._save_log(log_entry)
            except Exception as e:
                logger.exception(f"保存API日志出错: {str(e)}")

        # 中间件不返回响应，因为我们已经通过 send 函数发送了响应

    async def _save_log(self, log_data: Dict[str, Any]) -> None:
        """
        保存日志到数据库

        Args:
            log_data: 日志数据
        """
        # 创建API日志对象
        api_log = ApiLog(
            id=uuid.UUID(log_data["id"]) if "id" in log_data else uuid.uuid4(),
            method=log_data.get("method"),
            path=log_data.get("path"),
            query_params=log_data.get("query_params"),
            headers=log_data.get("headers"),
            client_ip=log_data.get("client_ip"),
            user_agent=log_data.get("user_agent"),
            request_body=log_data.get("request_body"),
            status_code=log_data.get("status_code"),
            response_body=log_data.get("response_body"),
            process_time=log_data.get("process_time"),
            user_id=uuid.UUID(log_data["user_id"]) if "user_id" in log_data else None,
            error=log_data.get("error"),
        )

        # 保存到数据库
        async with async_session_factory() as session:
            session.add(api_log)
            try:
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.exception(f"保存API日志到数据库失败: {str(e)}")