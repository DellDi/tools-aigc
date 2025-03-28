"""
工具相关的API端点 - 支持纯对话、纯工具调用和混合模式
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Optional, Dict, List, Any

from fastapi import APIRouter, HTTPException, Path, Header, Request
import httpx

from app.core.config import settings
from app.core.message_processor import process_messages, handle_hybrid_mode
from app.core.llm_service import forward_to_llm_service, format_llm_response

from app.schemas.tools import (
    ListToolsResponse,
    OpenAIToolsRequest,
    OpenAIToolsResponse,
    ToolCallRequest,
    ToolCallResponse,
    ToolInfo,
)
from app.tools import ToolRegistry


async def handle_conversation(messages: List[Dict], model: str) -> Dict:
    """
    处理纯对话模式请求
    
    Args:
        messages: 消息列表
        model: 模型名称
    
    Returns:
        Dict: OpenAI兼容格式的对话响应
    """
    try:
        # 转发到LLM服务并获取响应
        llm_response = await forward_to_llm_service(model, messages)
        
        # 格式化响应为OpenAI兼容格式
        formatted_response = format_llm_response(llm_response, model)
        
        return formatted_response
    except Exception as e:
        logger.exception(f"处理对话请求出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理对话请求出错: {str(e)}")

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


@router.post("/openai/v1/chat/completions", response_model=OpenAIToolsResponse, summary="OpenAI兼容的统一端点")
async def openai_tools(
    request: OpenAIToolsRequest, 
    authorization: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
    x_output_format: Optional[str] = Header(None, alias="X-Output-Format"),
):
    """
    OpenAI兼容的统一API端点

    此端点模拟OpenAI的chat/completions API，支持以下模式：
    1. 纯对话模式：处理普通对话请求
    2. 纯工具调用模式：处理有明确工具调用的请求
    3. 混合模式：情景理解并自动添加工具调用
    4. 双模式支持：支持客户端自定义工具和服务端预定义工具
    
    支持API Key验证和模型映射
    """
    # 验证API Key
    api_key = None
    if authorization:
        if authorization.startswith("Bearer "):
            api_key = authorization.replace("Bearer ", "")

    # 检查API Key是否有效
    if api_key:
        # 检查是否是预设的API Key前缀
        api_key_prefix = api_key.split("-")[0] + "-" + api_key.split("-")[1] if "-" in api_key else ""
        if api_key_prefix and api_key_prefix in settings.LLM_API_KEYS:
            # 使用对应的API Key
            logger.info(f"使用API Key前缀: {api_key_prefix}")
        else:
            # 如果不是预设前缀，检查是否是完整的API Key
            valid_key = False
            for key_name, key_value in settings.LLM_API_KEYS.items():
                if api_key == key_value and key_value:
                    valid_key = True
                    break

            if not valid_key:
                logger.warning(f"无效的API Key: {api_key[:10]}...")
                raise HTTPException(
                    status_code=401,
                    detail="无效的API Key"
                )

    # 模型映射
    original_model = request.model
    mapped_model = settings.LLM_MODEL_MAPPING.get(original_model, original_model)
    if mapped_model != original_model:
        logger.info(f"模型映射: {original_model} -> {mapped_model}")
    
    # 获取服务端预定义工具列表
    server_tools_list = []
    tools = ToolRegistry.get_all_tools()
    for tool in tools:
        if tool.parameters_schema:
            parameters_schema = tool.parameters_schema.model_json_schema()
        else:
            parameters_schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
        
        server_tools_list.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": parameters_schema
            }
        })
    
    # 处理客户端传入的工具列表
    client_tools_list = request.tools if request.tools else []
    
    # 判断工具来源和处理模式
    user_specified_tools = len(client_tools_list) > 0
    tool_choice_manual = request.tool_choice != "auto" and request.tool_choice is not None
    
    # 合并工具列表（优先使用客户端工具）
    available_tools_list = []
    tool_name_map = {}
    
    # 如果客户端指定了工具，优先使用客户端工具
    if user_specified_tools:
        available_tools_list = client_tools_list.copy()
        # 记录客户端工具名称，避免重复
        for tool in client_tools_list:
            if tool.get("type") == "function" and tool.get("function") and tool["function"].get("name"):
                tool_name_map[tool["function"]["name"]] = True
    
    # 添加服务端预定义工具（如果没有被客户端覆盖）
    for tool in server_tools_list:
        if tool.get("function") and tool["function"].get("name") and tool["function"]["name"] not in tool_name_map:
            available_tools_list.append(tool)
            tool_name_map[tool["function"]["name"]] = True
    
    # 记录处理模式
    logger.info(f"工具处理模式 - 客户端工具: {user_specified_tools}, 手动工具选择: {tool_choice_manual}")
    
    # 分析请求类型并处理消息
    messages = [msg.model_dump() for msg in request.messages]
    mode, processed_messages = await process_messages(messages, available_tools_list)
    
    logger.info(f"请求类型: {mode}")
    
    # 初始化或获取会话
    from app.core.session import session_manager
    
    session_id = x_session_id
    output_format = x_output_format or "json"
    
    # 获取或创建会话
    if session_id:
        session = session_manager.get_or_create_session(session_id)
        # 将消息添加到会话历史
        for msg in request.messages:
            session.add_message(msg.model_dump())
        logger.info(f"使用现有会话: {session_id}, 消息数: {len(session.get_messages())}")
    else:
        # 创建一个新会话
        session = session_manager.create_session()
        session_id = session.session_id
        # 添加初始消息
        for msg in request.messages:
            session.add_message(msg.model_dump())
        logger.info(f"创建新会话: {session_id}")
    
    # 标准两阶段模式：客户端期望看到工具调用中间态
    if tool_choice_manual:
        return await handle_standard_tool_workflow(
            processed_messages, 
            available_tools_list, 
            mapped_model, 
            mode, 
            session_id=session_id, 
            output_format=output_format
        )
    
    # 自动模式：屏蔽中间态，直接返回结果
    return await handle_auto_tool_workflow(
        processed_messages, 
        available_tools_list, 
        mapped_model, 
        mode, 
        session_id=session_id, 
        output_format=output_format
    )


async def handle_standard_tool_workflow(
    messages: List[Dict], 
    available_tools: List[Dict], 
    model: str, 
    mode: str,
    session_id: Optional[str] = None,
    output_format: str = "json"
) -> OpenAIToolsResponse:
    """
    处理标准OpenAI兼容的工具调用流程（两阶段）
    此模式与OpenAI API完全兼容，适用于客户端需要自行处理工具调用的场景
    
    Args:
        messages: 处理后的消息列表
        available_tools: 可用工具列表
        model: 模型名称
        mode: 请求模式（conversation/hybrid/tool_call）
        
    Returns:
        OpenAIToolsResponse: 符合OpenAI格式的响应
    """
    # 如果已经是工具调用模式，直接处理工具
    if mode == "tool_call":
        # 获取最后一条消息中的工具调用
        last_message = messages[-1]
        if not last_message.get("tool_calls"):
            # 返回错误，工具调用信息缺失
            raise HTTPException(status_code=400, detail="工具调用信息缺失")

        # 构建工具调用响应
        return OpenAIToolsResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:10]}",
            object="chat.completion",
            created=int(time.time()),
            model=model,
            choices=[
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": last_message.get("tool_calls"),
                    },
                    "finish_reason": "tool_calls"
                }
            ],
            usage={
                "prompt_tokens": len(str(messages)),
                "completion_tokens": len(str(last_message.get("tool_calls", []))),
                "total_tokens": len(str(messages)) + len(str(last_message.get("tool_calls", [])))
            }
        )
    
    # 对话或混合模式：提取可能的工具调用
    if mode == "conversation":
        # 处理纯对话模式
        return await handle_conversation(messages, model)
    else:  # mode == "hybrid"
        # 处理混合模式
        conversation_response = await handle_conversation(messages, model)
        return await handle_hybrid_mode(messages, conversation_response, available_tools)


async def handle_auto_tool_workflow(
    messages: List[Dict], 
    available_tools: List[Dict], 
    model: str, 
    mode: str,
    session_id: Optional[str] = None,
    output_format: str = "json"
) -> OpenAIToolsResponse:
    """
    处理自动工具调用流程（屏蔽中间态）
    此模式对客户端屏蔽工具调用细节，直接返回最终结果
    
    Args:
        messages: 处理后的消息列表
        available_tools: 可用工具列表
        model: 模型名称
        mode: 请求模式（conversation/hybrid/tool_call）
        
    Returns:
        OpenAIToolsResponse: 符合OpenAI格式的最终响应
    """
    # 处理现有的工具调用
    if mode == "tool_call":
        # 获取最后一条消息中的工具调用
        last_message = messages[-1]
        if not last_message.get("tool_calls"):
            # 没有工具调用，当作对话处理
            return await handle_conversation(messages, model)

        # 执行工具调用
        tool_call_results = await execute_tool_calls(
            last_message["tool_calls"],
            session_id=session_id,
            output_format=output_format
        )
        
        # 将工具调用结果加入到消息列表中
        for result in tool_call_results:
            messages.append({
                "role": "tool",
                "tool_call_id": result["tool_call_id"],
                "content": result["output"]
            })
            
        # 生成最终回复
        final_response = await handle_conversation(messages, model)
        return final_response
    
    # 对话模式直接返回
    if mode == "conversation":
        return await handle_conversation(messages, model)
    
    # 混合模式
    # 第一步：检测是否需要工具调用
    conversation_response = await handle_conversation(messages, model)
    hybrid_data = await handle_hybrid_mode(messages, conversation_response, available_tools)
    
    # 检查是否生成了工具调用
    first_choice = hybrid_data.choices[0] if hybrid_data.choices else None
    first_message = first_choice.message if first_choice else None
    tool_calls = first_message.tool_calls if first_message else None
    
    if not tool_calls:
        # 没有工具调用，直接返回对话结果
        return conversation_response
    
    # 第二步：执行工具调用
    tool_call_results = await execute_tool_calls(
        tool_calls,
        session_id=session_id,
        output_format=output_format
    )
    
    # 第三步：构建完整的上下文
    full_messages = messages.copy()
    # 添加助手的工具调用消息
    full_messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": tool_calls
    })
    # 添加工具调用结果
    for result in tool_call_results:
        full_messages.append({
            "role": "tool",
            "tool_call_id": result["tool_call_id"],
            "content": result["output"]
        })
    
    # 第四步：生成最终回复
    final_response = await handle_conversation(full_messages, model)
    return final_response


async def execute_tool_calls(tool_calls: List[Dict], session_id: Optional[str] = None, output_format: str = "json") -> List[Dict]:
    """
    执行工具调用并返回结果
    
    Args:
        tool_calls: 工具调用列表
        session_id: 会话ID，用于会话级工具权限管理
        output_format: 输出格式 (json, markdown, text, html)
        
    Returns:
        List[Dict]: 工具调用结果列表
    """
    # 导入缓存、会话管理和格式化模块
    from app.core.cache import tool_cache
    from app.core.session import session_manager
    from app.core.formatter import tool_formatter, OutputFormat
    
    # 格式化选项
    try:
        format_option = OutputFormat(output_format.lower())
    except ValueError:
        format_option = OutputFormat.JSON
    
    # 尝试获取会话
    session = None
    if session_id:
        session = session_manager.get_session(session_id)
    
    tool_call_results = []
    for tool_call in tool_calls:
        # 获取工具名称和参数
        function_call = tool_call["function"]
        tool_name = function_call["name"]

        try:
            # 解析参数
            arguments = json.loads(function_call["arguments"])
            
            # 检查会话级工具权限
            if session and not session.is_tool_allowed(tool_name):
                raise PermissionError(f"会话 {session_id} 没有权限使用工具 {tool_name}")

            # 检查缓存
            cached_result = tool_cache.get(tool_name, arguments)
            if cached_result:
                logger.info(f"使用缓存结果: {tool_name}")
                result = cached_result
            else:
                # 获取工具
                tool = ToolRegistry.get_tool(tool_name)
                if not tool:
                    raise ValueError(f"工具 {tool_name} 不存在")

                # 调用工具
                logger.info(f"执行工具调用: {tool_name} 参数: {arguments}")
                result = await tool.run(**arguments)
                
                # 缓存结果（仅缓存成功的结果）
                if result.success:
                    tool_cache.set(tool_name, arguments, result)
            
            # 记录工具调用到会话历史
            if session:
                session.add_message({
                    "role": "function",
                    "name": tool_name,
                    "content": json.dumps({
                        "arguments": arguments,
                        "result": {
                            "success": result.success,
                            "data": result.data,
                            "error": result.error
                        }
                    }, ensure_ascii=False)
                })

            # 构建并格式化结果
            result_dict = {
                "success": result.success,
                "data": result.data,
                "error": result.error
            }
            
            # 应用格式化（保留原始JSON以供LLM处理）
            formatted_result = tool_formatter.format_result(
                result_dict, 
                output_format=format_option,
                include_metadata=True
            )
            
            # 添加元数据
            metadata = {
                "tool_name": tool_name,
                "cached": cached_result is not None,
                "format": output_format,
                "timestamp": time.time()
            }
            
            # 构建输出
            output = json.dumps({
                "result": result_dict,
                "formatted": formatted_result,
                "metadata": metadata
            }, ensure_ascii=False)

            tool_call_results.append({
                "tool_call_id": tool_call["id"],
                "output": output
            })

        except Exception as e:
            error_message = str(e)
            logger.exception(f"处理工具调用 {tool_name} 出错: {error_message}")
            
            error_result = {
                "success": False,
                "data": None,
                "error": f"处理工具调用出错: {error_message}"
            }
            
            # 格式化错误信息
            formatted_error = tool_formatter.format_result(
                error_result,
                output_format=format_option,
                include_metadata=True
            )
            
            output = json.dumps({
                "result": error_result,
                "formatted": formatted_error,
                "metadata": {
                    "tool_name": tool_name,
                    "error": True,
                    "format": output_format,
                    "timestamp": time.time()
                }
            }, ensure_ascii=False)
            
            tool_call_results.append({
                "tool_call_id": tool_call["id"],
                "output": output
            })
            
            # 记录错误到会话历史
            if session:
                session.add_message({
                    "role": "function",
                    "name": tool_name,
                    "content": json.dumps({
                        "error": error_message
                    }, ensure_ascii=False)
                })
    
    return tool_call_results
