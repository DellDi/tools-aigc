"""
工具相关的数据模型
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ToolCallRequest(BaseModel):
    """工具调用请求"""

    name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "echo",
                "parameters": {
                    "message": "Hello, Tools-AIGC!",
                    "prefix": "Echo:",
                    "suffix": "- From Client Example",
                },
            }
        }


class ToolCallResponse(BaseModel):
    """工具调用响应"""

    name: str = Field(..., description="工具名称")
    success: bool = Field(..., description="调用是否成功")
    data: Optional[Any] = Field(default=None, description="调用结果数据")
    error: Optional[str] = Field(default=None, description="错误信息")


class ToolInfo(BaseModel):
    """工具信息"""

    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    version: str = Field(..., description="工具版本")
    parameters_schema: Dict[str, Any] = Field(..., description="参数模式")


class ListToolsResponse(BaseModel):
    """工具列表响应"""

    tools: List[ToolInfo] = Field(..., description="工具列表")


class OpenAIFunctionCall(BaseModel):
    """OpenAI Function Call请求"""

    name: str = Field(..., description="函数名称")
    arguments: str = Field(..., description="函数参数（JSON字符串）")


class OpenAIToolCall(BaseModel):
    """OpenAI Tool Call"""

    id: str = Field(..., description="工具调用ID")
    type: str = Field(default="function", description="工具类型")
    function: OpenAIFunctionCall = Field(..., description="函数调用")


class OpenAIToolCallResult(BaseModel):
    """OpenAI Tool Call结果"""

    tool_call_id: str = Field(..., description="工具调用ID")
    output: str = Field(..., description="工具调用输出")


class OpenAIMessage(BaseModel):
    """OpenAI消息"""

    role: str = Field(..., description="角色")
    content: Optional[str] = Field(default=None, description="内容")
    name: Optional[str] = Field(default=None, description="名称")
    tool_calls: Optional[List[OpenAIToolCall]] = Field(
        default=None, description="工具调用"
    )
    tool_call_id: Optional[str] = Field(default=None, description="工具调用ID")


class OpenAIToolsRequest(BaseModel):
    """OpenAI Tools请求"""

    model: str = Field(..., description="模型名称")
    messages: List[OpenAIMessage] = Field(..., description="消息列表")
    tools: Optional[List[Dict[str, Any]]] = Field(default=None, description="工具列表")
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(
        default="auto", description="工具选择"
    )
    temperature: Optional[float] = Field(default=0.7, description="温度")
    max_tokens: Optional[int] = Field(default=None, description="最大令牌数")
    stream: Optional[bool] = Field(default=False, description="是否流式输出")


class OpenAIToolsResponse(BaseModel):
    """OpenAI Tools响应"""

    id: str = Field(..., description="响应ID")
    object: str = Field(..., description="对象类型")
    created: int = Field(..., description="创建时间")
    model: str = Field(..., description="模型名称")
    choices: List[Dict[str, Any]] = Field(..., description="选择列表")
    usage: Dict[str, int] = Field(..., description="使用情况")
