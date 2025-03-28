"""
会话管理模块 - 提供会话状态和工具权限管理
"""

import time
import uuid
import logging
from typing import Dict, Any, List, Optional, Set
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class Session:
    """会话对象，包含会话状态和工具权限"""
    
    def __init__(self, session_id: str = None, user_id: Optional[str] = None):
        """
        初始化会话
        
        Args:
            session_id: 会话ID，如果不提供则自动生成
            user_id: 用户ID，可选
        """
        self.session_id = session_id or f"session-{uuid.uuid4().hex}"
        self.user_id = user_id
        self.created_at = time.time()
        self.last_active = time.time()
        self.allowed_tools: Set[str] = set()  # 允许使用的工具集合
        self.metadata: Dict[str, Any] = {}    # 会话元数据
        self.messages: List[Dict[str, Any]] = []  # 会话消息历史
        
    def update_active_time(self) -> None:
        """更新最后活跃时间"""
        self.last_active = time.time()
    
    def allow_tool(self, tool_name: str) -> None:
        """
        允许使用指定工具
        
        Args:
            tool_name: 工具名称
        """
        self.allowed_tools.add(tool_name)
        
    def allow_tools(self, tool_names: List[str]) -> None:
        """
        批量允许使用工具
        
        Args:
            tool_names: 工具名称列表
        """
        self.allowed_tools.update(tool_names)
        
    def disallow_tool(self, tool_name: str) -> None:
        """
        禁止使用指定工具
        
        Args:
            tool_name: 工具名称
        """
        if tool_name in self.allowed_tools:
            self.allowed_tools.remove(tool_name)
    
    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        检查工具是否允许使用
        
        Args:
            tool_name: 工具名称
            
        Returns:
            bool: 是否允许使用
        """
        # 如果没有设置任何允许工具，则默认允许所有工具
        if not self.allowed_tools:
            return True
        return tool_name in self.allowed_tools
    
    def add_message(self, message: Dict[str, Any]) -> None:
        """
        添加消息到会话历史
        
        Args:
            message: 消息内容
        """
        self.messages.append(message)
        self.update_active_time()
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """
        获取会话历史消息
        
        Returns:
            List[Dict[str, Any]]: 会话消息列表
        """
        return self.messages
    
    def clear_messages(self) -> None:
        """清空会话历史消息"""
        self.messages = []
        self.update_active_time()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典表示
        
        Returns:
            Dict[str, Any]: 会话字典表示
        """
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "allowed_tools": list(self.allowed_tools),
            "metadata": self.metadata,
            "messages_count": len(self.messages)
        }


class SessionManager:
    """会话管理器，管理全部会话"""
    
    def __init__(self, session_ttl: int = 3600):
        """
        初始化会话管理器
        
        Args:
            session_ttl: 会话过期时间（秒）
        """
        self.sessions: Dict[str, Session] = {}
        self.session_ttl = session_ttl
        
    def create_session(self, user_id: Optional[str] = None) -> Session:
        """
        创建新会话
        
        Args:
            user_id: 用户ID，可选
            
        Returns:
            Session: 新创建的会话
        """
        session = Session(user_id=user_id)
        self.sessions[session.session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Session]: 会话对象，如果不存在则返回None
        """
        session = self.sessions.get(session_id)
        if session:
            session.update_active_time()
        return session
    
    def get_or_create_session(self, session_id: Optional[str] = None, user_id: Optional[str] = None) -> Session:
        """
        获取或创建会话
        
        Args:
            session_id: 会话ID，可选
            user_id: 用户ID，可选
            
        Returns:
            Session: 会话对象
        """
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
            session.update_active_time()
            return session
            
        # 创建新会话
        session = Session(session_id=session_id, user_id=user_id)
        self.sessions[session.session_id] = session
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 是否成功删除
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def clean_expired_sessions(self) -> int:
        """
        清理过期会话
        
        Returns:
            int: 已清理的会话数量
        """
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if current_time - session.last_active > self.session_ttl
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            
        return len(expired_sessions)
    
    def get_all_sessions(self) -> Dict[str, Session]:
        """
        获取所有会话
        
        Returns:
            Dict[str, Session]: 会话ID到会话对象的映射
        """
        return self.sessions
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取会话统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_sessions": len(self.sessions),
            "session_ttl": self.session_ttl
        }


# 创建单例实例
session_manager = SessionManager()
    

@asynccontextmanager
async def get_session(session_id: Optional[str] = None, user_id: Optional[str] = None):
    """
    获取或创建会话的上下文管理器
    
    Args:
        session_id: 会话ID，可选
        user_id: 用户ID，可选
        
    Yields:
        Session: 会话对象
    """
    session = session_manager.get_or_create_session(session_id, user_id)
    try:
        yield session
    finally:
        # 更新最后活跃时间
        session.update_active_time()
