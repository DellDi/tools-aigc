"""
Echo工具 - 用于测试工具调用功能
"""

import logging
from typing import Any, Optional

from app.tools.base import BaseTool, ToolRegistry, ToolResult

logger = logging.getLogger(__name__)


class EchoTool(BaseTool):
    """Echo工具，返回输入的内容"""

    name = "echo"
    description = "返回输入的内容，用于测试工具调用功能"

    # 参数描述
    _message_description = "要返回的消息内容"
    _prefix_description = "可选的消息前缀"
    _suffix_description = "可选的消息后缀"

    async def execute(
        self,
        message: str,
        prefix: Optional[str] = None,
        suffix: Optional[str] = None
    ) -> ToolResult:
        """
        执行Echo操作

        Args:
            message: 要返回的消息内容
            prefix: 可选的消息前缀
            suffix: 可选的消息后缀

        Returns:
            ToolResult: 包含处理后的消息
        """
        try:
            # 构建结果消息
            result_message = message

            if prefix:
                result_message = f"{prefix} {result_message}"

            if suffix:
                result_message = f"{result_message} {suffix}"

            # 返回结果
            return ToolResult(
                success=True,
                data={
                    "original_message": message,
                    "processed_message": result_message,
                    "prefix": prefix,
                    "suffix": suffix
                }
            )

        except Exception as e:
            logger.exception(f"Echo工具执行出错: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Echo工具执行出错: {str(e)}"
            )


# 注册工具
ToolRegistry.register(EchoTool())