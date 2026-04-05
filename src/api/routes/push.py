"""
推送API路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query

from src.services import PushService
from src.api.dependencies import get_push_service_dep
from src.api.schemas import (
    Response,
    SubscribeRequest,
    UnsubscribeRequest,
    AnomalyAlertRequest,
    CustomAlertRequest,
    BatchPushRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/push", tags=["push"])


@router.post("/subscribe", response_model=Response)
async def subscribe_keyword(
    request: SubscribeRequest,
    service: PushService = Depends(get_push_service_dep)
):
    """
    订阅关键词
    """
    try:
        subscription_id = service.subscribe_keyword(
            user_id=request.user_id,
            keyword=request.keyword,
            **request.options if request.options else {}
        )

        return Response(
            success=True,
            message="订阅创建成功",
            data={"subscription_id": subscription_id}
        )
    except Exception as e:
        logger.error(f"创建订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unsubscribe", response_model=Response)
async def unsubscribe(
    request: UnsubscribeRequest,
    service: PushService = Depends(get_push_service_dep)
):
    """
    取消订阅
    """
    try:
        success = service.unsubscribe(request.subscription_id)

        if not success:
            raise HTTPException(status_code=404, detail="订阅不存在")

        return Response(
            success=True,
            message="订阅已取消"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions/{user_id}", response_model=Response)
async def get_user_subscriptions(
    user_id: str,
    service: PushService = Depends(get_push_service_dep)
):
    """
    获取用户的所有订阅
    """
    try:
        subscriptions = service.get_user_subscriptions(user_id)

        return Response(
            success=True,
            data={
                "user_id": user_id,
                "count": len(subscriptions),
                "subscriptions": subscriptions
            }
        )
    except Exception as e:
        logger.error(f"获取订阅失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/anomalies", response_model=Response)
async def check_anomaly_alerts(
    request: AnomalyAlertRequest,
    service: PushService = Depends(get_push_service_dep)
):
    """
    检查异常告警
    """
    try:
        alerts = service.check_anomaly_alerts(
            keywords=request.keywords,
            sensitivity=request.sensitivity
        )

        return Response(
            success=True,
            data={
                "count": len(alerts),
                "alerts": alerts
            }
        )
    except Exception as e:
        logger.error(f"异常检测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/custom", response_model=Response)
async def create_custom_alert(
    request: CustomAlertRequest,
    service: PushService = Depends(get_push_service_dep)
):
    """
    创建自定义告警规则
    """
    try:
        alert_id = service.create_custom_alert(
            user_id=request.user_id,
            alert_type=request.alert_type,
            conditions=request.conditions
        )

        return Response(
            success=True,
            message="自定义告警创建成功",
            data={"alert_id": alert_id}
        )
    except Exception as e:
        logger.error(f"创建自定义告警失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=Response)
async def batch_push_to_users(
    request: BatchPushRequest,
    service: PushService = Depends(get_push_service_dep)
):
    """
    批量推送给指定用户
    """
    try:
        # 获取新闻
        from src.api.dependencies import get_news_service_dep
        news_service = get_news_service_dep()
        news = news_service.get_news(request.news_id)

        if not news:
            raise HTTPException(status_code=404, detail="新闻不存在")

        # 批量推送
        results = service.batch_push_to_users(
            user_ids=request.user_ids,
            news=news,
            message=request.message
        )

        success_count = sum(1 for v in results.values() if v)

        return Response(
            success=True,
            message=f"批量推送完成，成功 {success_count}/{len(results)} 个用户",
            data=results
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量推送失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=Response)
async def get_push_statistics(
    user_id: str = Query(None, description="用户ID（None则统计所有）"),
    service: PushService = Depends(get_push_service_dep)
):
    """
    获取推送统计
    """
    try:
        stats = service.get_push_statistics(user_id=user_id)

        return Response(
            success=True,
            data=stats
        )
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
