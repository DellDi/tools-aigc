"""
处理工具调用的流式响应
"""

import asyncio
import json
import time
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from fastapi import Request
from fastapi.responses import StreamingResponse
from loguru import logger

from app.schemas.tools import OpenAIMessage, OpenAIToolCallResult


class StreamEvent(str, Enum):
    """流事件类型"""
    
    TOOL_CALL = "tool_call"  # 工具调用开始
    TOOL_RESULT = "tool_result"  # 工具调用结果
    MESSAGE = "message"  # 消息内容
    DONE = "done"  # 完成
    ERROR = "error"  # 错误


class StreamResponseHandler:
    """
    流式响应处理器
    支持 OpenAI 兼容的 SSE 格式
    """
    
    @staticmethod
    def format_sse_event(event_type: str, data: Union[Dict, str]) -> str:
        """
        格式化 SSE 事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            
        Returns:
            str: 格式化的 SSE 事件字符串
        """
        if isinstance(data, dict):
            data = json.dumps(data, ensure_ascii=False)
        
        return f"event: {event_type}\ndata: {data}\n\n"
    
    @staticmethod
    def create_delta_choice(
        role: str,
        content: Optional[str] = None,
        tool_calls: Optional[List[Dict]] = None,
        finish_reason: Optional[str] = None,
        index: int = 0
    ) -> Dict[str, Any]:
        """
        创建增量选择对象，与 OpenAI 兼容格式
        
        Args:
            role: 角色
            content: 内容
            tool_calls: 工具调用列表
            finish_reason: 完成原因
            index: 索引
            
        Returns:
            Dict: 选择对象
        """
        delta = {"role": role}
        if content is not None:
            delta["content"] = content
        if tool_calls is not None:
            delta["tool_calls"] = tool_calls
            
        choice = {
            "index": index,
            "delta": delta
        }
        
        if finish_reason is not None:
            choice["finish_reason"] = finish_reason
            
        return choice
    
    @staticmethod
    def create_stream_chunk(
        choices: List[Dict],
        model: str,
        id_prefix: str = "chatcmpl-"
    ) -> Dict[str, Any]:
        """
        创建流式块，与 OpenAI 兼容格式
        
        Args:
            choices: 选择列表
            model: 模型名称
            id_prefix: ID 前缀
            
        Returns:
            Dict: 流式块
        """
        chunk_id = f"{id_prefix}{str(time.time()).replace('.', '')}"
        return {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": choices
        }
    
    @staticmethod
    async def stream_tool_execution(
        request: Request,
        model: str,
        tool_calls: List[Dict],
        execute_tool_calls_func: Any,
        session_id: Optional[str] = None,
        output_format: str = "json"
    ) -> StreamingResponse:
        """
        流式执行工具并返回结果
        
        Args:
            request: 请求对象
            model: 模型名称
            tool_calls: 工具调用列表
            execute_tool_calls_func: 执行工具调用的函数
            session_id: 会话ID
            output_format: 输出格式
            
        Returns:
            StreamingResponse: 流式响应
        """
        async def generate() -> AsyncGenerator[str, None]:
            # 检查客户端是否已断开连接
            async def is_disconnected() -> bool:
                try:
                    return await request.is_disconnected()
                except Exception:
                    return True
            
            # 首先发送工具调用事件
            for i, tool_call in enumerate(tool_calls):
                # 每个工具调用先发送开始事件
                function_call = tool_call["function"]
                tool_call_data = {
                    "index": i,
                    "id": tool_call["id"],
                    "type": "function",
                    "function": {
                        "name": function_call["name"],
                        "arguments": function_call["arguments"]
                    }
                }
                
                # 创建工具调用开始事件
                choices = [StreamResponseHandler.create_delta_choice(
                    role="assistant",
                    tool_calls=[tool_call_data]
                )]
                
                chunk = StreamResponseHandler.create_stream_chunk(choices, model)
                yield StreamResponseHandler.format_sse_event("message", chunk)
                
                # 防止发送过快
                await asyncio.sleep(0.01)
                
                # 检查客户端是否断开
                if await is_disconnected():
                    logger.warning("客户端已断开连接，停止流式响应")
                    return
            
            # 执行工具调用
            try:
                # 每个工具按顺序执行并流式返回结果
                for tool_call in tool_calls:
                    # 单个工具调用的执行
                    single_result = await execute_tool_calls_func(
                        [tool_call],
                        session_id=session_id,
                        output_format=output_format
                    )
                    
                    # 发送工具结果
                    if single_result and len(single_result) > 0:
                        tool_result = single_result[0]
                        result_data = {
                            "role": "tool",
                            "tool_call_id": tool_result["tool_call_id"],
                            "content": tool_result["output"]
                        }
                        
                        # 创建工具结果事件
                        choices = [StreamResponseHandler.create_delta_choice(
                            role="tool",
                            content=tool_result["output"],
                            finish_reason="tool_calls"
                        )]
                        
                        chunk = StreamResponseHandler.create_stream_chunk(choices, model)
                        yield StreamResponseHandler.format_sse_event("message", chunk)
                    
                    # 暂停一下，防止发送过快
                    await asyncio.sleep(0.05)
                    
                    # 检查客户端是否断开
                    if await is_disconnected():
                        logger.warning("客户端已断开连接，停止流式响应")
                        return
                
                # 完成事件
                choices = [StreamResponseHandler.create_delta_choice(
                    role="assistant",
                    finish_reason="tool_calls"
                )]
                
                chunk = StreamResponseHandler.create_stream_chunk(choices, model)
                yield StreamResponseHandler.format_sse_event("message", chunk)
                
                # 最后发送 done 事件
                yield StreamResponseHandler.format_sse_event("done", {})
                
            except Exception as e:
                logger.exception(f"流式工具执行出错: {str(e)}")
                # 发送错误事件
                error_data = {"error": str(e)}
                yield StreamResponseHandler.format_sse_event("error", error_data)
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
            }
        )


async def create_streaming_response(
    request: Request,
    model: str,
    messages: List[Dict],
    tool_calls: Optional[List[Dict]] = None,
    execute_tool_calls_func = None,
    session_id: Optional[str] = None,
    output_format: str = "json"
) -> StreamingResponse:
    """
    创建流式响应
    
    Args:
        request: 请求对象
        model: 模型名称
        messages: 消息列表
        tool_calls: 工具调用列表，如果有的话
        execute_tool_calls_func: 执行工具调用的函数
        session_id: 会话ID
        output_format: 输出格式
        
    Returns:
        StreamingResponse: 流式响应
    """
    # 如果有工具调用，使用工具调用流
    if tool_calls and execute_tool_calls_func:
        return await StreamResponseHandler.stream_tool_execution(
            request=request,
            model=model,
            tool_calls=tool_calls,
            execute_tool_calls_func=execute_tool_calls_func,
            session_id=session_id,
            output_format=output_format
        )
    
    # 否则是普通对话流，但我们暂时不实现这部分（可扩展）
    # 这里仅作为占位符，实际项目中可能会调用 LLM 的流式 API
    async def generate() -> AsyncGenerator[str, None]:
        # 检查客户端是否已断开连接
        async def is_disconnected() -> bool:
            try:
                return await request.is_disconnected()
            except Exception:
                return True
                
        # 创建一个示例流式响应
        choices = [StreamResponseHandler.create_delta_choice(
            role="assistant",
            content="此版本暂不支持纯对话模式的流式输出，仅支持工具调用的流式执行。",
            finish_reason="stop"
        )]
        
        chunk = StreamResponseHandler.create_stream_chunk(choices, model)
        yield StreamResponseHandler.format_sse_event("message", chunk)
        
        # 完成事件
        yield StreamResponseHandler.format_sse_event("done", {})
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )
