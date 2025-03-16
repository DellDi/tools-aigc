"""
数据库会话管理模块
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)

# 创建异步数据库引擎
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
)

# 创建异步会话工厂
async_session_factory = async_sessionmaker(
    bind=async_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的依赖函数

    用于FastAPI的Depends注入
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.exception(f"数据库会话出错: {str(e)}")
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    初始化数据库

    在应用启动时调用
    """
    try:
        # 创建所有表（如果不存在）
        # 注意：在生产环境中，应该使用Alembic进行数据库迁移
        from app.db.base import Base

        async with async_engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)  # 仅用于开发环境
            await conn.run_sync(Base.metadata.create_all)

        logger.info("数据库初始化完成")
    except Exception as e:
        logger.exception(f"数据库初始化失败: {str(e)}")
        raise