"""
API路由模块
"""
from .news import router as news_router
from .search import router as search_router
from .trend import router as trend_router
from .push import router as push_router
from .market import router as market_router
from .analyzer import router as analyzer_router

__all__ = [
    'news_router',
    'search_router',
    'trend_router',
    'push_router',
    'market_router',
    'analyzer_router',
]
