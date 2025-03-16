"""
工具基类模块
"""

import asyncio
import inspect
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type, Union, get_type_hints

from pydantic import BaseModel, Field, create_model

from app.core.config import settings

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """工具执行结果"""

    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None


class BaseTool(ABC):
    """工具基类"""

    name: str
    description: str
    version: str = "1.0.0"
    parameters_schema: Optional[Type[BaseModel]] = None

    def __init__(self):
        """初始化工具"""
        if not hasattr(self, "name"):
            raise ValueError(f"{self.__class__.__name__} 必须定义 name 属性")

        if not hasattr(self, "description"):
            raise ValueError(f"{self.__class__.__name__} 必须定义 description 属性")

        # 如果没有定义参数模式，则自动从execute方法的类型注解生成
        if not self.parameters_schema:
            self._generate_parameters_schema()

    def _generate_parameters_schema(self) -> None:
        """从execute方法的类型注解生成参数模式"""
        execute_method = getattr(self, "execute")
        signature = inspect.signature(execute_method)
        type_hints = get_type_hints(execute_method)

        # 排除self参数
        parameters = {}
        for name, param in signature.parameters.items():
            if name == "self":
                continue

            # 获取参数类型和默认值
            param_type = type_hints.get(name, Any)
            default_value = ... if param.default is inspect.Parameter.empty else param.default

            # 获取参数描述（如果有）
            description = None
            if hasattr(self, f"_{name}_description"):
                description = getattr(self, f"_{name}_description")

            # 创建字段
            field = Field(default_value, description=description)
            parameters[name] = (param_type, field)

        # 创建参数模式
        model_name = f"{self.__class__.__name__}Parameters"
        self.parameters_schema = create_model(
            model_name,
            **parameters
        )

    def to_openai_function(self) -> Dict[str, Any]:
        """转换为OpenAI function格式"""
        if not self.parameters_schema:
            return {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }

        # 获取参数模式的JSON模式
        schema = self.parameters_schema.model_json_schema()

        # 构建OpenAI function格式
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema
            }
        }

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具（抽象方法）"""
        pass

    async def run(self, **kwargs) -> ToolResult:
        """运行工具，包含超时处理"""
        try:
            # 使用超时机制运行工具
            result = await asyncio.wait_for(
                self.execute(**kwargs),
                timeout=settings.TOOLS_TIMEOUT
            )
            return result
        except asyncio.TimeoutError:
            logger.error(f"工具 {self.name} 执行超时")
            return ToolResult(
                success=False,
                error=f"工具执行超时（{settings.TOOLS_TIMEOUT}秒）"
            )
        except Exception as e:
            logger.exception(f"工具 {self.name} 执行出错: {str(e)}")
            return ToolResult(
                success=False,
                error=f"工具执行出错: {str(e)}"
            )


class ToolRegistry:
    """工具注册表"""

    _tools: Dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool_instance: BaseTool) -> None:
        """注册工具"""
        if tool_instance.name in cls._tools:
            logger.warning(f"工具 {tool_instance.name} 已存在，将被覆盖")

        cls._tools[tool_instance.name] = tool_instance
        logger.info(f"工具 {tool_instance.name} 已注册")

    @classmethod
    def get_tool(cls, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return cls._tools.get(name)

    @classmethod
    def get_all_tools(cls) -> List[BaseTool]:
        """获取所有工具"""
        return list(cls._tools.values())

    @classmethod
    def get_openai_functions(cls) -> List[Dict[str, Any]]:
        """获取所有工具的OpenAI function格式"""
        return [tool.to_openai_function() for tool in cls._tools.values()]