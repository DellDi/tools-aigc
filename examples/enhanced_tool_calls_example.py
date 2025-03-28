#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
工具调用增强功能示例代码
包含会话管理、格式化输出、工具权限和缓存功能的使用示例
"""

import asyncio
import httpx
import json
from typing import Dict, Any, List, Optional


# 会话级工具调用示例
async def multi_turn_conversation():
    """
    演示使用会话ID保持多轮对话上下文的示例
    """
    session_id = "user-123"  # 自定义会话ID
    
    # 第一轮对话
    async with httpx.AsyncClient() as client:
        response1 = await client.post(
            "http://localhost:8000/openai/v1/chat/completions",
            headers={"X-Session-Id": session_id},
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": "北京今天天气怎么样？"}
                ]
            }
        )
        print(f"第一轮对话响应: {response1.json()}")
    
    # 第二轮对话（会保持上下文）
    async with httpx.AsyncClient() as client:
        response2 = await client.post(
            "http://localhost:8000/openai/v1/chat/completions",
            headers={"X-Session-Id": session_id},
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "user", "content": "明天呢？"}
                ]
            }
        )
        print(f"第二轮对话响应: {response2.json()}")


# 自定义输出格式示例
async def format_output_example():
    """
    演示不同输出格式的工具调用结果
    支持 json, markdown, text, html 格式
    """
    for output_format in ["json", "markdown", "text", "html"]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/openai/v1/chat/completions",
                headers={"X-Output-Format": output_format},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "user", "content": "帮我查询上海天气"}
                    ],
                    "tools": [{
                        "type": "function", 
                        "function": {
                            "name": "weather",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "city": {"type": "string"}
                                },
                                "required": ["city"]
                            }
                        }
                    }]
                }
            )
            print(f"\n{output_format.upper()} 格式输出示例:")
            try:
                resp_data = response.json()
                print(json.dumps(resp_data, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"解析响应出错: {str(e)}")


# 服务端工具权限管理示例 (需要在服务端运行)
def session_tool_permissions_example():
    """
    演示如何在服务端管理工具权限
    注意: 此函数需要在服务端环境中运行
    """
    from app.core.session import session_manager
    
    # 获取或创建会话
    session = session_manager.get_or_create_session("user-123")
    
    # 设置允许使用的工具
    session.allow_tools(["weather", "calculator"])
    print(f"已允许工具: {session.get_allowed_tools()}")
    
    # 禁用特定工具
    session.disallow_tool("http_request")
    
    # 检查工具权限
    allowed = session.is_tool_allowed("weather")
    blocked = session.is_tool_allowed("http_request")
    print(f"weather工具允许状态: {allowed}")
    print(f"http_request工具允许状态: {blocked}")
    
    # 重置为允许所有工具
    session.reset_tool_permissions()
    print(f"重置后允许的工具: {session.get_allowed_tools()}")


# 自定义缓存行为示例 (需要在服务端运行)
def cache_management_example():
    """
    演示如何管理工具调用缓存
    注意: 此函数需要在服务端环境中运行
    """
    from app.core.cache import tool_cache
    
    # 检查缓存状态
    stats = tool_cache.get_stats()
    print(f"缓存状态: {stats}")
    
    # 设置缓存TTL和容量
    tool_cache.set_ttl(300)  # 5分钟过期时间
    tool_cache.set_max_size(1000)  # 最多1000条缓存项
    print(f"已设置缓存TTL为300秒, 最大容量为1000条")
    
    # 手动清除缓存
    tool_cache.clear()
    print("已清除所有缓存")


# 完整功能演示
async def main():
    print("===== 多轮对话示例 =====")
    await multi_turn_conversation()
    
    print("\n===== 自定义输出格式示例 =====")
    await format_output_example()
    
    print("\n注意: 以下示例需要在服务端环境中运行")
    print("\n===== 工具权限管理示例 (服务端) =====")
    print("session_tool_permissions_example()")
    
    print("\n===== 缓存管理示例 (服务端) =====")
    print("cache_management_example()")


if __name__ == "__main__":
    asyncio.run(main())
