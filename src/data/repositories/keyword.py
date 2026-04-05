"""
关键词仓储
提供关键词和趋势数据的访问接口
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from src.data.repositories.base import BaseRepository
from src.data.schema import (
    CREATE_NEWS_KEYWORDS_TABLE,
    CREATE_KEYWORD_TRENDS_TABLE,
    CREATE_NEWS_KEYWORDS_INDEX,
    CREATE_NEWS_ID_INDEX,
    CREATE_KEYWORD_TRENDS_INDEX,
)
from src.core.models import Keyword, KeywordTrend

logger = logging.getLogger(__name__)


def _ensure_keyword_tables(repo: BaseRepository) -> None:
    """确保关键词与趋势表在目标数据库中存在。"""
    for sql in (
        CREATE_NEWS_KEYWORDS_TABLE,
        CREATE_KEYWORD_TRENDS_TABLE,
        CREATE_NEWS_KEYWORDS_INDEX,
        CREATE_NEWS_ID_INDEX,
        CREATE_KEYWORD_TRENDS_INDEX,
    ):
        try:
            repo.db_manager.execute_update(sql, db_path=repo.db_path)
        except Exception as exc:
            logger.warning(f"初始化关键词表结构失败: {exc}")


class KeywordRepository(BaseRepository[Keyword]):
    """关键词仓储"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _ensure_keyword_tables(self)

    @property
    def table_name(self) -> str:
        return "news_keywords"

    def _row_to_model(self, row: Dict[str, Any]) -> Keyword:
        return Keyword(
            id=row.get('id'),
            news_id=row.get('news_id'),
            keyword=row.get('keyword', ''),
            weight=row.get('weight', 0.0),
            created_at=row.get('created_at'),
        )

    def _model_to_row(self, model: Keyword) -> Dict[str, Any]:
        return {
            'id': model.id,
            'news_id': model.news_id,
            'keyword': model.keyword,
            'weight': model.weight,
        }

    def get_by_news_id(self, news_id: int) -> List[Keyword]:
        """
        获取指定新闻的所有关键词

        Args:
            news_id: 新闻ID

        Returns:
            关键词列表
        """
        return self.find("news_id = ?", (news_id,), "weight DESC")

    def get_by_keyword(self, keyword: str, limit: Optional[int] = None) -> List[Keyword]:
        """
        获取指定关键词的所有记录

        Args:
            keyword: 关键词
            limit: 限制数量

        Returns:
            关键词记录列表
        """
        return self.find("keyword = ?", (keyword,), "created_at DESC", limit)

    def save_batch(self, news_id: int, keywords: List[tuple]) -> int:
        """
        批量保存新闻的关键词

        Args:
            news_id: 新闻ID
            keywords: [(keyword, weight), ...]

        Returns:
            保存的数量
        """
        if not keywords:
            return 0

        query = """
        INSERT OR REPLACE INTO news_keywords (news_id, keyword, weight)
        VALUES (?, ?, ?)
        """
        params_list = [(news_id, kw, weight) for kw, weight in keywords]
        return self.db_manager.execute_many(query, params_list, self.db_path)

    def add_or_update_keyword(
        self,
        keyword: str,
        news_id: int,
        news_date: Optional[str] = None,
        weight: float = 1.0
    ) -> bool:
        """
        保存单个关键词，并同步更新关键词趋势表。

        Args:
            keyword: 关键词
            news_id: 新闻ID
            news_date: 新闻日期
            weight: 关键词权重

        Returns:
            是否成功
        """
        query = """
        INSERT OR REPLACE INTO news_keywords (news_id, keyword, weight)
        VALUES (?, ?, ?)
        """
        affected = self.db_manager.execute_update(query, (news_id, keyword, weight), self.db_path)

        if news_date:
            normalized_date = str(news_date).replace('T', ' ').split('+')[0].split(' ')[0]
            trend_query = """
            INSERT INTO keyword_trends (keyword, date, count, total_weight, updated_at)
            VALUES (?, ?, 1, ?, datetime('now'))
            ON CONFLICT(keyword, date) DO UPDATE SET
                count = count + 1,
                total_weight = total_weight + excluded.total_weight,
                updated_at = excluded.updated_at
            """
            self.db_manager.execute_update(
                trend_query,
                (keyword, normalized_date, weight),
                self.db_path
            )

        return affected >= 0

    def get_top_keywords(self, limit: int = 20, min_count: int = 1) -> List[Dict[str, Any]]:
        """
        获取出现频率最高的关键词

        Args:
            limit: 限制数量
            min_count: 最小出现次数

        Returns:
            关键词统计列表 [{'keyword': str, 'count': int, 'avg_weight': float}, ...]
        """
        query = """
        SELECT keyword, COUNT(*) as count, AVG(weight) as avg_weight
        FROM news_keywords
        GROUP BY keyword
        HAVING count >= ?
        ORDER BY count DESC, avg_weight DESC
        LIMIT ?
        """
        return self.db_manager.execute_query(query, (min_count, limit), self.db_path)

    def check_keywords_exist(self, news_ids: List[int]) -> Dict[int, bool]:
        """
        检查哪些新闻已经提取过关键词

        Args:
            news_ids: 新闻ID列表

        Returns:
            {news_id: exists} 字典
        """
        if not news_ids:
            return {}

        placeholders = ','.join('?' * len(news_ids))
        query = f"""
        SELECT DISTINCT news_id
        FROM news_keywords
        WHERE news_id IN ({placeholders})
        """
        results = self.db_manager.execute_query(query, tuple(news_ids), self.db_path)
        existing_ids = {row['news_id'] for row in results}
        return {nid: nid in existing_ids for nid in news_ids}


class TrendRepository(BaseRepository[KeywordTrend]):
    """关键词趋势仓储"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _ensure_keyword_tables(self)

    @property
    def table_name(self) -> str:
        return "keyword_trends"

    def _row_to_model(self, row: Dict[str, Any]) -> KeywordTrend:
        return KeywordTrend(
            id=row.get('id'),
            keyword=row.get('keyword', ''),
            date=row.get('date', ''),
            count=row.get('count', 0),
            total_weight=row.get('total_weight', 0.0),
            updated_at=row.get('updated_at'),
        )

    def _model_to_row(self, model: KeywordTrend) -> Dict[str, Any]:
        return {
            'id': model.id,
            'keyword': model.keyword,
            'date': model.date,
            'count': model.count,
            'total_weight': model.total_weight,
        }

    def get_trend(self, keyword: str, start_date: Optional[str] = None,
                  end_date: Optional[str] = None) -> List[KeywordTrend]:
        """
        获取关键词的热度趋势

        Args:
            keyword: 关键词
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            趋势数据列表
        """
        if start_date and end_date:
            where_clause = "keyword = ? AND date >= ? AND date <= ?"
            params = (keyword, start_date, end_date)
        elif start_date:
            where_clause = "keyword = ? AND date >= ?"
            params = (keyword, start_date)
        elif end_date:
            where_clause = "keyword = ? AND date <= ?"
            params = (keyword, end_date)
        else:
            where_clause = "keyword = ?"
            params = (keyword,)

        return self.find(where_clause, params, "date")

    def get_hot_dates(self, keyword: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        获取关键词最热门的日期

        Args:
            keyword: 关键词
            top_n: 返回数量

        Returns:
            热门日期列表 [{'date': str, 'count': int}, ...]
        """
        query = """
        SELECT date, count
        FROM keyword_trends
        WHERE keyword = ?
        ORDER BY count DESC
        LIMIT ?
        """
        return self.db_manager.execute_query(query, (keyword, top_n), self.db_path)

    def save_or_update(self, keyword: str, date: str, count: int, total_weight: float) -> bool:
        """
        保存或更新趋势数据

        Args:
            keyword: 关键词
            date: 日期
            count: 出现次数
            total_weight: 总权重

        Returns:
            是否成功
        """
        query = """
        INSERT INTO keyword_trends (keyword, date, count, total_weight, updated_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(keyword, date) DO UPDATE SET
            count = excluded.count,
            total_weight = excluded.total_weight,
            updated_at = excluded.updated_at
        """
        affected = self.db_manager.execute_update(
            query, (keyword, date, count, total_weight), self.db_path
        )
        return affected > 0

    def get_trending_keywords(self, days: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取最近trending的关键词

        Args:
            days: 统计天数
            limit: 限制数量

        Returns:
            trending关键词列表 [{'keyword': str, 'total_count': int, 'avg_count': float}, ...]
        """
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        query = """
        SELECT keyword, SUM(count) as total_count, AVG(count) as avg_count
        FROM keyword_trends
        WHERE date >= ?
        GROUP BY keyword
        ORDER BY total_count DESC
        LIMIT ?
        """
        return self.db_manager.execute_query(query, (start_date, limit), self.db_path)

    def compare_keywords(self, keywords: List[str], start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        对比多个关键词的趋势

        Args:
            keywords: 关键词列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            对比结果列表
        """
        if not keywords:
            return []

        placeholders = ','.join('?' * len(keywords))
        base_query = f"""
        SELECT keyword, date, count, total_weight
        FROM keyword_trends
        WHERE keyword IN ({placeholders})
        """

        params = list(keywords)
        if start_date:
            base_query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            base_query += " AND date <= ?"
            params.append(end_date)

        base_query += " ORDER BY date, keyword"

        return self.db_manager.execute_query(base_query, tuple(params), self.db_path)


# 便捷函数
def get_keyword_repository() -> KeywordRepository:
    """获取关键词仓储"""
    return KeywordRepository()


def get_trend_repository() -> TrendRepository:
    """获取趋势仓储"""
    return TrendRepository()
