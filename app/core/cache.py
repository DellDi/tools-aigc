"""
缓存模块 - 提供工具调用结果缓存

基于内存的简单缓存实现，支持TTL和容量限制
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple
from functools import lru_cache
import json
import hashlib

logger = logging.getLogger(__name__)


class ToolCallCache:
    """工具调用缓存管理类"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存条目数
            ttl: 缓存有效期（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.lru_keys: list = []
    
    def _generate_key(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """
        根据工具名称和参数生成缓存键
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            
        Returns:
            str: 缓存键
        """
        # 对参数进行排序以确保相同参数生成相同的键
        serialized = json.dumps(parameters, sort_keys=True)
        key_str = f"{tool_name}:{serialized}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, tool_name: str, parameters: Dict[str, Any]) -> Optional[Any]:
        """
        获取缓存结果
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            
        Returns:
            Optional[Any]: 缓存的结果，如果不存在或已过期则返回None
        """
        key = self._generate_key(tool_name, parameters)
        
        if key not in self.cache:
            return None
        
        value, timestamp = self.cache[key]
        current_time = time.time()
        
        # 检查缓存是否过期
        if current_time - timestamp > self.ttl:
            # 删除过期缓存
            del self.cache[key]
            self.lru_keys.remove(key)
            return None
        
        # 更新LRU队列
        self.lru_keys.remove(key)
        self.lru_keys.append(key)
        
        logger.info(f"缓存命中: {tool_name}")
        return value
    
    def set(self, tool_name: str, parameters: Dict[str, Any], result: Any) -> None:
        """
        设置缓存结果
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            result: 结果
        """
        key = self._generate_key(tool_name, parameters)
        
        # 如果缓存已满，删除最久未使用的项
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = self.lru_keys.pop(0)
            del self.cache[oldest_key]
        
        # 添加新缓存
        current_time = time.time()
        self.cache[key] = (result, current_time)
        
        # 如果键已存在，先从LRU队列中移除
        if key in self.lru_keys:
            self.lru_keys.remove(key)
        
        # 添加到LRU队列末尾
        self.lru_keys.append(key)
        
        logger.info(f"缓存已设置: {tool_name}")
    
    def clear(self) -> None:
        """清空所有缓存"""
        self.cache.clear()
        self.lru_keys.clear()
        logger.info("缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "memory_usage_approx": len(json.dumps(self.cache))
        }


# 创建单例对象
tool_cache = ToolCallCache()
