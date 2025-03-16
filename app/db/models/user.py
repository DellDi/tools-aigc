"""
用户模型
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLAEnum, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from app.db.base import Base, TimestampMixin, UUIDMixin


class UserRole(str, Enum):
    """用户角色枚举"""

    ADMIN = "admin"
    USER = "user"
    API = "api"


class User(Base, UUIDMixin, TimestampMixin):
    """用户模型"""

    # 基本信息
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(100), unique=True, nullable=True, index=True, comment="邮箱")
    full_name = Column(String(100), nullable=True, comment="全名")

    # 认证信息
    hashed_password = Column(String(255), nullable=False, comment="哈希密码")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否激活")

    # 角色和权限
    role = Column(
        SQLAEnum(UserRole),
        default=UserRole.USER,
        nullable=False,
        comment="用户角色"
    )
    permissions = Column(ARRAY(String), default=[], nullable=False, comment="权限列表")

    # API访问
    api_key = Column(String(255), unique=True, nullable=True, index=True, comment="API密钥")

    # 其他信息
    last_login = Column(DateTime(timezone=True), nullable=True, comment="最后登录时间")
    description = Column(Text, nullable=True, comment="描述")

    def __repr__(self) -> str:
        return f"<User {self.username}>"