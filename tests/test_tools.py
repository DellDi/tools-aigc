"""
工具测试模块
"""

import json
import pytest
from fastapi.testclient import TestClient

from app.tools import load_tools
from main import app

# 载入环境变量
from dotenv import load_dotenv

load_dotenv()

# 初始化测试客户端
@pytest.fixture
def client():
    """创建测试客户端"""
    # 加载工具
    load_tools()

    # 创建测试客户端
    return TestClient(app)


def test_list_tools(client):
    """测试获取工具列表"""
    response = client.get("/api/tools/")
    assert response.status_code == 200

    data = response.json()
    assert "tools" in data
    assert len(data["tools"]) > 0

    # 检查是否包含echo工具
    echo_tool = next((tool for tool in data["tools"] if tool["name"] == "echo"), None)
    assert echo_tool is not None
    assert echo_tool["name"] == "echo"
    assert "description" in echo_tool
    assert "parameters_schema" in echo_tool


def test_call_echo_tool(client):
    """测试调用echo工具"""
    # 准备请求数据
    request_data = {
        "name": "echo",
        "parameters": {
            "message": "Hello, World!",
            "prefix": "Echo:",
            "suffix": "End"
        }
    }

    # 发送请求
    response = client.post("/api/tools/echo", json=request_data)
    assert response.status_code == 200

    # 验证响应
    data = response.json()
    assert data["name"] == "echo"
    assert data["success"] is True
    assert data["data"]["original_message"] == "Hello, World!"
    assert data["data"]["processed_message"] == "Echo: Hello, World! End"
    assert data["data"]["prefix"] == "Echo:"
    assert data["data"]["suffix"] == "End"


def test_call_nonexistent_tool(client):
    """测试调用不存在的工具"""
    response = client.post("/api/tools/nonexistent", json={"name": "nonexistent", "parameters": {}})
    assert response.status_code == 404


def test_openai_tools_api(client):
    """测试OpenAI兼容的工具调用API"""
    # 准备请求数据
    request_data = {
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

    # 发送请求
    response = client.post("/api/tools/openai/v1/chat/completions", json=request_data)
    assert response.status_code == 200

    # 验证响应
    data = response.json()
    assert "id" in data
    assert "choices" in data
    assert len(data["choices"]) > 0
