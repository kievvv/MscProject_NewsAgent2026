"""
趋势API路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from src.services import TrendService
from src.api.dependencies import get_trend_service_dep
from src.api.schemas import (
    Response,
    TrendAnalysisRequest,
    CompareKeywordsRequest,
    AnomalyDetectionRequest,
    CorrelationAnalysisRequest,
    TrendPredictionRequest,
    TrendingKeywordsRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trend", tags=["trend"])


@router.post("/analyze", response_model=Response)
async def analyze_keyword_trend(
    request: TrendAnalysisRequest,
    service: TrendService = Depends(get_trend_service_dep)
):
    """
    分析关键词趋势
    """
    try:
        trend = service.analyze_keyword_trend(
            keyword=request.keyword,
            start_date=request.start_date,
            end_date=request.end_date,
            granularity=request.granularity
        )

        return Response(
            success=True,
            data={
                "keyword": trend.keyword,
                "total_count": trend.total_count,
                "active_days": trend.active_days,
                "date_range": trend.date_range,
                "avg_daily_count": trend.avg_daily_count,
                "peak_date": trend.peak_date,
                "peak_count": trend.peak_count,
                "daily_trend": trend.daily_trend
            }
        )
    except Exception as e:
        logger.error(f"趋势分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", response_model=Response)
async def compare_keywords(
    request: CompareKeywordsRequest,
    service: TrendService = Depends(get_trend_service_dep)
):
    """
    对比多个关键词的趋势
    """
    try:
        comparison = service.compare_keywords(
            keywords=request.keywords,
            start_date=request.start_date,
            end_date=request.end_date
        )

        return Response(
            success=True,
            data=comparison
        )
    except Exception as e:
        logger.error(f"关键词对比失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/anomalies", response_model=Response)
async def detect_anomalies(
    request: AnomalyDetectionRequest,
    service: TrendService = Depends(get_trend_service_dep)
):
    """
    检测关键词热度异常
    """
    try:
        result = service.detect_anomalies(
            keyword=request.keyword,
            start_date=request.start_date,
            end_date=request.end_date,
            sensitivity=request.sensitivity
        )

        return Response(
            success=True,
            data=result
        )
    except Exception as e:
        logger.error(f"异常检测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/velocity", response_model=Response)
async def calculate_growth_velocity(
    request: TrendAnalysisRequest,
    service: TrendService = Depends(get_trend_service_dep)
):
    """
    计算关键词增长速度
    """
    try:
        result = service.calculate_growth_velocity(
            keyword=request.keyword,
            start_date=request.start_date,
            end_date=request.end_date
        )

        return Response(
            success=True,
            data=result
        )
    except Exception as e:
        logger.error(f"增长速度计算失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/correlation", response_model=Response)
async def analyze_correlation(
    request: CorrelationAnalysisRequest,
    service: TrendService = Depends(get_trend_service_dep)
):
    """
    分析两个关键词的关联性
    """
    try:
        result = service.analyze_correlation(
            keyword1=request.keyword1,
            keyword2=request.keyword2,
            start_date=request.start_date,
            end_date=request.end_date
        )

        return Response(
            success=True,
            data=result
        )
    except Exception as e:
        logger.error(f"关联分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot-dates", response_model=Response)
async def get_hot_dates(
    keyword: str = Query(..., description="关键词"),
    top_n: int = Query(10, description="返回前N天"),
    service: TrendService = Depends(get_trend_service_dep)
):
    """
    获取关键词最热门的日期
    """
    try:
        hot_dates = service.get_hot_dates(keyword=keyword, top_n=top_n)

        return Response(
            success=True,
            data={
                "keyword": keyword,
                "hot_dates": hot_dates
            }
        )
    except Exception as e:
        logger.error(f"获取热门日期失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trending", response_model=Response)
async def get_trending_keywords(
    request: TrendingKeywordsRequest,
    service: TrendService = Depends(get_trend_service_dep)
):
    """
    获取当前热门关键词（基于最近的趋势）
    """
    try:
        trending = service.get_trending_keywords(
            days=request.days,
            top_n=request.top_n,
            min_count=request.min_count
        )

        return Response(
            success=True,
            data={
                "days": request.days,
                "trending_keywords": trending
            }
        )
    except Exception as e:
        logger.error(f"获取热门关键词失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lifecycle", response_model=Response)
async def analyze_keyword_lifecycle(
    request: TrendAnalysisRequest,
    service: TrendService = Depends(get_trend_service_dep)
):
    """
    分析关键词生命周期（兴起、高峰、衰落）
    """
    try:
        result = service.analyze_keyword_lifecycle(
            keyword=request.keyword,
            start_date=request.start_date,
            end_date=request.end_date
        )

        return Response(
            success=True,
            data=result
        )
    except Exception as e:
        logger.error(f"生命周期分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict", response_model=Response)
async def predict_trend(
    request: TrendPredictionRequest,
    service: TrendService = Depends(get_trend_service_dep)
):
    """
    简单趋势预测（基于历史数据）
    """
    try:
        prediction = service.predict_trend(
            keyword=request.keyword,
            days=request.days
        )

        return Response(
            success=True,
            data=prediction
        )
    except Exception as e:
        logger.error(f"趋势预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
