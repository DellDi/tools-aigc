from openai import OpenAI
import json
import os
import sys

# 使用环境变量或默认值设置基础 URL
base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")

client = OpenAI(
    api_key="sk-qwen",  # 测试用的默认 API 密钥
    base_url=f"{base_url}/api/tools/openai/v1",  # 只需要指定到 v1 为止，客户端会自动添加 /chat/completions
)

# 获取测试模式，默认为工具调用模式
# 可选值: tool_call, conversation, hybrid
test_mode = os.environ.get("TEST_MODE", "tool_call")
if len(sys.argv) > 1:
    test_mode = sys.argv[1]
    
print(f"\n测试模式: {test_mode}")

# 根据测试模式构建不同的消息列表
if test_mode == "tool_call":
    # 定义天气工具调用
    weather_tool_call = {
        "id": "call_123",
        "type": "function",
        "function": {
            "name": "weather",
            "arguments": json.dumps({
                "city": "北京",
                "country": "CN",
                "units": "metric",
                "exclude": "minutely"  # 测试 exclude 参数
            })
        }
    }
    
    # 构建工具调用消息列表
    messages = [
        {"role": "user", "content": "请查询北京的天气，包括当前天气和未来几天的预报"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [weather_tool_call]
        }
    ]
    print("\n测试纯工具调用模式 - 发送包含明确工具调用的请求")
    
elif test_mode == "conversation":
    # 构建纯对话消息列表
    messages = [
        {"role": "user", "content": "你好，请简单介绍一下自己"}
    ]
    print("\n测试纯对话模式 - 发送普通对话请求")
    
elif test_mode == "hybrid":
    # 构建混合模式消息列表 - 包含隐含的工具调用意图但不显式指定工具调用
    messages = [
        {"role": "user", "content": "北京今天天气怎么样？会下雨吗？"}
    ]
    print("\n测试混合模式 - 发送包含隐含工具调用意图的请求")
    
else:
    print(f"错误: 未知的测试模式 {test_mode}，支持的模式: tool_call, conversation, hybrid")
    sys.exit(1)

# 构建请求参数
request_params = {
    "model": os.environ.get("TEST_MODEL", "qwen-max"),
    "messages": messages,
}

# 如果是工具调用或混合模式，添加工具定义
if test_mode in ["tool_call", "hybrid"]:
    request_params["tools"] = [
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
                        },
                        "country": {
                            "type": "string",
                            "description": "国家代码，如CN表示中国"
                        },
                        "units": {
                            "type": "string",
                            "description": "温度单位，默认为metric（摄氏度）"
                        }
                    },
                    "required": ["city"]
                }
            }
        }
    ]

# 发送请求
try:
    print("\n发送请求...")
    response = client.chat.completions.create(**request_params)
    print("\n响应结果:")
    print(response)
    
    # 打印响应消息内容
    if hasattr(response.choices[0].message, 'content') and response.choices[0].message.content:
        print("\n返回的消息内容:")
        print(response.choices[0].message.content)
    
    # 如果有工具调用
    if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
        print("\n工具调用:")
        for tool_call in response.choices[0].message.tool_calls:
            print(f"工具ID: {tool_call.id}")
            print(f"工具名称: {tool_call.function.name}")
            print(f"参数: {tool_call.function.arguments}")
    
    # 如果有工具调用结果
    if hasattr(response.choices[0].message, 'tool_call_results'):
        print("\n工具调用结果:")
        # 处理列表形式的结果
        results = response.choices[0].message.tool_call_results
        if isinstance(results, list):
            for result in results:
                print(f"\nTool ID: {result['tool_call_id']}")
                print(f"Output: {result['output']}")
                
                # 解析 JSON 输出
                output_data = json.loads(result['output'])
                if output_data.get("success"):
                    data = output_data.get('data')
                    print(f"\n数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    
                    # 验证 One Call API 3.0 的新字段
                    if "current" in data:
                        print("\n当前天气数据有效")
                    if "hourly" in data:
                        print(f"\n小时预报数据有效，包含 {len(data['hourly'])} 条记录")
                    if "daily" in data:
                        print(f"\n每日预报数据有效，包含 {len(data['daily'])} 条记录")
                    if "alerts" in data:
                        print(f"\n天气预警数据有效，包含 {len(data['alerts'])} 条记录")
                else:
                    print(f"\n错误: {output_data.get('error')}")
    
    # 将响应添加到消息列表
    messages.append(response.choices[0].message)
    print(f"\n消息列表更新完成")
    
except Exception as e:
    print(f"\n错误: {str(e)}")
