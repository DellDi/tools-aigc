#!/usr/bin/env python
"""
数据库初始化脚本
用于创建数据库（如果不存在）并应用所有迁移
支持异步 PostgreSQL 连接
"""

import asyncio
import os
import sys
from urllib.parse import urlparse

import asyncpg
from alembic.config import Config
from alembic import command
from dotenv import load_dotenv


async def ensure_database_exists(db_url: str) -> bool:
    """
    确保数据库存在，如果不存在则创建
    
    Args:
        db_url: 数据库连接URL (postgresql+asyncpg://...)
        
    Returns:
        bool: 如果数据库已存在或成功创建则返回True
    """
    # 处理异步PostgreSQL URL
    if db_url.startswith('postgresql+asyncpg://'):
        # 转换为标准PostgreSQL URL
        db_url = db_url.replace('postgresql+asyncpg://', 'postgresql://')
    
    # 解析数据库URL
    parsed = urlparse(db_url)
    dbname = parsed.path.strip('/')
    user = parsed.username
    password = parsed.password
    host = parsed.hostname
    port = parsed.port or 5432
    
    try:
        # 连接到默认的postgres数据库
        conn = await asyncpg.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database='postgres'
        )
        
        # 检查数据库是否存在
        result = await conn.fetchrow(
            f"SELECT 1 FROM pg_database WHERE datname = $1",
            dbname
        )
        
        if not result:
            print(f"创建数据库 {dbname}...")
            await conn.execute(f'CREATE DATABASE "{dbname}"')
            print(f"数据库 {dbname} 创建成功!")
            created = True
        else:
            print(f"数据库 {dbname} 已存在.")
            created = False
            
        await conn.close()
        return True
    except Exception as e:
        print(f"检查/创建数据库时出错: {e}", file=sys.stderr)
        return False


def apply_migrations():
    """应用所有迁移"""
    try:
        print("应用数据库迁移...")
        # 获取项目根目录的绝对路径
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 创建Alembic配置
        alembic_cfg = Config(os.path.join(base_dir, "alembic.ini"))
        
        # 运行迁移
        command.upgrade(alembic_cfg, "head")
        print("数据库迁移应用成功!")
        return True
    except Exception as e:
        print(f"应用迁移时出错: {e}", file=sys.stderr)
        return False


def main():
    """主函数"""
    # 加载环境变量
    load_dotenv()
    
    # 获取数据库URL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("错误: 未设置DATABASE_URL环境变量", file=sys.stderr)
        sys.exit(1)
    
    # 确保数据库存在
    try:
        # 创建一个新的事件循环来运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        db_exists = loop.run_until_complete(ensure_database_exists(db_url))
        loop.close()
        
        if not db_exists:
            print("错误: 无法确保数据库存在", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"确保数据库存在时出错: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 应用迁移
    if not apply_migrations():
        print("错误: 应用迁移失败", file=sys.stderr)
        sys.exit(1)
    
    print("数据库初始化完成!")


if __name__ == "__main__":
    main()
