"""
API路由模块
"""

from fastapi import APIRouter

from app.api.endpoints import auth, tools

# 创建主路由
api_router = APIRouter()

# 注册认证路由
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# 注册工具路由
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])