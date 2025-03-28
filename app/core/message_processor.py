"""
消息处理模块 - 支持对话、工具调用和混合模式
"""

import json
import logging
import uuid
from typing import Dict, List, Tuple, Optional, Any

import httpx

from app.core.config import settings
from app.tools import ToolRegistry

logger = logging.getLogger(__name__)


async def process_messages(messages: List[Dict], available_tools: List[Dict] = None) -> Tuple[str, List[Dict]]:
    """
    分析请求类型并处理消息
    
    Args:
        messages: 消息列表
        available_tools: 可用工具列表，格式为OpenAI工具格式
    
    Returns:
        Tuple[str, List[Dict]]: (模式类型, 处理后的消息)
        模式类型: "conversation", "tool_call", "hybrid"
    """
    # 检查消息列表是否为空
    if not messages:
        return "conversation", messages
    
    # 检查最后一条消息
    last_message = messages[-1]
    
    # 如果最后一条消息是assistant且包含tool_calls，直接判定为工具调用模式
    if (last_message.get("role") == "assistant" and 
            last_message.get("tool_calls")):
        return "tool_call", messages
    
    # 如果没有可用工具，直接使用对话模式
    if not available_tools:
        return "conversation", messages
    
    # 检查是否有明确的工具调用意图
    has_tool_intent, tool_info = await detect_tool_intent(messages, available_tools)
    
    if has_tool_intent and tool_info:
        # 有明确工具调用意图，生成工具调用消息
        tool_call_msg = await generate_tool_call_message(tool_info)
        if tool_call_msg:
            # 添加工具调用消息
            processed_messages = messages + [tool_call_msg]
            return "tool_call", processed_messages
        else:
            # 有工具调用意图但无法生成具体工具调用，使用混合模式
            return "hybrid", messages
    
    # 默认为对话模式
    return "conversation", messages


async def detect_tool_intent(messages: List[Dict], available_tools: List[Dict] = None) -> Tuple[bool, Optional[Dict]]:
    """
    检测用户消息中是否有工具调用意图
    
    Args:
        messages: 消息列表
        available_tools: 可用工具列表，格式为OpenAI工具格式
    
    Returns:
        Tuple[bool, Optional[Dict]]: (是否有工具调用意图, 工具信息)
        工具信息格式: {"tool": "工具名称", "parameters": {...}}
    """
    # 获取最后一条用户消息
    last_user_msg = None
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break
    
    if not last_user_msg:
        return False, None
    
    # 首先尝试使用LLM辅助提取
    try:
        # 如果有可用工具定义，尝试使用LLM进行参数提取
        if available_tools:
            llm_result = await extract_parameters_with_llm(last_user_msg, available_tools)
            if llm_result and llm_result.get("tool") and llm_result.get("parameters"):
                logger.info(f"LLM参数提取成功: {llm_result}")
                return True, llm_result
    except Exception as e:
        logger.warning(f"LLM参数提取失败: {str(e)}，回退到规则引擎")
    
    # LLM提取失败或不可用，回退到规则引擎
    return await detect_tool_intent_by_rules(last_user_msg)


async def detect_tool_intent_by_rules(last_user_msg: str) -> Tuple[bool, Optional[Dict]]:
    """
    使用规则引擎检测工具调用意图（作为备份方案）
    
    Args:
        last_user_msg: 用户消息内容
    
    Returns:
        Tuple[bool, Optional[Dict]]: (是否有工具调用意图, 工具信息)
    """
    # 关键词匹配（针对常见工具）
    tool_keywords = {
        "weather": ["天气", "气温", "下雨", "温度", "humidity", "气候", "weather"],
        "echo": ["回声", "复述", "echo", "repeat"],
        "search": ["搜索", "查询", "查找", "search"]
    }
    
    # 提取常见城市名称（用于天气工具）
    cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "武汉", "西安", "南京", 
              "beijing", "shanghai", "guangzhou", "shenzhen"]
    
    # 城市提取辅助函数
    def extract_city(text: str) -> str:
        for city in cities:
            if city in text.lower():
                return city
        return "北京"  # 默认城市
    
    # 初始化工具信息
    tool_info = None
    
    # 检查是否匹配任何工具关键词
    for tool_name, keywords in tool_keywords.items():
        if any(keyword in last_user_msg.lower() for keyword in keywords):
            # 根据工具类型构建参数
            if tool_name == "weather":
                city = extract_city(last_user_msg)
                tool_info = {
                    "tool": "weather",
                    "parameters": {
                        "city": city,
                        "country": "CN" if any(c in "京沪广深杭成重武西南" for c in city) else "US"
                    }
                }
            elif tool_name == "echo":
                tool_info = {
                    "tool": "echo",
                    "parameters": {
                        "message": last_user_msg
                    }
                }
            elif tool_name == "search":
                query = last_user_msg.replace("搜索", "").replace("查询", "").replace("查找", "").strip()
                tool_info = {
                    "tool": "search",
                    "parameters": {
                        "query": query
                    }
                }
            
            # 找到匹配的工具就返回
            if tool_info:
                return True, tool_info
    
    # 没有检测到工具调用意图
    return False, None


async def extract_parameters_with_llm(user_message: str, available_tools: List[Dict]) -> Optional[Dict]:
    """
    使用LLM提取工具参数
    
    Args:
        user_message: 用户消息
        available_tools: 可用工具列表，格式为OpenAI工具格式
    
    Returns:
        Optional[Dict]: 提取的工具信息和参数
    """
    # 选择用于参数提取的LLM服务
    tool_extractor_model = settings.TOOL_EXTRACTOR_MODEL or "gpt-3.5-turbo"  # 默认使用gpt-3.5-turbo提取参数
    api_key = settings.LLM_API_KEYS.get(tool_extractor_model) or settings.LLM_API_KEYS.get("default", "")
    
    if not api_key:
        logger.warning("未配置工具参数提取所需的API密钥")
        return None
    
    # 准备工具定义
    tools_definition = json.dumps(available_tools, ensure_ascii=False, indent=2)
    
    # 构建提示词
    prompt = f"""
    你是一个AI助手，需要从用户消息中提取出应该使用的工具和参数。
    下面是可用的工具列表:
    {tools_definition}
    
    用户消息: "{user_message}"
    
    你的任务是确定用户是否想要使用某个工具，如果是，请提取出对应的工具名称和参数。
    返回结果格式必须是严格的JSON，包含'tool'和'parameters'字段，例如: 
    {{"tool": "weather", "parameters": {{"city": "北京", "country": "CN"}}}}
    如果无法确定用户想要使用的工具，请返回: {{"tool": null, "parameters": null}}
    只返回JSON，不要有任何其他说明文字。
    """
    
    # 构建API请求
    api_url = "https://api.openai.com/v1/chat/completions"  # 可能需要根据实际模型调整
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": tool_extractor_model,
        "messages": [
            {"role": "system", "content": "你是一个提取工具调用参数的助手。根据用户消息提取出适合的工具名称和参数。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,  # 低温度提高准确性
        "max_tokens": 500
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 尝试解析LLM返回的JSON
            try:
                # 清理内容，确保只有JSON部分
                content = content.strip()
                if content.startswith("```json"):
                    content = content.split("```json", 1)[1]
                if content.endswith("```"):
                    content = content.rsplit("```", 1)[0]
                content = content.strip()
                
                tool_info = json.loads(content)
                
                # 验证格式是否正确
                if "tool" in tool_info and "parameters" in tool_info:
                    if tool_info["tool"] is None:
                        return None  # 未检测到工具调用意图
                    return tool_info
            except json.JSONDecodeError as e:
                logger.warning(f"LLM返回内容解析失败: {str(e)}\n内容: {content}")
                return None
    except Exception as e:
        logger.warning(f"调用LLM提取参数失败: {str(e)}")
        return None
    
    return None


async def generate_tool_call_message(tool_info: Dict) -> Optional[Dict]:
    """
    根据工具信息生成工具调用消息
    
    Args:
        tool_info: 工具信息，包含工具名称和参数
    
    Returns:
        Optional[Dict]: 工具调用消息，格式符合OpenAI规范
    """
    try:
        tool_name = tool_info["tool"]
        parameters = tool_info["parameters"]
        
        # 验证工具是否存在
        tool = ToolRegistry.get_tool(tool_name)
        if not tool:
            logger.warning(f"工具 {tool_name} 不存在")
            return None
        
        # 构建工具调用消息
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": f"call_{uuid.uuid4().hex[:8]}",
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": json.dumps(parameters, ensure_ascii=False)
                }
            }]
        }
    except Exception as e:
        logger.exception(f"生成工具调用消息失败: {str(e)}")
        return None


async def handle_hybrid_mode(messages: List[Dict], conversation_response: Dict, available_tools: List[Dict] = None) -> Dict:
    """
    处理混合模式：分析对话回复中是否包含工具调用意图
    
    Args:
        messages: 原始消息列表
        conversation_response: 对话模式生成的响应
        available_tools: 可用工具列表，格式为OpenAI工具格式
    
    Returns:
        Dict: 处理后的响应
    """
    try:
        # 从对话响应中提取回复内容
        response_content = conversation_response.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not response_content:
            return conversation_response
        
        # 构建新的消息列表，包含对话回复
        new_messages = messages + [{
            "role": "assistant",
            "content": response_content
        }]
        
        # 检测回复中是否包含工具调用意图
        has_tool_intent, tool_info = await detect_tool_intent(new_messages, available_tools)
        
        if has_tool_intent and tool_info:
            # 生成工具调用
            tool_call_msg = await generate_tool_call_message(tool_info)
            
            if tool_call_msg and tool_call_msg.get("tool_calls"):
                # 添加工具调用信息到响应中
                conversation_response["choices"][0]["message"]["tool_calls"] = tool_call_msg["tool_calls"]
                conversation_response["choices"][0]["message"]["content"] = (
                    f"{response_content}\n\n[系统自动检测到工具调用意图，将执行工具调用]"
                )
                conversation_response["choices"][0]["finish_reason"] = "tool_calls"
        
        return conversation_response
    except Exception as e:
        logger.exception(f"处理混合模式失败: {str(e)}")
        return conversation_response
