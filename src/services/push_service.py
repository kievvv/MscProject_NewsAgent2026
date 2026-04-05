"""
推送服务
提供新闻推送和告警功能
"""
import logging
from typing import List, Optional, Dict, Any, Callable
from datetime import datetime

from src.data.repositories.news import NewsRepository
from src.analyzers import get_trend_analyzer
from src.core.models import News, NewsSource
from src.core.exceptions import ServiceException

logger = logging.getLogger(__name__)


class PushService:
    """
    推送服务

    功能：
    1. 关键词订阅推送
    2. 热度异常告警
    3. 自定义规则推送
    4. 批量推送
    """

    def __init__(self, source: NewsSource = NewsSource.CRYPTO):
        """
        初始化推送服务

        Args:
            source: 新闻来源
        """
        self.source = source
        self.news_repo = NewsRepository(source=source)

        # 延迟加载分析器
        self._trend_analyzer = None

        # 订阅规则存储（实际项目中应该持久化到数据库）
        self.subscriptions: Dict[str, Dict[str, Any]] = {}

    @property
    def trend_analyzer(self):
        """延迟加载趋势分析器"""
        if self._trend_analyzer is None:
            self._trend_analyzer = get_trend_analyzer()
        return self._trend_analyzer

    def subscribe_keyword(self,
                         user_id: str,
                         keyword: str,
                         callback: Optional[Callable] = None,
                         **options) -> str:
        """
        订阅关键词

        Args:
            user_id: 用户ID
            keyword: 关键词
            callback: 回调函数（用于推送）
            **options: 其他选项（如推送频率、过滤条件等）

        Returns:
            订阅ID
        """
        try:
            subscription_id = f"{user_id}_{keyword}_{datetime.now().timestamp()}"

            self.subscriptions[subscription_id] = {
                'user_id': user_id,
                'keyword': keyword,
                'callback': callback,
                'created_at': datetime.now().isoformat(),
                'options': options,
                'active': True
            }

            logger.info(f"订阅创建成功: {subscription_id}")
            return subscription_id

        except Exception as e:
            logger.error(f"创建订阅失败: {e}")
            raise ServiceException(f"Failed to create subscription: {e}")

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        取消订阅

        Args:
            subscription_id: 订阅ID

        Returns:
            是否成功
        """
        try:
            if subscription_id in self.subscriptions:
                self.subscriptions[subscription_id]['active'] = False
                logger.info(f"订阅已取消: {subscription_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"取消订阅失败: {e}")
            return False

    def get_user_subscriptions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户的所有订阅

        Args:
            user_id: 用户ID

        Returns:
            订阅列表
        """
        return [
            {
                'subscription_id': sub_id,
                **sub_data
            }
            for sub_id, sub_data in self.subscriptions.items()
            if sub_data['user_id'] == user_id and sub_data['active']
        ]

    def check_and_push(self, news: News) -> List[str]:
        """
        检查新闻是否匹配订阅并推送

        Args:
            news: 新闻对象

        Returns:
            推送的订阅ID列表
        """
        pushed = []

        for sub_id, sub_data in self.subscriptions.items():
            if not sub_data['active']:
                continue

            keyword = sub_data['keyword'].lower()

            # 检查是否匹配
            matched = False
            if keyword in news.title.lower():
                matched = True
            elif keyword in news.content.lower():
                matched = True
            elif news.keywords and keyword in news.keywords.lower():
                matched = True

            if matched:
                # 执行推送
                if sub_data.get('callback'):
                    try:
                        sub_data['callback'](news, sub_data)
                        pushed.append(sub_id)
                        logger.info(f"推送成功: {sub_id} -> 新闻 {news.id}")
                    except Exception as e:
                        logger.error(f"推送失败: {sub_id}, {e}")

        return pushed

    def check_anomaly_alerts(self,
                           keywords: Optional[List[str]] = None,
                           sensitivity: float = 2.0) -> List[Dict[str, Any]]:
        """
        检查异常告警

        Args:
            keywords: 要检查的关键词列表（None则检查所有热门关键词）
            sensitivity: 敏感度

        Returns:
            异常告警列表
        """
        try:
            alerts = []

            # 如果没有指定关键词，获取热门关键词
            if not keywords:
                from src.analyzers import get_similarity_analyzer
                analyzer = get_similarity_analyzer()
                stats = analyzer.get_keyword_statistics(source=self.source)
                keyword_counter = stats['keyword_counter']
                keywords = [kw for kw, _ in keyword_counter.most_common(20)]

            # 检测每个关键词的异常
            for keyword in keywords:
                try:
                    result = self.trend_analyzer.detect_anomalies(
                        keyword=keyword,
                        source=self.source,
                        sensitivity=sensitivity
                    )

                    # 如果有异常，创建告警
                    if result.get('anomalies'):
                        # 只取最近的异常
                        recent_anomalies = [
                            a for a in result['anomalies']
                            if self._is_recent_date(a['date'], days=3)
                        ]

                        if recent_anomalies:
                            alerts.append({
                                'keyword': keyword,
                                'type': 'anomaly',
                                'anomalies': recent_anomalies,
                                'statistics': result.get('statistics', {}),
                                'timestamp': datetime.now().isoformat()
                            })

                except Exception as e:
                    logger.debug(f"检查关键词 '{keyword}' 异常失败: {e}")
                    continue

            return alerts

        except Exception as e:
            logger.error(f"异常检测失败: {e}")
            return []

    def create_custom_alert(self,
                          user_id: str,
                          alert_type: str,
                          conditions: Dict[str, Any],
                          callback: Optional[Callable] = None) -> str:
        """
        创建自定义告警规则

        Args:
            user_id: 用户ID
            alert_type: 告警类型（如 'threshold', 'velocity', 'correlation'）
            conditions: 条件字典
            callback: 回调函数

        Returns:
            告警ID
        """
        try:
            alert_id = f"alert_{user_id}_{alert_type}_{datetime.now().timestamp()}"

            self.subscriptions[alert_id] = {
                'user_id': user_id,
                'type': 'custom_alert',
                'alert_type': alert_type,
                'conditions': conditions,
                'callback': callback,
                'created_at': datetime.now().isoformat(),
                'active': True
            }

            logger.info(f"自定义告警创建成功: {alert_id}")
            return alert_id

        except Exception as e:
            logger.error(f"创建自定义告警失败: {e}")
            raise ServiceException(f"Failed to create custom alert: {e}")

    def batch_push_to_users(self,
                          user_ids: List[str],
                          news: News,
                          message: Optional[str] = None) -> Dict[str, bool]:
        """
        批量推送给指定用户

        Args:
            user_ids: 用户ID列表
            news: 新闻对象
            message: 推送消息（可选）

        Returns:
            {user_id: success} 字典
        """
        results = {}

        for user_id in user_ids:
            try:
                # 这里应该调用实际的推送服务（如Telegram、邮件等）
                # 示例代码只记录日志
                logger.info(f"推送给用户 {user_id}: 新闻 {news.id}")
                results[user_id] = True

            except Exception as e:
                logger.error(f"推送给用户 {user_id} 失败: {e}")
                results[user_id] = False

        return results

    def get_push_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        获取推送统计

        Args:
            user_id: 用户ID（None则统计所有）

        Returns:
            统计信息
        """
        try:
            subscriptions = self.subscriptions.values()

            if user_id:
                subscriptions = [
                    sub for sub in subscriptions
                    if sub.get('user_id') == user_id
                ]

            total = len(subscriptions)
            active = len([s for s in subscriptions if s.get('active')])

            return {
                'total_subscriptions': total,
                'active_subscriptions': active,
                'inactive_subscriptions': total - active
            }

        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return {}

    def _is_recent_date(self, date_str: str, days: int = 3) -> bool:
        """
        判断日期是否在最近N天内

        Args:
            date_str: 日期字符串 (YYYY-MM-DD)
            days: 天数

        Returns:
            是否最近
        """
        try:
            date = datetime.fromisoformat(date_str.split('T')[0])
            now = datetime.now()
            return (now - date).days <= days
        except Exception:
            return False


# 便捷函数
def get_push_service(source: NewsSource = NewsSource.CRYPTO) -> PushService:
    """
    获取推送服务实例

    Args:
        source: 新闻来源

    Returns:
        PushService实例
    """
    return PushService(source=source)
