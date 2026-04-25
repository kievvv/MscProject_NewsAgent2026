"""
FastAPI主应用
"""
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from src.api.middleware import setup_middlewares
from src.api.routes import (
    news_router,
    search_router,
    trend_router,
    push_router,
    market_router,
    analyzer_router
)
from src.api.routes.frontend import router as frontend_router
from src.api.routes.agent import router as agent_router
from src.api.routes.websocket import router as websocket_router
from src.crawlers.telegram.config import RedisConfig
from src.crawlers.telegram.monitor import build_pipeline_status
from src.services.crypto_bootstrap_service import get_crypto_startup_bootstrap_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="NewsAgent API",
    description="新闻聚合和分析API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置中间件
setup_middlewares(app, enable_rate_limit=False)

# 挂载静态文件
static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 注册API路由
app.include_router(news_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(trend_router, prefix="/api/v1")
app.include_router(push_router, prefix="/api/v1")
app.include_router(market_router, prefix="/api/v1")
app.include_router(agent_router, prefix="/api/v1")  # AI Agent路由
app.include_router(websocket_router)  # WebSocket路由

# 注册分析器路由（特殊路径，直接/api开头）
app.include_router(analyzer_router)

# 注册前端路由（无前缀，直接挂载到根路径）
app.include_router(frontend_router)


@app.on_event("startup")
async def startup_background_jobs():
    """Schedule non-blocking startup jobs."""
    get_crypto_startup_bootstrap_service().schedule_startup_check()


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "2.0.0"
    }


@app.get("/api/status")
async def api_status():
    """API状态"""
    return {
        "name": "NewsAgent API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/api/crypto-pipeline/health")
async def crypto_pipeline_health():
    """Crypto/Telegram 实时链路健康检查。"""
    redis_config = RedisConfig(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        queue_name="crypto_news_queue",
    )
    status = build_pipeline_status(redis_config)
    status.update(get_crypto_startup_bootstrap_service().get_status())
    return status


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "detail": str(exc) if settings.DEBUG else None
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
