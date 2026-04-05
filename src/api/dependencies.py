"""
API依赖注入
提供服务层实例注入
"""
from typing import Optional
from fastapi import Header, HTTPException, Depends

from src.services import (
    NewsService,
    SearchService,
    TrendService,
    PushService,
    MarketService,
    get_news_service,
    get_search_service,
    get_trend_service,
    get_push_service,
    get_market_service
)
from src.core.models import NewsSource


def get_news_source(x_news_source: Optional[str] = Header("crypto")) -> NewsSource:
    """
    从请求头获取新闻来源

    Args:
        x_news_source: 请求头中的数据源（crypto/hkstocks）

    Returns:
        NewsSource枚举

    Raises:
        HTTPException: 无效的数据源
    """
    source_map = {
        "crypto": NewsSource.CRYPTO,
        "hkstocks": NewsSource.HKSTOCKS
    }

    source_lower = x_news_source.lower() if x_news_source else "crypto"

    if source_lower not in source_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid news source: {x_news_source}. Must be 'crypto' or 'hkstocks'"
        )

    return source_map[source_lower]


def get_news_service_dep(
    source: NewsSource = Depends(get_news_source)
) -> NewsService:
    """
    获取新闻服务依赖

    Args:
        source: 新闻来源

    Returns:
        NewsService实例
    """
    return get_news_service(
        source=source,
        auto_extract_keywords=True,
        auto_generate_summary=False
    )


def get_search_service_dep(
    source: NewsSource = Depends(get_news_source)
) -> SearchService:
    """
    获取搜索服务依赖

    Args:
        source: 新闻来源

    Returns:
        SearchService实例
    """
    return get_search_service(source=source)


def get_trend_service_dep(
    source: NewsSource = Depends(get_news_source)
) -> TrendService:
    """
    获取趋势服务依赖

    Args:
        source: 新闻来源

    Returns:
        TrendService实例
    """
    return get_trend_service(source=source)


def get_push_service_dep(
    source: NewsSource = Depends(get_news_source)
) -> PushService:
    """
    获取推送服务依赖

    Args:
        source: 新闻来源

    Returns:
        PushService实例
    """
    return get_push_service(source=source)


def get_market_service_dep(
    source: NewsSource = Depends(get_news_source)
) -> MarketService:
    """
    获取市场服务依赖

    Args:
        source: 新闻来源

    Returns:
        MarketService实例
    """
    return get_market_service(source=source)


# 可选的认证依赖（预留）
def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    验证API密钥（示例）

    Args:
        x_api_key: API密钥

    Returns:
        API密钥

    Raises:
        HTTPException: 无效的API密钥
    """
    # TODO: 实际项目中应该从配置或数据库验证
    # if not x_api_key or x_api_key != "your-secret-key":
    #     raise HTTPException(status_code=401, detail="Invalid API key")

    return x_api_key or "public"


# 可选的分页参数依赖
def get_pagination_params(
    page: int = 1,
    page_size: int = 20
) -> dict:
    """
    获取分页参数

    Args:
        page: 页码（从1开始）
        page_size: 每页数量

    Returns:
        分页参数字典

    Raises:
        HTTPException: 无效的分页参数
    """
    if page < 1:
        raise HTTPException(status_code=400, detail="Page must be >= 1")

    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="Page size must be between 1 and 100")

    return {
        "page": page,
        "page_size": page_size,
        "offset": (page - 1) * page_size,
        "limit": page_size
    }
