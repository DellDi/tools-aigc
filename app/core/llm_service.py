"""
LLM服务模块 - 处理与大语言模型交互的核心功能
"""

import json
import logging
import time
from typing import Dict, List, Any, Optional

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


async def forward_to_llm_service(model_id: str, messages: List[Dict]) -> Dict:
    """
    将请求转发到实际的LLM服务
    
    Args:
        model_id: 模型ID
        messages: 消息列表
    
    Returns:
        Dict: LLM服务的响应
    """
    try:
        # 根据模型ID确定API Key和服务URL
        api_key = get_api_key_for_model(model_id)
        service_url = get_service_url_for_model(model_id)
        
        if not api_key or not service_url:
            raise ValueError(f"无法找到模型{model_id}的API Key或服务URL")
            
        # 构建请求体
        request_body = {
            "model": model_id,
            "messages": messages,
            "temperature": 0.3,
            "stream": False
        }
        
        # 设置请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 发送请求
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                service_url,
                headers=headers,
                json=request_body
            )
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP错误: {str(e)}")
        raise HTTPException(status_code=e.response.status_code, detail=f"LLM服务错误: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"请求错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"请求LLM服务失败: {str(e)}")
    except Exception as e:
        logger.exception(f"调用LLM服务出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"调用LLM服务出错: {str(e)}")


def get_api_key_for_model(model_id: str) -> str:
    """根据模型ID获取相应的API Key"""
    # 先检查是否有完全匹配
    if model_id in settings.LLM_API_KEYS:
        return settings.LLM_API_KEYS[model_id]
        
    # 检查前缀匹配
    for prefix, key in settings.LLM_API_KEYS.items():
        if model_id.startswith(prefix) and key:
            return key
            
    # 默认返回通用API Key
    return settings.LLM_API_KEYS.get("default", "")
    

def get_service_url_for_model(model_id: str) -> str:
    """根据模型ID获取相应的服务URL"""
    model_services = {
        "qwen": "https://dashscope.aliyuncs.com",
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
    }
    
    # 根据模型ID的前缀匹配服务URL
    for prefix, url in model_services.items():
        if model_id.startswith(prefix):
            return url
            
    # 默认返回Qwen服务URL
    return model_services["qwen"]
    

def format_llm_response(llm_response: Dict, model_id: str) -> Dict:
    """
    格式化LLM响应为OpenAI兼容格式
    
    Args:
        llm_response: LLM服务的原始响应
        model_id: 模型ID
    
    Returns:
        Dict: 格式化后的响应
    """
    try:
        # 提取生成的内容
        content = extract_content_from_response(llm_response, model_id)
        
        # 构建OpenAI兼容的响应格式
        formatted_response = {
            "id": llm_response.get("id", f"chatcmpl-{int(time.time())}"),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_id,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": llm_response.get("usage", {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            })
        }
        
        return formatted_response
        
    except Exception as e:
        logger.exception(f"格式化LLM响应出错: {str(e)}")
        raise ValueError(f"格式化LLM响应出错: {str(e)}")
        

def extract_content_from_response(response: Dict, model_id: str) -> str:
    """
    从不同模型的响应中提取生成的内容
    
    Args:
        response: LLM服务的原始响应
        model_id: 模型ID
    
    Returns:
        str: 提取的内容
    """
    try:
        # 处理OpenAI格式的响应
        if "choices" in response and isinstance(response["choices"], list):
            choices = response["choices"]
            if choices and "message" in choices[0]:
                return choices[0]["message"].get("content", "")
        
        # 处理千问格式的响应
        if "output" in response and "text" in response["output"]:
            return response["output"]["text"]
            
        # 处理DeepSeek格式的响应
        if "choices" in response and isinstance(response["choices"], list):
            choices = response["choices"]
            if choices and "text" in choices[0]:
                return choices[0]["text"]
                
        # 其他格式，尝试JSON序列化后查找
        response_str = json.dumps(response)
        if "content" in response_str:
            for key, value in response.items():
                if isinstance(value, dict) and "content" in value:
                    return value["content"]
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and "content" in item:
                            return item["content"]
        
        # 如果无法提取内容，返回原始响应的字符串形式
        logger.warning(f"无法从响应中提取内容，返回原始响应: {response}")
        return str(response)
        
    except Exception as e:
        logger.exception(f"提取响应内容出错: {str(e)}")
        return f"提取响应内容出错: {str(e)}"
