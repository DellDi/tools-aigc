"""
流式工具调用示例

本示例展示如何使用流式工具调用功能，接收实时工具执行结果
"""

import asyncio
import json
import sys
import time
from datetime import datetime

import httpx
import sseclient

# 服务端点配置
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/v1/tools/openai/v1/chat/completions"

# 调用请求示例
REQUEST_DATA = {
    "model": "gpt-3.5-turbo",
    "messages": [
        {
            "role": "system",
            "content": "你是一个有用的助手，可以使用各种工具来帮助用户。"
        },
        {
            "role": "user",
            "content": "请给我查询一下当前的日期和时间"
        }
    ],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_current_datetime",
                "description": "获取当前的日期和时间",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "format": {
                            "type": "string",
                            "description": "日期时间格式，例如: '%Y-%m-%d %H:%M:%S'"
                        }
                    },
                    "required": []
                }
            }
        }
    ],
    "tool_choice": "auto",
    "stream": True  # 启用流式响应
}

# 格式化函数用于更好的输出显示
def print_colored(text, color_code='\033[94m'):
    """打印彩色文本"""
    reset_code = '\033[0m'
    print(f"{color_code}{text}{reset_code}")

async def stream_tool_calls():
    """流式接收工具调用结果的示例"""
    print_colored("开始流式工具调用示例", '\033[92m')
    print_colored("---------------------", '\033[92m')
    
    headers = {
        "Content-Type": "application/json",
        "X-Session-Id": f"stream-example-{int(time.time())}",  # 唯一会话ID
        "X-Output-Format": "markdown"  # 结果格式化为markdown
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                API_ENDPOINT,
                json=REQUEST_DATA,
                headers=headers
            ) as response:
                # 检查响应状态
                if response.status_code != 200:
                    print_colored(f"请求失败: {response.status_code}", '\033[91m')
                    try:
                        error_details = await response.json()
                        print_colored(f"错误详情: {json.dumps(error_details, indent=2, ensure_ascii=False)}", '\033[91m')
                    except Exception:
                        print_colored(f"无法解析错误详情: {await response.text()}", '\033[91m')
                    return
                
                # 处理SSE流
                buffer = ""
                async for chunk in response.aiter_bytes():
                    buffer += chunk.decode("utf-8")
                    
                    # 处理可能有多个SSE消息的情况
                    while "\n\n" in buffer:
                        message, buffer = buffer.split("\n\n", 1)
                        message = message.strip()
                        
                        if not message:
                            continue
                            
                        # 解析SSE格式
                        event_type = None
                        data = None
                        
                        for line in message.split("\n"):
                            if line.startswith("event:"):
                                event_type = line[6:].strip()
                            elif line.startswith("data:"):
                                data = line[5:].strip()
                        
                        if not event_type or not data:
                            continue
                            
                        # 处理不同类型的事件
                        if event_type == "message":
                            try:
                                message_data = json.loads(data)
                                
                                # 打印工具调用和结果
                                if "choices" in message_data and message_data["choices"]:
                                    choice = message_data["choices"][0]
                                    
                                    if "delta" in choice:
                                        delta = choice["delta"]
                                        
                                        # 处理工具调用
                                        if "tool_calls" in delta:
                                            for tool_call in delta["tool_calls"]:
                                                print_colored(f"[工具调用] ID: {tool_call['id']}", '\033[94m')
                                                print_colored(f"[工具名称] {tool_call['function']['name']}", '\033[94m')
                                                print_colored(f"[参数] {tool_call['function']['arguments']}", '\033[94m')
                                        
                                        # 处理工具结果
                                        if delta.get("role") == "tool" and "content" in delta:
                                            print_colored(f"[工具结果] {delta['content']}", '\033[92m')
                            except json.JSONDecodeError:
                                print_colored(f"无法解析消息: {data}", '\033[93m')
                        
                        # 处理完成事件
                        elif event_type == "done":
                            print_colored("流式响应完成", '\033[92m')
                            
                        # 处理错误事件
                        elif event_type == "error":
                            try:
                                error_data = json.loads(data)
                                print_colored(f"错误: {error_data.get('error', '未知错误')}", '\033[91m')
                            except json.JSONDecodeError:
                                print_colored(f"错误: {data}", '\033[91m')
    
    except Exception as e:
        print_colored(f"发生错误: {str(e)}", '\033[91m')

async def main():
    """主函数"""
    await stream_tool_calls()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_colored("\n用户终止程序", '\033[93m')
        sys.exit(0)
