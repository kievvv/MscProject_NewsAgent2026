"""
API中间件
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        处理请求并记录日志

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            响应对象
        """
        # 记录请求开始
        start_time = time.time()
        logger.info(f"Request: {request.method} {request.url.path}")

        # 处理请求
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise

        # 记录请求结束
        process_time = time.time() - start_time
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"status={response.status_code} time={process_time:.3f}s"
        )

        # 添加处理时间到响应头
        response.headers["X-Process-Time"] = f"{process_time:.3f}"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    简单的速率限制中间件（示例）
    实际项目中应使用Redis等分布式缓存
    """

    def __init__(self, app, max_requests: int = 100, time_window: int = 60):
        """
        初始化速率限制中间件

        Args:
            app: FastAPI应用
            max_requests: 时间窗口内的最大请求数
            time_window: 时间窗口（秒）
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.time_window = time_window
        self.request_counts = {}  # {ip: [(timestamp, count)]}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        检查速率限制

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理器

        Returns:
            响应对象
        """
        # 获取客户端IP
        client_ip = request.client.host if request.client else "unknown"

        # 清理过期记录
        current_time = time.time()
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                (ts, count) for ts, count in self.request_counts[client_ip]
                if current_time - ts < self.time_window
            ]

        # 检查请求数
        if client_ip in self.request_counts:
            total_requests = sum(count for _, count in self.request_counts[client_ip])
            if total_requests >= self.max_requests:
                logger.warning(f"Rate limit exceeded for {client_ip}")
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=429,
                    content={
                        "success": False,
                        "message": "Rate limit exceeded. Please try again later."
                    }
                )

        # 记录请求
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        self.request_counts[client_ip].append((current_time, 1))

        # 处理请求
        response = await call_next(request)

        # 添加速率限制信息到响应头
        total_requests = sum(count for _, count in self.request_counts[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(self.max_requests - total_requests)

        return response


def setup_cors(app):
    """
    配置CORS

    Args:
        app: FastAPI应用
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 实际项目中应该配置具体的域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def setup_middlewares(app, enable_rate_limit: bool = False):
    """
    配置所有中间件

    Args:
        app: FastAPI应用
        enable_rate_limit: 是否启用速率限制
    """
    # CORS
    setup_cors(app)

    # 日志中间件
    app.add_middleware(LoggingMiddleware)

    # 速率限制（可选）
    if enable_rate_limit:
        app.add_middleware(RateLimitMiddleware, max_requests=100, time_window=60)
