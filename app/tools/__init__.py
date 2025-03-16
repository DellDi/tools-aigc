"""
工具模块
"""

import importlib
import logging
import os
import pkgutil
from typing import List

from app.tools.base import BaseTool, ToolRegistry

logger = logging.getLogger(__name__)


def load_tools() -> List[BaseTool]:
    """
    加载所有工具

    自动导入app.tools包下的所有模块，并返回已注册的工具列表
    """
    logger.info("开始加载工具...")

    # 获取当前包的路径
    package_path = os.path.dirname(__file__)

    # 遍历包中的所有模块
    for _, module_name, is_pkg in pkgutil.iter_modules([package_path]):
        # 跳过__init__.py和base.py
        if module_name in ["__init__", "base"]:
            continue

        # 导入模块
        try:
            module = importlib.import_module(f"app.tools.{module_name}")
            logger.info(f"已加载工具模块: {module_name}")
        except Exception as e:
            logger.error(f"加载工具模块 {module_name} 失败: {str(e)}")

    # 获取所有已注册的工具
    tools = ToolRegistry.get_all_tools()
    logger.info(f"共加载了 {len(tools)} 个工具")

    return tools


# 导出工具注册表
__all__ = ["ToolRegistry", "BaseTool", "load_tools"]