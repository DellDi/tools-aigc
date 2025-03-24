"""
Alembic环境配置
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# 在 run_migrations_online 函数中添加
from sqlalchemy_utils import database_exists, create_database

from app.core.config import settings

# 导入所有模型，确保它们被加载到元数据中
from app.db.models import *  # noqa

# 加载Alembic配置
config = context.config

# 解释alembic.ini中的配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置SQLAlchemy URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 添加模型的元数据
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    离线运行迁移

    不需要实际连接数据库，只生成SQL脚本
    """
    url = config.get_main_option("sqlalchemy.url")
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    运行迁移
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    在线运行迁移

    实际连接数据库并应用迁移
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
