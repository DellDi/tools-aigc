"""
工具相关的API端点
"""

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Path

from app.schemas.tools import (
    ListToolsResponse,
    OpenAIToolsRequest,
    OpenAIToolsResponse,
    ToolCallRequest,
    ToolCallResponse,
    ToolInfo,
)
from app.tools import ToolRegistry

logger = logging.getLogger("uvicorn")

router = APIRouter()


@router.get("", response_model=ListToolsResponse, summary="获取所有工具")
async def list_tools():
    """
    获取所有可用工具的列表
    """

    tools = ToolRegistry.get_all_tools()

    # 转换为响应格式
    tool_infos = []
    for tool in tools:
        # 获取参数模式
        if tool.parameters_schema:
            parameters_schema = tool.parameters_schema.model_json_schema()
        else:
            parameters_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }

        tool_infos.append(
            ToolInfo(
                name=tool.name,
                description=tool.description,
                version=tool.version,
                parameters_schema=parameters_schema
            )
        )

    return ListToolsResponse(tools=tool_infos)


@router.post("/{tool_name}", response_model=ToolCallResponse, summary="调用工具")
async def call_tool(
    tool_name: str = Path(..., description="工具名称"),
    request: ToolCallRequest = None
):
    """
    调用指定的工具
    """
    logger.info(f"调用工具 {tool_name}，参数: {request.parameters if request else None}")

    # 获取工具
    tool = ToolRegistry.get_tool(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"工具 {tool_name} 不存在")

    # 如果没有提供请求体，则使用空参数
    if request is None:
        request = ToolCallRequest(name=tool_name, parameters={})

    # 验证工具名称
    if request.name != tool_name:
        raise HTTPException(
            status_code=400,
            detail=f"请求中的工具名称 {request.name} 与路径中的工具名称 {tool_name} 不一致"
        )

    # 调用工具
    try:
        logger.info(f"开始执行工具: {tool_name}")
        # 设置较短的超时时间
        result = await asyncio.wait_for(tool.execute(**request.parameters), timeout=5.0)
        logger.info(f"工具执行完成: {tool_name}")

        # 构建响应
        response = ToolCallResponse(
            name=tool_name,
            success=result.success,
            data=result.data,
            error=result.error
        )
        logger.info(f"响应已构建: {tool_name}")
        return response
    except asyncio.TimeoutError:
        logger.error(f"工具 {tool_name} 执行超时")
        return ToolCallResponse(
            name=tool_name,
            success=False,
            error="工具执行超时（5秒）"
        )
    except Exception as e:
        logger.exception(f"调用工具 {tool_name} 出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"调用工具出错: {str(e)}")


@router.post("/openai/v1/chat/completions", response_model=OpenAIToolsResponse, summary="OpenAI兼容的工具调用")
async def openai_tools(request: OpenAIToolsRequest):
    """
    OpenAI兼容的工具调用API

    此端点模拟OpenAI的chat/completions API，但只处理工具调用部分
    """
    # 检查是否有工具调用
    last_message = request.messages[-1]
    if last_message.role != "assistant" or not last_message.tool_calls:
        # 返回错误，因为我们只处理工具调用
        raise HTTPException(
            status_code=400,
            detail="此API仅处理工具调用，请确保最后一条消息是助手消息且包含工具调用"
        )

    # 处理工具调用
    tool_call_results = []
    for tool_call in last_message.tool_calls:
        # 获取工具名称和参数
        function_call = tool_call.function
        tool_name = function_call.name

        try:
            # 解析参数
            arguments = json.loads(function_call.arguments)

            # 获取工具
            tool = ToolRegistry.get_tool(tool_name)
            if not tool:
                raise ValueError(f"工具 {tool_name} 不存在")

            # 调用工具
            result = await tool.run(**arguments)

            # 构建结果
            output = json.dumps(
                {
                    "success": result.success,
                    "data": result.data,
                    "error": result.error
                },
                ensure_ascii=False
            )

            tool_call_results.append({
                "tool_call_id": tool_call.id,
                "output": output
            })

        except Exception as e:
            logger.exception(f"处理工具调用 {tool_name} 出错: {str(e)}")
            tool_call_results.append({
                "tool_call_id": tool_call.id,
                "output": json.dumps(
                    {
                        "success": False,
                        "data": None,
                        "error": f"处理工具调用出错: {str(e)}"
                    },
                    ensure_ascii=False
                )
            })

    # 构建OpenAI兼容的响应
    return OpenAIToolsResponse(
        id=f"chatcmpl-{tool_call.id}",
        object="chat.completion",
        created=1234567890,  # 使用固定值
        model=request.model,
        choices=[
            {
                "index": 0,
                "message": {
                    "role": "tool",
                    "content": None,
                    "tool_calls": None,
                    "tool_call_id": None
                },
                "finish_reason": "tool_calls"
            }
        ],
        usage={
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    )
