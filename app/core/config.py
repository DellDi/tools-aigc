"""
配置管理模块
"""

from typing import List, Optional, Union

from pydantic import AnyHttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """应用配置设置"""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )
    # 应用配置
    APP_NAME: str = model_config.get("APP_NAME")
    APP_ENV: str = model_config.get("APP_ENV")
    APP_DEBUG: bool = model_config.get("APP_DEBUG")
    APP_PORT: int = model_config.get("APP_PORT")
    APP_HOST: str = model_config.get("APP_HOST")

    # CORS配置
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = ['http://localhost:8000', 'http://127.0.0.1:8000', 'http://localhost:3000', 'http://127.0.0.1:3000']

    # 工具配置
    TOOLS_TIMEOUT: int = model_config.get("TOOLS_TIMEOUT")

    # 通义API配置
    QWEN_API_KEY: Optional[str] = model_config.get("QWEN_API_KEY")

    # OpenWeatherMap API配置
    OPENWEATHERMAP_API_KEY: Optional[str] = model_config.get("OPENWEATHERMAP_API_KEY")

    # 数据库配置
    DATABASE_URL: str = model_config.get("DATABASE_URL")
    
    @field_validator("DATABASE_URL", mode="before")
    def validate_database_url(cls, v: str) -> str:
        """验证数据库URL格式"""
        # 使用 PostgresDsn 进行验证，但返回字符串
        PostgresDsn(v)
        return v
    DATABASE_POOL_SIZE: int = model_config.get("DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = model_config.get("DATABASE_MAX_OVERFLOW")
    DATABASE_ECHO: bool = model_config.get("DATABASE_ECHO")

    # JWT认证配置
    JWT_SECRET_KEY: str = model_config.get("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = model_config.get("JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = model_config.get(
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # API路由白名单（不需要认证的路由）
    API_WHITELIST: List[str] = [
        "/api/health",
        "/api/docs",
        "/api/openapi.json",
        "/api/auth/login",
    ]
    
    # 日志配置
    LOG_FILE_ENABLED: bool = model_config.get("LOG_FILE_ENABLED", True)
    LOG_DB_ENABLED: bool = model_config.get("LOG_DB_ENABLED", True)
    BATCH_SIZE: int = model_config.get("BATCH_SIZE", 50)
    CAPTURE_RESPONSE_BODY: bool = model_config.get("CAPTURE_RESPONSE_BODY", True)
    MAX_RESPONSE_SIZE: int = model_config.get("MAX_RESPONSE_SIZE", 1024 * 1024)
    LOG_ROTATION_BY_DAY: bool = model_config.get("LOG_ROTATION_BY_DAY", True)
    LOG_MAX_SIZE: int = model_config.get("LOG_MAX_SIZE", 5 * 1024 * 1024)
    DB_LOG_ERRORS_ONLY: bool = model_config.get("DB_LOG_ERRORS_ONLY", True)

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """验证CORS配置"""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)




settings = Settings()
