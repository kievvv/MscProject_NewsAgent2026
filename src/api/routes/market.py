"""
市场API路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException

from src.services import MarketService
from src.api.dependencies import get_market_service_dep
from src.api.schemas import (
    Response,
    PriceRequest,
    HistoricalPriceRequest,
    PriceChangeRequest,
    CorrelationRequest,
    SentimentRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])


@router.post("/price/current", response_model=Response)
async def get_current_price(
    request: PriceRequest,
    service: MarketService = Depends(get_market_service_dep)
):
    """
    获取当前价格
    """
    try:
        price_data = service.get_current_price(
            symbol=request.symbol,
            currency=request.currency
        )

        if not price_data:
            raise HTTPException(status_code=404, detail="价格数据不可用")

        return Response(
            success=True,
            data=price_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取价格失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/price/historical", response_model=Response)
async def get_historical_price(
    request: HistoricalPriceRequest,
    service: MarketService = Depends(get_market_service_dep)
):
    """
    获取历史价格
    """
    try:
        historical_data = service.get_historical_price(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            currency=request.currency
        )

        return Response(
            success=True,
            data={
                "symbol": request.symbol,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "data": historical_data
            }
        )
    except Exception as e:
        logger.error(f"获取历史价格失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/price/change", response_model=Response)
async def calculate_price_change(
    request: PriceChangeRequest,
    service: MarketService = Depends(get_market_service_dep)
):
    """
    计算价格变化
    """
    try:
        change_data = service.calculate_price_change(
            symbol=request.symbol,
            days=request.days
        )

        if not change_data:
            raise HTTPException(status_code=404, detail="价格数据不可用")

        return Response(
            success=True,
            data=change_data
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"计算价格变化失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/correlation", response_model=Response)
async def analyze_news_price_correlation(
    request: CorrelationRequest,
    service: MarketService = Depends(get_market_service_dep)
):
    """
    分析新闻热度与价格变化的关联
    """
    try:
        correlation_data = service.analyze_news_price_correlation(
            symbol=request.symbol,
            days=request.days
        )

        return Response(
            success=True,
            data=correlation_data
        )
    except Exception as e:
        logger.error(f"关联分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sentiment", response_model=Response)
async def get_market_sentiment(
    request: SentimentRequest,
    service: MarketService = Depends(get_market_service_dep)
):
    """
    获取市场情绪（基于新闻数量和价格变化）
    """
    try:
        sentiment_data = service.get_market_sentiment(
            symbol=request.symbol,
            days=request.days
        )

        return Response(
            success=True,
            data=sentiment_data
        )
    except Exception as e:
        logger.error(f"市场情绪分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/volume", response_model=Response)
async def get_volume_analysis(
    request: PriceChangeRequest,
    service: MarketService = Depends(get_market_service_dep)
):
    """
    获取成交量分析
    """
    try:
        volume_data = service.get_volume_analysis(
            symbol=request.symbol,
            days=request.days
        )

        return Response(
            success=True,
            data=volume_data
        )
    except Exception as e:
        logger.error(f"成交量分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
