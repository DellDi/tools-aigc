"""
HTTP请求工具
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

import httpx
from pydantic import BaseModel, Field

from app.tools.base import BaseTool, ToolRegistry, ToolResult

logger = logging.getLogger(__name__)


class HttpRequestParameters(BaseModel):
    """HTTP请求参数"""

    url: str = Field(..., description="请求URL")
    method: str = Field(default="GET", description="请求方法，支持GET、POST、PUT、DELETE等")
    headers: Optional[Dict[str, str]] = Field(default=None, description="请求头")
    params: Optional[Dict[str, Any]] = Field(default=None, description="URL查询参数")
    data: Optional[Union[Dict[str, Any], List[Any], str]] = Field(default=None, description="请求体数据，用于POST、PUT等方法")
    json_data: Optional[Union[Dict[str, Any], List[Any]]] = Field(default=None, description="JSON格式的请求体数据")
    timeout: Optional[float] = Field(default=10.0, description="请求超时时间（秒）")


class HttpRequestTool(BaseTool):
    """HTTP请求工具"""

    name = "http_request"
    description = "发送HTTP请求并获取响应"
    parameters_schema = HttpRequestParameters

    async def execute(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], List[Any], str]] = None,
        json_data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        timeout: Optional[float] = 10.0
    ) -> ToolResult:
        """
        执行HTTP请求

        Args:
            url: 请求URL
            method: 请求方法，支持GET、POST、PUT、DELETE等
            headers: 请求头
            params: URL查询参数
            data: 请求体数据，用于POST、PUT等方法
            json_data: JSON格式的请求体数据
            timeout: 请求超时时间（秒）

        Returns:
            ToolResult: 请求结果
        """
        # 验证请求方法
        method = method.upper()
        valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
        if method not in valid_methods:
            return ToolResult(
                success=False,
                error=f"不支持的请求方法: {method}，支持的方法有: {', '.join(valid_methods)}"
            )

        # 设置默认请求头
        if headers is None:
            headers = {}

        # 如果没有设置User-Agent，则设置一个默认值
        if "User-Agent" not in headers:
            headers["User-Agent"] = "tools-aigc/0.1.0"

        try:
            # 发送请求
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json_data,
                    timeout=timeout
                )

                # 尝试解析响应内容为JSON
                try:
                    response_data = response.json()
                except Exception:
                    response_data = response.text

                # 构建结果
                result = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "data": response_data,
                    "url": str(response.url)
                }

                return ToolResult(
                    success=response.is_success,
                    data=result,
                    error=None if response.is_success else f"请求失败，状态码: {response.status_code}"
                )

        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                error=f"请求超时（{timeout}秒）"
            )
        except httpx.RequestError as e:
            logger.exception(f"请求错误: {str(e)}")
            return ToolResult(
                success=False,
                error=f"请求错误: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"未知错误: {str(e)}")
            return ToolResult(
                success=False,
                error=f"未知错误: {str(e)}"
            )


# 注册工具
ToolRegistry.register(HttpRequestTool())