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

    async def __call__(self, request: Request, call_next: Callable) -> Response:
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

        # 调用下一个中间件或路由处理函数
        try:
            response = await call_next(request)

            # 记录响应信息
            log_entry["status_code"] = response.status_code

            # 尝试提取响应体
            try:
                # 读取响应体
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk

                # 重新设置响应体
                response = Response(
                    content=response_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )

                # 尝试解析为JSON
                try:
                    body_json = json.loads(response_body)
                    log_entry["response_body"] = body_json
                except json.JSONDecodeError:
                    # 如果不是JSON，则存储原始内容的长度
                    log_entry["response_body"] = {"_raw_length": len(response_body)}
            except Exception as e:
                logger.warning(f"无法提取响应体: {str(e)}")

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

        return response

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
            await session.commit()