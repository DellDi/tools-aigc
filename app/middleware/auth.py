"""
认证中间件
"""

import logging
from typing import Callable, List, Optional

from fastapi import FastAPI, HTTPException, Request, Response, status
from jose import JWTError, jwt

from app.core.config import settings
from app.db.models.user import User
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """认证中间件"""

    def __init__(
        self,
        app: FastAPI,
        exclude_paths: Optional[List[str]] = None,
        exclude_prefixes: Optional[List[str]] = None,
    ) -> None:
        """
        初始化中间件

        Args:
            app: FastAPI应用实例
            exclude_paths: 排除的路径（完全匹配）
            exclude_prefixes: 排除的路径前缀
        """
        self.app = app
        self.exclude_paths = exclude_paths or []
        self.exclude_prefixes = exclude_prefixes or []

        # 添加默认的白名单路径
        self.exclude_paths.extend(settings.API_WHITELIST)

        # 添加默认的白名单前缀
        self.exclude_prefixes.extend([
            "/docs",
            "/redoc",
            "/openapi.json",
        ])

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """
        中间件调用

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 响应对象
        """
        # 检查路径是否在白名单中
        path = request.url.path

        # 完全匹配
        if path in self.exclude_paths:
            return await call_next(request)

        # 前缀匹配
        for prefix in self.exclude_prefixes:
            if path.startswith(prefix):
                return await call_next(request)

        # 提取认证头
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return Response(
                content='{"detail":"未提供认证凭据"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 检查认证类型
        auth_parts = auth_header.split()
        if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
            return Response(
                content='{"detail":"无效的认证类型"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = auth_parts[1]

        try:
            # 解码JWT
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            user_id = payload.get("sub")

            if user_id is None:
                return Response(
                    content='{"detail":"无效的认证凭据"}',
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    media_type="application/json",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # 查询用户
            async with async_session_factory() as session:
                user = await session.get(User, user_id)

                if user is None:
                    return Response(
                        content='{"detail":"用户未找到"}',
                        status_code=status.HTTP_404_NOT_FOUND,
                        media_type="application/json",
                    )

                if not user.is_active:
                    return Response(
                        content='{"detail":"用户未激活"}',
                        status_code=status.HTTP_400_BAD_REQUEST,
                        media_type="application/json",
                    )

                # 将用户对象存储在请求状态中
                request.state.user = user

        except JWTError as e:
            logger.error(f"JWT解码错误: {str(e)}")
            return Response(
                content='{"detail":"无效的认证凭据"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except Exception as e:
            logger.exception(f"认证处理出错: {str(e)}")
            return Response(
                content='{"detail":"认证处理出错"}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="application/json",
            )

        # 调用下一个中间件或路由处理函数
        return await call_next(request)