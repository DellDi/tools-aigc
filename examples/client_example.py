"""
客户端示例 - 演示如何使用tools-aigc服务
"""

import asyncio
import json
import sys

import httpx


async def list_tools(base_url: str) -> None:
    """获取所有可用工具的列表"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/api/tools/")
        response.raise_for_status()

        tools = response.json()["tools"]
        print(f"可用工具列表 ({len(tools)}):")
        for tool in tools:
            print(f"- {tool['name']}: {tool['description']}")


async def call_echo_tool(base_url: str) -> None:
    """调用Echo工具"""
    data = {
        "name": "echo",
        "parameters": {
            "message": "Hello, Tools-AIGC!",
            "prefix": "Echo:",
            "suffix": "- From Client Example"
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{base_url}/api/tools/echo", json=data)
        response.raise_for_status()

        result = response.json()
        print("\nEcho工具调用结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))


async def call_weather_tool(base_url: str, city: str) -> None:
    """调用天气查询工具"""
    data = {
        "name": "weather",
        "parameters": {
            "city": city,
            "country": "CN",
            "units": "metric"
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{base_url}/api/tools/weather", json=data)
        response.raise_for_status()

        result = response.json()
        print(f"\n{city}天气查询结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))


async def call_http_request_tool(base_url: str, url: str) -> None:
    """调用HTTP请求工具"""
    data = {
        "name": "http_request",
        "parameters": {
            "url": url,
            "method": "GET",
            "headers": {
                "User-Agent": "Tools-AIGC Client Example"
            }
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{base_url}/api/tools/http_request", json=data)
        response.raise_for_status()

        result = response.json()
        print(f"\nHTTP请求工具调用结果 ({url}):")
        print(f"状态码: {result['data']['status_code']}")

        # 如果响应数据太大，只打印部分
        data_str = json.dumps(result['data']['data'], ensure_ascii=False)
        if len(data_str) > 1000:
            print(f"响应数据: {data_str[:1000]}... (已截断)")
        else:
            print(f"响应数据: {data_str}")


async def call_openai_compatible_api(base_url: str) -> None:
    """调用OpenAI兼容的API"""
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": "What's the weather in Beijing?"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "weather",
                            "arguments": json.dumps({"city": "Beijing"})
                        }
                    }
                ]
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "weather",
                    "description": "查询指定城市的天气信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "城市名称"
                            }
                        },
                        "required": ["city"]
                    }
                }
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{base_url}/api/tools/openai/v1/chat/completions", json=data)
        response.raise_for_status()

        result = response.json()
        print("\nOpenAI兼容API调用结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))


async def main() -> None:
    """主函数"""
    # 默认服务地址
    base_url = "http://localhost:8000"

    # 如果提供了命令行参数，使用提供的服务地址
    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    print(f"使用服务地址: {base_url}")

    try:
        # 获取工具列表
        await list_tools(base_url)

        # 调用Echo工具
        await call_echo_tool(base_url)

        # 调用天气查询工具
        await call_weather_tool(base_url, "北京")

        # 调用HTTP请求工具
        await call_http_request_tool(base_url, "https://httpbin.org/json")

        # 调用OpenAI兼容的API
        await call_openai_compatible_api(base_url)

    except httpx.HTTPStatusError as e:
        print(f"HTTP错误: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        print(f"请求错误: {str(e)}")
    except Exception as e:
        print(f"未知错误: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())