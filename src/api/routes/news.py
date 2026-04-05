"""
新闻API路由
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from src.services import NewsService
from src.api.dependencies import get_news_service_dep, get_pagination_params
from src.api.schemas import (
    Response,
    PaginatedResponse,
    NewsCreate,
    NewsUpdate,
    NewsResponse,
    BatchGenerateRequest,
    StatisticsResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news", tags=["news"])


@router.post("/", response_model=Response)
async def create_news(
    news_data: NewsCreate,
    service: NewsService = Depends(get_news_service_dep)
):
    """
    创建新闻（自动提取关键词）
    """
    try:
        news = service.create_news(**news_data.model_dump())
        return Response(
            success=True,
            message="新闻创建成功",
            data=NewsResponse.model_validate(news)
        )
    except Exception as e:
        logger.error(f"创建新闻失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{news_id}", response_model=Response)
async def get_news(
    news_id: str,
    service: NewsService = Depends(get_news_service_dep)
):
    """
    获取单条新闻
    """
    try:
        news = service.get_news(news_id)
        if not news:
            raise HTTPException(status_code=404, detail="新闻不存在")

        return Response(
            success=True,
            data=NewsResponse.model_validate(news)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取新闻失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{news_id}", response_model=Response)
async def update_news(
    news_id: str,
    update_data: NewsUpdate,
    service: NewsService = Depends(get_news_service_dep)
):
    """
    更新新闻
    """
    try:
        # 过滤None值
        update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}

        if not update_dict:
            raise HTTPException(status_code=400, detail="没有提供更新数据")

        news = service.update_news(news_id, **update_dict)
        if not news:
            raise HTTPException(status_code=404, detail="新闻不存在")

        return Response(
            success=True,
            message="新闻更新成功",
            data=NewsResponse.model_validate(news)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新新闻失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{news_id}", response_model=Response)
async def delete_news(
    news_id: str,
    service: NewsService = Depends(get_news_service_dep)
):
    """
    删除新闻
    """
    try:
        success = service.delete_news(news_id)
        if not success:
            raise HTTPException(status_code=404, detail="新闻不存在")

        return Response(
            success=True,
            message="新闻删除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除新闻失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=PaginatedResponse)
async def list_news(
    pagination: dict = Depends(get_pagination_params),
    service: NewsService = Depends(get_news_service_dep)
):
    """
    获取新闻列表（分页）
    """
    try:
        # 获取所有新闻
        all_news = service.get_all_news()
        total = len(all_news)

        # 分页
        start = pagination['offset']
        end = start + pagination['limit']
        news_page = all_news[start:end]

        # 转换为响应模型
        news_responses = [NewsResponse.model_validate(n) for n in news_page]

        return PaginatedResponse(
            success=True,
            data=news_responses,
            total=total,
            page=pagination['page'],
            page_size=pagination['page_size'],
            total_pages=(total + pagination['page_size'] - 1) // pagination['page_size']
        )
    except Exception as e:
        logger.error(f"获取新闻列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-date/", response_model=Response)
async def get_news_by_date_range(
    start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
    service: NewsService = Depends(get_news_service_dep)
):
    """
    按日期范围获取新闻
    """
    try:
        news_list = service.get_news_by_date_range(start_date, end_date)
        news_responses = [NewsResponse.model_validate(n) for n in news_list]

        return Response(
            success=True,
            data=news_responses
        )
    except Exception as e:
        logger.error(f"获取新闻失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-channel/{channel_id}", response_model=Response)
async def get_news_by_channel(
    channel_id: str,
    limit: Optional[int] = Query(None, description="限制返回数量"),
    service: NewsService = Depends(get_news_service_dep)
):
    """
    按频道获取新闻（仅Crypto）
    """
    try:
        news_list = service.get_news_by_channel(channel_id, limit=limit)
        news_responses = [NewsResponse.model_validate(n) for n in news_list]

        return Response(
            success=True,
            data=news_responses
        )
    except Exception as e:
        logger.error(f"获取新闻失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-keyword/{keyword}", response_model=Response)
async def get_news_by_keyword(
    keyword: str,
    limit: Optional[int] = Query(None, description="限制返回数量"),
    service: NewsService = Depends(get_news_service_dep)
):
    """
    按关键词获取新闻
    """
    try:
        news_list = service.get_news_by_keyword(keyword, limit=limit)
        news_responses = [NewsResponse.model_validate(n) for n in news_list]

        return Response(
            success=True,
            data=news_responses
        )
    except Exception as e:
        logger.error(f"获取新闻失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{news_id}/summary", response_model=Response)
async def generate_summary(
    news_id: str,
    force: bool = Query(False, description="是否强制重新生成"),
    service: NewsService = Depends(get_news_service_dep)
):
    """
    为新闻生成摘要
    """
    try:
        summary = service.generate_summary(news_id, force=force)
        if summary is None:
            raise HTTPException(status_code=404, detail="新闻不存在")

        return Response(
            success=True,
            message="摘要生成成功",
            data={"summary": summary}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成摘要失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/summaries", response_model=Response)
async def batch_generate_summaries(
    request: BatchGenerateRequest,
    service: NewsService = Depends(get_news_service_dep)
):
    """
    批量生成摘要
    """
    try:
        results = service.batch_generate_summaries(
            news_ids=request.news_ids,
            force=request.force,
            limit=request.limit
        )

        return Response(
            success=True,
            message=f"批量生成完成，成功 {len(results)} 条",
            data=results
        )
    except Exception as e:
        logger.error(f"批量生成摘要失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/keywords", response_model=Response)
async def batch_extract_keywords(
    request: BatchGenerateRequest,
    service: NewsService = Depends(get_news_service_dep)
):
    """
    批量提取关键词
    """
    try:
        results = service.batch_extract_keywords(
            news_ids=request.news_ids,
            force=request.force,
            limit=request.limit
        )

        return Response(
            success=True,
            message=f"批量提取完成，成功 {len(results)} 条",
            data=results
        )
    except Exception as e:
        logger.error(f"批量提取关键词失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/", response_model=Response)
async def get_statistics(
    service: NewsService = Depends(get_news_service_dep)
):
    """
    获取统计信息
    """
    try:
        stats = service.get_statistics()
        return Response(
            success=True,
            data=stats
        )
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
