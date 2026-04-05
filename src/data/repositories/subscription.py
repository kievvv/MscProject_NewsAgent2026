"""
订阅仓储
提供用户订阅和推送历史的数据访问接口
"""
from typing import List, Optional, Dict, Any

from src.data.repositories.base import BaseRepository
from src.core.models import Subscription, PushHistory, SubscriptionStatus


class SubscriptionRepository(BaseRepository[Subscription]):
    """订阅仓储"""

    @property
    def table_name(self) -> str:
        return "subscriptions"

    def _row_to_model(self, row: Dict[str, Any]) -> Subscription:
        is_active = row.get('is_active', 1)
        status = SubscriptionStatus.ACTIVE if is_active else SubscriptionStatus.INACTIVE

        return Subscription(
            id=row.get('id'),
            user_id=row.get('user_id', ''),
            keyword=row.get('keyword', ''),
            telegram_chat_id=row.get('telegram_chat_id'),
            status=status,
            created_at=row.get('created_at'),
        )

    def _model_to_row(self, model: Subscription) -> Dict[str, Any]:
        return {
            'id': model.id,
            'user_id': model.user_id,
            'keyword': model.keyword,
            'telegram_chat_id': model.telegram_chat_id,
            'is_active': 1 if model.is_active else 0,
        }

    def get_by_user(self, user_id: str, active_only: bool = True) -> List[Subscription]:
        """
        获取用户的所有订阅

        Args:
            user_id: 用户ID
            active_only: 是否只返回活跃订阅

        Returns:
            订阅列表
        """
        if active_only:
            where_clause = "user_id = ? AND is_active = 1"
        else:
            where_clause = "user_id = ?"

        return self.find(where_clause, (user_id,), "created_at DESC")

    def get_by_keyword(self, keyword: str, active_only: bool = True) -> List[Subscription]:
        """
        获取订阅某个关键词的所有用户

        Args:
            keyword: 关键词
            active_only: 是否只返回活跃订阅

        Returns:
            订阅列表
        """
        if active_only:
            where_clause = "keyword = ? AND is_active = 1"
        else:
            where_clause = "keyword = ?"

        return self.find(where_clause, (keyword,), "created_at")

    def create_or_update(self, user_id: str, keyword: str,
                        telegram_chat_id: Optional[str] = None) -> Subscription:
        """
        创建或更新订阅

        Args:
            user_id: 用户ID
            keyword: 关键词
            telegram_chat_id: Telegram聊天ID

        Returns:
            订阅对象
        """
        # 检查是否已存在
        existing = self.find_one("user_id = ? AND keyword = ?", (user_id, keyword))

        if existing:
            # 更新为活跃状态
            query = """
            UPDATE subscriptions
            SET is_active = 1, telegram_chat_id = ?
            WHERE id = ?
            """
            self.db_manager.execute_update(query, (telegram_chat_id, existing.id), self.db_path)
            return self.get_by_id(existing.id)
        else:
            # 创建新订阅
            subscription = Subscription(
                user_id=user_id,
                keyword=keyword,
                telegram_chat_id=telegram_chat_id,
                status=SubscriptionStatus.ACTIVE,
            )
            return self.create(subscription)

    def deactivate(self, subscription_id: int) -> bool:
        """
        停用订阅

        Args:
            subscription_id: 订阅ID

        Returns:
            是否成功
        """
        query = "UPDATE subscriptions SET is_active = 0 WHERE id = ?"
        affected = self.db_manager.execute_update(query, (subscription_id,), self.db_path)
        return affected > 0

    def activate(self, subscription_id: int) -> bool:
        """
        激活订阅

        Args:
            subscription_id: 订阅ID

        Returns:
            是否成功
        """
        query = "UPDATE subscriptions SET is_active = 1 WHERE id = ?"
        affected = self.db_manager.execute_update(query, (subscription_id,), self.db_path)
        return affected > 0

    def get_active_count(self, user_id: Optional[str] = None) -> int:
        """
        获取活跃订阅数量

        Args:
            user_id: 用户ID（可选）

        Returns:
            订阅数量
        """
        if user_id:
            return self.count("user_id = ? AND is_active = 1", (user_id,))
        else:
            return self.count("is_active = 1")


class PushHistoryRepository(BaseRepository[PushHistory]):
    """推送历史仓储"""

    @property
    def table_name(self) -> str:
        return "push_history"

    def _row_to_model(self, row: Dict[str, Any]) -> PushHistory:
        return PushHistory(
            id=row.get('id'),
            subscription_id=row.get('subscription_id', 0),
            news_id=row.get('news_id', 0),
            status=row.get('status', 'success'),
            pushed_at=row.get('pushed_at'),
        )

    def _model_to_row(self, model: PushHistory) -> Dict[str, Any]:
        return {
            'id': model.id,
            'subscription_id': model.subscription_id,
            'news_id': model.news_id,
            'status': model.status,
        }

    def record_push(self, subscription_id: int, news_id: int, status: str = 'success') -> PushHistory:
        """
        记录推送历史

        Args:
            subscription_id: 订阅ID
            news_id: 新闻ID
            status: 推送状态

        Returns:
            推送历史对象
        """
        history = PushHistory(
            subscription_id=subscription_id,
            news_id=news_id,
            status=status,
        )
        return self.create(history)

    def is_pushed(self, subscription_id: int, news_id: int) -> bool:
        """
        检查新闻是否已推送给该订阅

        Args:
            subscription_id: 订阅ID
            news_id: 新闻ID

        Returns:
            是否已推送
        """
        count = self.count(
            "subscription_id = ? AND news_id = ?",
            (subscription_id, news_id)
        )
        return count > 0

    def get_by_subscription(self, subscription_id: int,
                           limit: Optional[int] = None) -> List[PushHistory]:
        """
        获取订阅的推送历史

        Args:
            subscription_id: 订阅ID
            limit: 限制数量

        Returns:
            推送历史列表
        """
        return self.find(
            "subscription_id = ?",
            (subscription_id,),
            "pushed_at DESC",
            limit
        )

    def get_by_news(self, news_id: int) -> List[PushHistory]:
        """
        获取新闻的推送历史

        Args:
            news_id: 新闻ID

        Returns:
            推送历史列表
        """
        return self.find("news_id = ?", (news_id,), "pushed_at DESC")

    def get_push_statistics(self, subscription_id: Optional[int] = None,
                           days: int = 7) -> Dict[str, Any]:
        """
        获取推送统计

        Args:
            subscription_id: 订阅ID（可选）
            days: 统计天数

        Returns:
            统计信息
        """
        from datetime import datetime, timedelta

        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        if subscription_id:
            where_clause = "subscription_id = ? AND DATE(pushed_at) >= ?"
            params = (subscription_id, start_date)
        else:
            where_clause = "DATE(pushed_at) >= ?"
            params = (start_date,)

        # 总数
        total_count = self.count(where_clause, params)

        # 成功数
        success_count = self.count(
            where_clause + " AND status = 'success'",
            params
        )

        # 失败数
        failed_count = total_count - success_count

        # 每日统计
        daily_query = f"""
        SELECT DATE(pushed_at) as date, COUNT(*) as count,
               SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count
        FROM {self.table_name}
        WHERE {where_clause}
        GROUP BY DATE(pushed_at)
        ORDER BY date DESC
        """
        daily_stats = self.db_manager.execute_query(daily_query, params, self.db_path)

        return {
            'total_count': total_count,
            'success_count': success_count,
            'failed_count': failed_count,
            'success_rate': success_count / total_count if total_count > 0 else 0,
            'daily_stats': daily_stats,
        }


# 便捷函数
def get_subscription_repository() -> SubscriptionRepository:
    """获取订阅仓储"""
    return SubscriptionRepository()


def get_push_history_repository() -> PushHistoryRepository:
    """获取推送历史仓储"""
    return PushHistoryRepository()
