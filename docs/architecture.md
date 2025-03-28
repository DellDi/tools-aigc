# Tools-AIGC 架构设计文档

本文档描述了Tools-AIGC项目的架构设计，包括核心组件、数据流程和交互模式。

## 工具调用增强功能架构

下图展示了工具调用增强功能的整体架构，包括缓存、会话管理、格式化和多轮对话支持：

```mermaid
graph TD
    A[客户端请求] --> B[会话管理]
    B --> C{处理模式}
    C -->|标准模式| D[工具调用识别]
    C -->|自动模式| E[自动工具执行]
    
    D --> F[返回工具调用描述]
    E --> G[工具执行与缓存]
    G --> H[结果格式化]
    H --> I[多轮对话更新]
    I --> J[返回最终结果]
    
    subgraph "核心增强功能"
    K[工具调用缓存]
    L[会话级权限]
    M[结果格式化]
    N[多轮对话处理]
    end
    
    G <--> K
    G <--> L
    H <--> M
    I <--> N
```

## 数据流程架构

下图展示了一个完整工具调用的数据流程，从客户端请求到最终响应的全过程：

```mermaid
sequenceDiagram
    participant 客户端
    participant API端点
    participant 会话管理
    participant 工具执行器
    participant 缓存系统
    participant 底层工具
    participant 格式化器
    
    客户端->>API端点: POST /openai/v1/chat/completions
    API端点->>+会话管理: 获取/创建会话
    会话管理-->>-API端点: 返回会话
    
    API端点->>API端点: 处理消息和工具调用
    API端点->>+工具执行器: 执行工具调用
    工具执行器->>+会话管理: 检查工具权限
    会话管理-->>-工具执行器: 权限返回
    
    工具执行器->>+缓存系统: 查询缓存
    缓存系统-->>-工具执行器: 缓存结果(如有)
    
    alt 缓存未命中
        工具执行器->>+底层工具: 执行工具
        底层工具-->>-工具执行器: 工具结果
        工具执行器->>+缓存系统: 存入缓存
        缓存系统-->>-工具执行器: 缓存确认
    end
    
    工具执行器->>+格式化器: 格式化结果
    格式化器-->>-工具执行器: 格式化输出
    工具执行器->>+会话管理: 记录工具调用历史
    会话管理-->>-工具执行器: 确认
    工具执行器-->>-API端点: 返回工具结果
    
    API端点->>API端点: 组装最终响应
    API端点-->>+客户端: 返回响应
```

## 核心组件结构

### 缓存系统 (ToolCallCache)

```mermaid
classDiagram
    class ToolCallCache {
        -dict _cache
        -int _ttl
        -int _max_size
        -dict _stats
        +get(tool_name, parameters)
        +set(tool_name, parameters, result)
        +clear()
        +set_ttl(seconds)
        +set_max_size(size)
        +get_stats()
        -_generate_cache_key(tool_name, parameters)
    }
```

### 会话管理 (SessionManager)

```mermaid
classDiagram
    class SessionManager {
        -dict _sessions
        +create_session()
        +get_session(session_id)
        +get_or_create_session(session_id)
        +delete_session(session_id)
        +cleanup_expired_sessions()
    }
    
    class Session {
        +str session_id
        -list _messages
        -set _allowed_tools
        -datetime _created_at
        -datetime _last_activity
        +add_message(message)
        +get_messages()
        +allow_tool(tool_name)
        +allow_tools(tool_names)
        +disallow_tool(tool_name)
        +is_tool_allowed(tool_name)
        +reset_tool_permissions()
        +get_allowed_tools()
    }
    
    SessionManager --> Session : manages
```

### 格式化器 (ToolResultFormatter)

```mermaid
classDiagram
    class OutputFormat {
        <<enumeration>>
        JSON
        MARKDOWN
        TEXT
        HTML
    }
    
    class ToolResultFormatter {
        +format_result(result, output_format, include_metadata)
        -_format_json(result)
        -_format_markdown(result)
        -_format_text(result)
        -_format_html(result)
    }
    
    ToolResultFormatter --> OutputFormat : uses
```

## 工具调用执行流程

下图展示了工具调用的详细执行流程：

```mermaid
flowchart TD
    Start([开始]) --> A{检查缓存}
    A -->|命中| B[获取缓存结果]
    A -->|未命中| C[权限检查]
    C -->|通过| D[执行工具]
    C -->|未通过| E[权限错误]
    D --> F[缓存结果]
    B --> G[格式化输出]
    F --> G
    E --> G
    G --> H[记录会话历史]
    H --> End([结束])
```

## 数据模型

### 工具结果模型

```mermaid
classDiagram
    class ToolResult {
        +bool success
        +Any data
        +str error
    }
```

### 格式化结果模型

```mermaid
classDiagram
    class FormattedResult {
        +Dict result
        +str formatted
        +Dict metadata
    }
    
    class ResultMetadata {
        +str tool_name
        +bool cached
        +str format
        +float timestamp
    }
    
    FormattedResult --> ResultMetadata : contains
```
