"""
认证相关的数据模型
"""

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """令牌模型"""

    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")


class TokenPayload(BaseModel):
    """令牌载荷模型"""

    sub: Optional[str] = Field(None, description="主题（通常是用户ID）")
    exp: Optional[int] = Field(None, description="过期时间")


class UserLogin(BaseModel):
    """用户登录模型"""

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserCreate(BaseModel):
    """用户创建模型"""

    username: str = Field(..., description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    password: str = Field(..., description="密码")
    full_name: Optional[str] = Field(None, description="全名")


class UserUpdate(BaseModel):
    """用户更新模型"""

    email: Optional[EmailStr] = Field(None, description="邮箱")
    full_name: Optional[str] = Field(None, description="全名")
    password: Optional[str] = Field(None, description="密码")
    is_active: Optional[bool] = Field(None, description="是否激活")


class UserResponse(BaseModel):
    """用户响应模型"""

    id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    full_name: Optional[str] = Field(None, description="全名")
    is_active: bool = Field(..., description="是否激活")
    role: str = Field(..., description="角色")
    permissions: List[str] = Field(default=[], description="权限列表")

    class Config:
        """配置"""

        from_attributes = True