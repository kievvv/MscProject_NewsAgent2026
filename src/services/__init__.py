"""
服务层模块
提供业务逻辑封装
"""
from .news_service import NewsService, get_news_service
from .search_service import SearchService, get_search_service
from .trend_service import TrendService, get_trend_service
from .push_service import PushService, get_push_service
from .market_service import MarketService, get_market_service

__all__ = [
    'NewsService',
    'get_news_service',
    'SearchService',
    'get_search_service',
    'TrendService',
    'get_trend_service',
    'PushService',
    'get_push_service',
    'MarketService',
    'get_market_service',
]
