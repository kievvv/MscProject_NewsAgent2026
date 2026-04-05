"""
搜索API路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from src.services import SearchService
from src.api.dependencies import get_search_service_dep
from src.api.schemas import (
    Response,
    NewsResponse,
    SearchRequest,
    SimilaritySearchRequest,
    SearchRankRequest,
    KeywordStatsResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/keyword", response_model=Response)
async def search_by_keyword(
    keyword: str = Query(..., description="关键词"),
    exact: bool = Query(False, description="是否精确匹配"),
    limit: int = Query(100, description="限制返回数量"),
    service: SearchService = Depends(get_search_service_dep)
):
    """
    按关键词搜索
    """
    try:
        news_list = service.search_by_keyword(keyword, exact=exact, limit=limit)
        news_responses = [NewsResponse.model_validate(n) for n in news_list]

        return Response(
            success=True,
            data={
                "keyword": keyword,
                "count": len(news_responses),
                "news": news_responses
            }
        )
    except Exception as e:
        logger.error(f"关键词搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/similarity", response_model=Response)
async def search_by_similarity(
    request: SimilaritySearchRequest,
    service: SearchService = Depends(get_search_service_dep)
):
    """
    相似度搜索（查找相似关键词的新闻）
    """
    try:
        results = service.search_by_similarity(
            keyword=request.keyword,
            top_n=request.top_n,
            min_similarity=request.min_similarity
        )

        # 转换新闻为响应模型
        for result in results:
            result['news'] = [NewsResponse.model_validate(n) for n in result['news']]

        return Response(
            success=True,
            data={
                "keyword": request.keyword,
                "similar_keywords": results
            }
        )
    except Exception as e:
        logger.error(f"相似度搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/date-range", response_model=Response)
async def search_by_date_range(
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    limit: int = Query(None, description="限制返回数量"),
    service: SearchService = Depends(get_search_service_dep)
):
    """
    按日期范围搜索
    """
    try:
        news_list = service.search_by_date_range(start_date, end_date, limit=limit)
        news_responses = [NewsResponse.model_validate(n) for n in news_list]

        return Response(
            success=True,
            data={
                "start_date": start_date,
                "end_date": end_date,
                "count": len(news_responses),
                "news": news_responses
            }
        )
    except Exception as e:
        logger.error(f"日期范围搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recent", response_model=Response)
async def search_recent(
    days: int = Query(7, description="最近N天"),
    limit: int = Query(None, description="限制返回数量"),
    service: SearchService = Depends(get_search_service_dep)
):
    """
    搜索最近N天的新闻
    """
    try:
        news_list = service.search_recent(days=days, limit=limit)
        news_responses = [NewsResponse.model_validate(n) for n in news_list]

        return Response(
            success=True,
            data={
                "days": days,
                "count": len(news_responses),
                "news": news_responses
            }
        )
    except Exception as e:
        logger.error(f"最近新闻搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/channel/{channel_id}", response_model=Response)
async def search_by_channel(
    channel_id: str,
    limit: int = Query(None, description="限制返回数量"),
    service: SearchService = Depends(get_search_service_dep)
):
    """
    按频道搜索（仅Crypto）
    """
    try:
        news_list = service.search_by_channel(channel_id, limit=limit)
        news_responses = [NewsResponse.model_validate(n) for n in news_list]

        return Response(
            success=True,
            data={
                "channel_id": channel_id,
                "count": len(news_responses),
                "news": news_responses
            }
        )
    except Exception as e:
        logger.error(f"频道搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/currency/{currency}", response_model=Response)
async def search_by_currency(
    currency: str,
    limit: int = Query(None, description="限制返回数量"),
    service: SearchService = Depends(get_search_service_dep)
):
    """
    按币种搜索（仅Crypto）
    """
    try:
        news_list = service.search_by_currency(currency, limit=limit)
        news_responses = [NewsResponse.model_validate(n) for n in news_list]

        return Response(
            success=True,
            data={
                "currency": currency,
                "count": len(news_responses),
                "news": news_responses
            }
        )
    except Exception as e:
        logger.error(f"币种搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/industry/{industry}", response_model=Response)
async def search_by_industry(
    industry: str,
    limit: int = Query(None, description="限制返回数量"),
    service: SearchService = Depends(get_search_service_dep)
):
    """
    按行业搜索（仅HKStocks）
    """
    try:
        news_list = service.search_by_industry(industry, limit=limit)
        news_responses = [NewsResponse.model_validate(n) for n in news_list]

        return Response(
            success=True,
            data={
                "industry": industry,
                "count": len(news_responses),
                "news": news_responses
            }
        )
    except Exception as e:
        logger.error(f"行业搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/advanced", response_model=Response)
async def advanced_search(
    request: SearchRequest,
    service: SearchService = Depends(get_search_service_dep)
):
    """
    高级搜索（多条件组合）
    """
    try:
        news_list = service.advanced_search(
            keywords=request.keywords,
            start_date=request.start_date,
            end_date=request.end_date,
            channel_ids=request.channel_ids,
            currencies=request.currencies,
            industries=request.industries,
            has_summary=request.has_summary,
            limit=request.limit
        )
        news_responses = [NewsResponse.model_validate(n) for n in news_list]

        return Response(
            success=True,
            data={
                "count": len(news_responses),
                "news": news_responses
            }
        )
    except Exception as e:
        logger.error(f"高级搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rank", response_model=Response)
async def search_and_rank(
    request: SearchRankRequest,
    service: SearchService = Depends(get_search_service_dep)
):
    """
    搜索并按相关性排序
    """
    try:
        results = service.search_and_rank(
            query=request.query,
            top_n=request.top_n,
            use_similarity=request.use_similarity
        )

        # 转换新闻为响应模型
        for result in results:
            result['news'] = NewsResponse.model_validate(result['news'])

        return Response(
            success=True,
            data={
                "query": request.query,
                "count": len(results),
                "results": results
            }
        )
    except Exception as e:
        logger.error(f"搜索排序失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/popular/keywords", response_model=Response)
async def get_popular_keywords(
    top_n: int = Query(20, description="返回前N个"),
    service: SearchService = Depends(get_search_service_dep)
):
    """
    获取热门关键词
    """
    try:
        keywords = service.get_popular_keywords(top_n=top_n)

        return Response(
            success=True,
            data={
                "top_n": top_n,
                "keywords": keywords
            }
        )
    except Exception as e:
        logger.error(f"获取热门关键词失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/popular/currencies", response_model=Response)
async def get_popular_currencies(
    top_n: int = Query(20, description="返回前N个"),
    service: SearchService = Depends(get_search_service_dep)
):
    """
    获取热门币种（仅Crypto）
    """
    try:
        currencies = service.get_popular_currencies(top_n=top_n)

        return Response(
            success=True,
            data={
                "top_n": top_n,
                "currencies": currencies
            }
        )
    except Exception as e:
        logger.error(f"获取热门币种失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
