"""
格式化处理模块 - 提供工具调用结果的统一格式化

支持多种格式化规则，确保工具调用结果的一致性和可读性
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
import re
from enum import Enum

logger = logging.getLogger(__name__)


class OutputFormat(str, Enum):
    """输出格式枚举"""
    JSON = "json"        # JSON格式
    MARKDOWN = "markdown"  # Markdown格式
    TEXT = "text"        # 纯文本格式
    HTML = "html"        # HTML格式


class ToolResultFormatter:
    """工具调用结果格式化器"""
    
    @staticmethod
    def format_result(
        result: Dict[str, Any], 
        output_format: OutputFormat = OutputFormat.JSON,
        pretty: bool = True,
        include_metadata: bool = False
    ) -> str:
        """
        格式化工具调用结果
        
        Args:
            result: 工具调用结果
            output_format: 输出格式
            pretty: 是否美化输出
            include_metadata: 是否包含元数据
            
        Returns:
            str: 格式化后的结果
        """
        # 提取需要的数据
        success = result.get("success", False)
        data = result.get("data")
        error = result.get("error")
        
        if not include_metadata:
            # 如果不需要元数据，只返回数据部分
            if success and data is not None:
                result_data = data
            else:
                result_data = {"error": error or "Unknown error"}
        else:
            # 保留完整结构
            result_data = result
            
        # 根据格式类型进行格式化
        if output_format == OutputFormat.JSON:
            return ToolResultFormatter.format_json(result_data, pretty)
        elif output_format == OutputFormat.MARKDOWN:
            return ToolResultFormatter.format_markdown(result_data, success)
        elif output_format == OutputFormat.HTML:
            return ToolResultFormatter.format_html(result_data, success)
        else:  # 默认为文本格式
            return ToolResultFormatter.format_text(result_data, success)
    
    @staticmethod
    def format_json(data: Any, pretty: bool = True) -> str:
        """
        格式化为JSON
        
        Args:
            data: 数据
            pretty: 是否美化
            
        Returns:
            str: JSON字符串
        """
        if pretty:
            return json.dumps(data, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False)
    
    @staticmethod
    def format_markdown(data: Any, success: bool = True) -> str:
        """
        格式化为Markdown
        
        Args:
            data: 数据
            success: 是否成功
            
        Returns:
            str: Markdown字符串
        """
        if not success:
            return f"## ❌ 错误\n\n{data.get('error', '未知错误')}"
        
        # 处理不同类型的数据
        if isinstance(data, dict):
            result = "## 📊 结果\n\n"
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    value = f"\n```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```"
                result += f"**{key}**: {value}\n\n"
            return result
        elif isinstance(data, list):
            items = '\n'.join([f"- {ToolResultFormatter._format_list_item(item)}" for item in data])
            return f"## 📋 结果列表\n\n{items}"
        else:
            return f"## 📝 结果\n\n{data}"
    
    @staticmethod
    def _format_list_item(item: Any) -> str:
        """格式化列表项"""
        if isinstance(item, dict):
            return json.dumps(item, ensure_ascii=False)
        return str(item)
    
    @staticmethod
    def format_text(data: Any, success: bool = True) -> str:
        """
        格式化为纯文本
        
        Args:
            data: 数据
            success: 是否成功
            
        Returns:
            str: 文本字符串
        """
        if not success:
            return f"错误: {data.get('error', '未知错误')}"
        
        if isinstance(data, dict):
            result = "结果:\n"
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                result += f"{key}: {value}\n"
            return result
        elif isinstance(data, list):
            items = '\n'.join([f"- {str(item)}" for item in data])
            return f"结果列表:\n{items}"
        else:
            return f"结果: {data}"
    
    @staticmethod
    def format_html(data: Any, success: bool = True) -> str:
        """
        格式化为HTML
        
        Args:
            data: 数据
            success: 是否成功
            
        Returns:
            str: HTML字符串
        """
        if not success:
            return f'<div class="error-message"><h3>错误</h3><p>{data.get("error", "未知错误")}</p></div>'
        
        if isinstance(data, dict):
            rows = []
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    value = f'<pre>{json.dumps(value, ensure_ascii=False, indent=2)}</pre>'
                rows.append(f'<tr><th>{key}</th><td>{value}</td></tr>')
            table = f'<table class="result-table">{"".join(rows)}</table>'
            return f'<div class="result-container"><h3>结果</h3>{table}</div>'
        elif isinstance(data, list):
            items = ''.join([f"<li>{ToolResultFormatter._html_escape(item)}</li>" for item in data])
            return f'<div class="result-list"><h3>结果列表</h3><ul>{items}</ul></div>'
        else:
            return f'<div class="result-text"><h3>结果</h3><p>{data}</p></div>'
    
    @staticmethod
    def _html_escape(item: Any) -> str:
        """HTML转义"""
        if isinstance(item, (dict, list)):
            return f'<pre>{json.dumps(item, ensure_ascii=False, indent=2)}</pre>'
        text = str(item)
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&#39;")
        return text


# 创建单例对象
tool_formatter = ToolResultFormatter()
