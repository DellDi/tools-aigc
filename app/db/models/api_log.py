"""
API日志模型
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base, TimestampMixin, UUIDMixin


class ApiLog(Base, UUIDMixin, TimestampMixin):
    """API调用日志模型"""

    # 请求信息
    method = Column(String(10), nullable=False, comment="HTTP方法")
    path = Column(String(255), nullable=False, comment="请求路径")
    query_params = Column(JSONB, nullable=True, comment="查询参数")
    headers = Column(JSONB, nullable=True, comment="请求头")
    client_ip = Column(String(50), nullable=True, comment="客户端IP")
    user_agent = Column(String(255), nullable=True, comment="用户代理")

    # 请求体
    request_body = Column(JSONB, nullable=True, comment="请求体")

    # 响应信息
    status_code = Column(Integer, nullable=True, comment="状态码")
    response_body = Column(JSONB, nullable=True, comment="响应体")

    # 性能信息
    process_time = Column(Integer, nullable=True, comment="处理时间（毫秒）")

    # 用户信息
    user_id = Column(UUID(as_uuid=True), nullable=True, comment="用户ID")

    # 错误信息
    error = Column(Text, nullable=True, comment="错误信息")

    def __repr__(self) -> str:
        return f"<ApiLog {self.method} {self.path} {self.status_code}>"