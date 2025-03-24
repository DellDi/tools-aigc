"""
配置管理模块
"""

from typing import List, Optional, Union

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置设置"""

    # 应用配置
    APP_NAME: str = "tools-aigc"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_PORT: int = 8000
    APP_HOST: str = "0.0.0.0"

    # CORS配置
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """验证CORS配置"""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # 工具配置
    TOOLS_TIMEOUT: int = 30  # 工具调用超时时间（秒）
    
    # 通义API配置
    QWEN_API_KEY: Optional[str] = None
    
    # OpenWeatherMap API配置
    OPENWEATHERMAP_API_KEY: Optional[str] = None

    # 数据库配置
    DATABASE_URL: str = Field(..., description="数据库连接URL")
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # JWT认证配置
    JWT_SECRET_KEY: str = Field(..., description="JWT密钥")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # API路由白名单（不需要认证的路由）
    API_WHITELIST: List[str] = [
        "/api/health",
        "/api/docs",
        "/api/openapi.json",
        "/api/auth/login",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


settings = Settings()