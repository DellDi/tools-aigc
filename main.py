"""
FastAPI应用主入口
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.responses import RedirectResponse

from app.api import api_router
from app.core.config import settings
from app.db.session import init_db
from app.middleware.api_log import ApiLogMiddleware
from app.tools import load_tools

# 配置日志
logging.basicConfig(
    level=logging.INFO if settings.APP_DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时加载所有工具
    logger.info("应用启动中...")
    load_tools()

    # 初始化数据库
    await init_db()

    yield

    # 应用关闭时的清理操作
    logger.info("应用关闭中...")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="通用OpenAI兼容模型的function call工具集合调用服务",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,  # 禁用默认的Swagger UI，使用自定义的
    redoc_url=None,  # 禁用默认的ReDoc
)

# 配置CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 添加API日志中间件（已优化，使用后台任务和超时机制）
app.add_middleware(ApiLogMiddleware)

# 暂时禁用认证中间件
# app.add_middleware(
#     AuthMiddleware,
#     exclude_paths=[
#         "/",
#         "/api/health",
#         "/api/auth/login",
#         "/api/auth/register",
#         "/api/docs",
#         "/api/redoc",
#         "/api/openapi.json",
#     ],
#     exclude_prefixes=[
#         "/docs",
#         "/redoc",
#         "/openapi.json",
#         "/static",
#     ],
# )

# 注册路由
app.include_router(api_router, prefix="/api")


# 自定义OpenAPI模式，添加认证
def custom_openapi():
    """自定义OpenAPI模式"""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # # 添加认证组件
    # openapi_schema["components"] = openapi_schema.get("components", {})
    # openapi_schema["components"]["securitySchemes"] = {
    #     "bearerAuth": {
    #         "type": "http",
    #         "scheme": "bearer",
    #         "bearerFormat": "JWT",
    #     }
    # }

    # # 添加全局安全要求
    # openapi_schema["security"] = [{"bearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# 提供 OpenAPI JSON
@app.get("/api/openapi.json", include_in_schema=False)
async def get_openapi_json():
    """提供 OpenAPI JSON文件供 Swagger UI 使用"""
    return JSONResponse(
        content=app.openapi(),
        headers={
            "content-type": "application/json",
            "Content-Disposition": "attachment; filename=\"openapi.json\"",
        },
    )


# 自定义Swagger UI
@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """自定义Swagger UI"""
    return get_swagger_ui_html(
        openapi_url="/api/openapi.json",  # 使用根路径的 OpenAPI JSON
        title=f"{settings.APP_NAME} - Swagger UI",
        oauth2_redirect_url="/api/docs/oauth2-redirect",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_favicon_url="/static/favicon.ico",
        init_oauth={
            "clientId": "",
            "clientSecret": "",
            "realm": "",
            "appName": settings.APP_NAME,
            "scopeSeparator": " ",
            "scopes": "",
            "usePkceWithAuthorizationCodeGrant": True,
        },
    )


# 健康检查端点
@app.get("/api/health", tags=["health"])
async def health_check():
    """
    健康检查端点
    """
    return JSONResponse(
        status_code=200, content={"status": "ok", "message": "服务正常运行"}
    )


# 根路径重定向到文档
@app.get("/", include_in_schema=False)
async def root():
    """
    根路径重定向到文档
    """
    return RedirectResponse(url="/api/docs")


if __name__ == "__main__":
    """
    开发环境启动应用
    """
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
    )
