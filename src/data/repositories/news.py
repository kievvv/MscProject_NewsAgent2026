"""
新闻仓储
提供新闻数据的访问接口
"""
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta

from src.data.repositories.base import BaseRepository
from src.core.models import News, NewsSource
from config.settings import settings


class NewsRepository(BaseRepository[News]):
    """
    新闻仓储类
    支持加密货币新闻和港股新闻
    """

    def __init__(self, source: NewsSource = NewsSource.CRYPTO, **kwargs):
        """
        初始化新闻仓储

        Args:
            source: 新闻来源
        """
        self.source = source

        # 根据来源选择数据库和表
        if source == NewsSource.CRYPTO:
            db_path = settings.crypto_db_path_full
            table = "messages"
        else:  # HKSTOCKS
            db_path = settings.history_db_path_full
            table = "hkstocks_news"

        super().__init__(db_path=db_path, **kwargs)
        self._table_name = table
        self._columns_cache: Optional[set[str]] = None
        self._ensure_schema_compatibility()

    @property
    def table_name(self) -> str:
        return self._table_name

    @property
    def columns(self) -> set[str]:
        """获取当前表列并缓存。"""
        if self._columns_cache is None:
            self._columns_cache = set(self.db_manager.get_table_columns(self.table_name, self.db_path))
        return self._columns_cache

    def _refresh_columns(self) -> None:
        self._columns_cache = set(self.db_manager.get_table_columns(self.table_name, self.db_path))

    def _ensure_schema_compatibility(self) -> None:
        """确保历史数据库结构与当前代码兼容。"""
        if self.source != NewsSource.CRYPTO:
            return

        if not self.db_manager.table_exists(self.table_name, self.db_path):
            create_table = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT,
                message_id INTEGER,
                text TEXT NOT NULL,
                url TEXT,
                keywords TEXT,
                currency TEXT,
                abstract TEXT,
                date TEXT NOT NULL,
                original_text TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
            self.db_manager.execute_update(create_table, db_path=self.db_path)

        existing_columns = set(self.db_manager.get_table_columns(self.table_name, self.db_path))
        desired_columns = {
            "url": "TEXT",
            "keywords": "TEXT",
            "currency": "TEXT",
            "abstract": "TEXT",
            "original_text": "TEXT",
            "created_at": "TEXT",
        }
        for column_name, column_type in desired_columns.items():
            if column_name not in existing_columns:
                alter_sql = f"ALTER TABLE {self.table_name} ADD COLUMN {column_name} {column_type}"
                self.db_manager.execute_update(alter_sql, db_path=self.db_path)

        if "summary" in existing_columns and "abstract" in self.db_manager.get_table_columns(self.table_name, self.db_path):
            self.db_manager.execute_update(
                f"UPDATE {self.table_name} SET abstract = COALESCE(abstract, summary) WHERE summary IS NOT NULL",
                db_path=self.db_path,
            )

        # 清理重复消息，保留最早插入的一条，再建立唯一索引。
        dedupe_sql = f"""
        DELETE FROM {self.table_name}
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM {self.table_name}
            WHERE channel_id IS NOT NULL AND message_id IS NOT NULL
            GROUP BY channel_id, message_id
        )
        AND channel_id IS NOT NULL AND message_id IS NOT NULL
        """
        self.db_manager.execute_update(dedupe_sql, db_path=self.db_path)
        self.db_manager.execute_update(
            f"CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_channel_message_unique "
            f"ON {self.table_name}(channel_id, message_id)",
            db_path=self.db_path,
        )
        self.db_manager.execute_update(
            f"CREATE INDEX IF NOT EXISTS idx_messages_date ON {self.table_name}(date DESC)",
            db_path=self.db_path,
        )
        self.db_manager.execute_update(
            f"CREATE INDEX IF NOT EXISTS idx_messages_channel_date ON {self.table_name}(channel_id, date DESC)",
            db_path=self.db_path,
        )
        self._refresh_columns()

    def _row_to_model(self, row: Dict[str, Any]) -> News:
        """将数据库行转换为News模型"""
        if self.source == NewsSource.CRYPTO:
            abstract_value = row.get('abstract')
            if abstract_value is None:
                abstract_value = row.get('summary')
            return News(
                id=row.get('id'),
                source=NewsSource.CRYPTO,
                channel_id=row.get('channel_id'),
                message_id=row.get('message_id'),
                text=row.get('text', ''),
                original_text=row.get('original_text'),
                url=row.get('url'),
                keywords=row.get('keywords'),
                currency=row.get('currency'),
                abstract=abstract_value,
                date=row.get('date'),
                created_at=row.get('created_at'),
            )
        else:  # HKSTOCKS
            return News(
                id=row.get('id'),
                source=NewsSource.HKSTOCKS,
                title=row.get('title'),
                text=row.get('content', ''),
                url=row.get('url'),
                keywords=row.get('keywords'),
                industry=row.get('industry'),
                abstract=row.get('summary') or row.get('abstract'),
                date=row.get('publish_date') or row.get('date'),
                created_at=row.get('created_at'),
            )

    def _model_to_row(self, model: News) -> Dict[str, Any]:
        """将News模型转换为数据库行"""
        if self.source == NewsSource.CRYPTO:
            return {
                'id': model.id,
                'channel_id': model.channel_id,
                'message_id': model.message_id,
                'text': model.text,
                'original_text': model.original_text,
                'url': model.url,
                'keywords': model.keywords,
                'currency': model.currency,
                'abstract': model.abstract,
                'date': model.date,
            }
        else:  # HKSTOCKS
            return {
                'id': model.id,
                'title': model.title,
                'url': model.url,
                'content': model.text,
                'keywords': model.keywords,
                'industry': model.industry,
                'publish_date': model.date,
            }

    def _row_to_insert_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """根据当前表结构过滤写入列。"""
        row.pop('id', None)
        filtered: Dict[str, Any] = {}
        for key, value in row.items():
            if key in self.columns:
                filtered[key] = value
        if self.source == NewsSource.CRYPTO and 'abstract' in self.columns and 'summary' in self.columns:
            filtered['summary'] = filtered.get('abstract')
        return filtered

    def create(self, model: Optional[News] = None, **kwargs) -> News:
        """兼容 model / kwargs 两种创建方式。"""
        if model is None:
            if 'content' in kwargs and 'text' not in kwargs:
                kwargs['text'] = kwargs.pop('content')
            if 'summary' in kwargs and 'abstract' not in kwargs:
                kwargs['abstract'] = kwargs.pop('summary')
            model = News(source=self.source, **kwargs)
        row = self._row_to_insert_dict(self._model_to_row(model))
        columns = ', '.join(row.keys())
        placeholders = ', '.join(['?' for _ in row])
        insert_prefix = "INSERT OR IGNORE" if self.source == NewsSource.CRYPTO else "INSERT"
        query = f"{insert_prefix} INTO {self.table_name} ({columns}) VALUES ({placeholders})"
        self.db_manager.execute_update(query, tuple(row.values()), self.db_path)

        if self.source == NewsSource.CRYPTO and model.channel_id and model.message_id is not None:
            existing = self.get_by_channel_message(model.channel_id, model.message_id)
            if existing:
                return existing

        created = None
        latest_query = f"SELECT * FROM {self.table_name} ORDER BY id DESC LIMIT 1"
        latest_rows = self.db_manager.execute_query(latest_query, db_path=self.db_path)
        if latest_rows:
            created = self._row_to_model(latest_rows[0])
        if created is None and self.source == NewsSource.CRYPTO and model.channel_id and model.message_id is not None:
            created = self.get_by_channel_message(model.channel_id, model.message_id)
        if created is None:
            raise ValueError(f"Failed to create record in {self.table_name}")
        return created

    def update(self, id: int, model: Optional[News] = None, **kwargs) -> Optional[News]:
        """兼容 model / kwargs 两种更新方式。"""
        if model is not None:
            row = self._model_to_row(model)
        else:
            current = self.get_by_id(id)
            if current is None:
                return None
            merged = current.to_dict()
            if 'summary' in kwargs and 'abstract' not in kwargs:
                kwargs['abstract'] = kwargs['summary']
            merged.update(kwargs)
            model = News.from_dict(merged)
            row = self._model_to_row(model)

        row = self._row_to_insert_dict(row)
        if not row:
            return self.get_by_id(id)
        set_clause = ', '.join([f"{k} = ?" for k in row.keys()])
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"
        params = list(row.values()) + [id]
        self.db_manager.execute_update(query, tuple(params), self.db_path)
        return self.get_by_id(id)

    def get_by_channel_message(self, channel_id: str, message_id: Union[int, str]) -> Optional[News]:
        """按 channel_id + message_id 获取唯一新闻。"""
        if self.source != NewsSource.CRYPTO:
            return None
        try:
            normalized_message_id = int(message_id)
        except (TypeError, ValueError):
            normalized_message_id = message_id
        return self.find_one(
            "channel_id = ? AND message_id = ?",
            (channel_id, normalized_message_id),
        )

    def get_by_date_range(self, start_date: str, end_date: str,
                         limit: Optional[int] = None) -> List[News]:
        """
        获取指定日期范围的新闻

        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制数量

        Returns:
            新闻列表
        """
        date_column = 'date' if self.source == NewsSource.CRYPTO else 'publish_date'
        where_clause = f"{date_column} >= ? AND {date_column} <= ?"
        order_by = f"{date_column} DESC"

        return self.find(where_clause, (start_date, end_date), order_by, limit)

    def get_recent(self, limit: int = 20) -> List[News]:
        """
        获取最新的新闻

        Args:
            limit: 限制数量

        Returns:
            新闻列表
        """
        date_column = 'date' if self.source == NewsSource.CRYPTO else 'publish_date'
        query = f"SELECT * FROM {self.table_name} ORDER BY {date_column} DESC LIMIT ?"
        results = self.db_manager.execute_query(query, (limit,), self.db_path)
        return [self._row_to_model(row) for row in results]

    def search_by_keyword(self, keyword: str, limit: int = 100) -> List[News]:
        """
        按关键词搜索新闻

        Args:
            keyword: 关键词
            limit: 限制数量

        Returns:
            新闻列表
        """
        text_column = 'text' if self.source == NewsSource.CRYPTO else 'content'
        where_clause = f"({text_column} LIKE ? OR keywords LIKE ?)"
        order_by = 'date DESC' if self.source == NewsSource.CRYPTO else 'publish_date DESC'

        keyword_pattern = f'%{keyword}%'
        return self.find(where_clause, (keyword_pattern, keyword_pattern), order_by, limit)

    def get_by_keyword(self, keyword: str, limit: Optional[int] = None) -> List[News]:
        """兼容旧服务层调用。"""
        return self.search_by_keyword(keyword, limit=limit or 100)

    def get_by_channel(self, channel_id: str, limit: Optional[int] = None) -> List[News]:
        """
        获取指定频道的新闻（仅适用于Crypto）

        Args:
            channel_id: 频道ID
            limit: 限制数量

        Returns:
            新闻列表
        """
        if self.source != NewsSource.CRYPTO:
            return []

        where_clause = "channel_id = ?"
        order_by = "date DESC"
        return self.find(where_clause, (channel_id,), order_by, limit)

    def get_by_currency(self, currency: str, limit: Optional[int] = None) -> List[News]:
        """
        获取指定币种的新闻（仅适用于Crypto）

        Args:
            currency: 币种
            limit: 限制数量

        Returns:
            新闻列表
        """
        if self.source != NewsSource.CRYPTO:
            return []

        where_clause = "currency LIKE ?"
        order_by = "date DESC"
        return self.find(where_clause, (f'%{currency}%',), order_by, limit)

    def get_by_industry(self, industry: str, limit: Optional[int] = None) -> List[News]:
        """
        获取指定行业的新闻（仅适用于HKStocks）

        Args:
            industry: 行业
            limit: 限制数量

        Returns:
            新闻列表
        """
        if self.source != NewsSource.HKSTOCKS:
            return []

        where_clause = "industry LIKE ?"
        order_by = "publish_date DESC"
        return self.find(where_clause, (f'%{industry}%',), order_by, limit)

    def update_keywords(self, news_id: int, keywords: str) -> bool:
        """
        更新新闻的关键词

        Args:
            news_id: 新闻ID
            keywords: 关键词字符串（逗号分隔）

        Returns:
            是否更新成功
        """
        query = f"UPDATE {self.table_name} SET keywords = ? WHERE id = ?"
        affected = self.db_manager.execute_update(query, (keywords, news_id), self.db_path)
        return affected > 0

    def update_abstract(self, news_id: int, abstract: str) -> bool:
        """
        更新新闻的摘要

        Args:
            news_id: 新闻ID
            abstract: 摘要内容

        Returns:
            是否更新成功
        """
        query = f"UPDATE {self.table_name} SET abstract = ? WHERE id = ?"
        affected = self.db_manager.execute_update(query, (abstract, news_id), self.db_path)
        if self.source == NewsSource.CRYPTO and 'summary' in self.columns:
            self.db_manager.execute_update(
                f"UPDATE {self.table_name} SET summary = ? WHERE id = ?",
                (abstract, news_id),
                self.db_path,
            )
        return affected > 0

    def batch_create(self, news_list: List[News]) -> int:
        """
        批量创建新闻

        Args:
            news_list: 新闻列表

        Returns:
            成功创建的数量
        """
        if not news_list:
            return 0

        rows = [self._model_to_row(news) for news in news_list]
        first_row = rows[0]
        first_row.pop('id', None)

        columns = ', '.join(first_row.keys())
        placeholders = ', '.join(['?' for _ in first_row])
        query = f"INSERT OR IGNORE INTO {self.table_name} ({columns}) VALUES ({placeholders})"

        params_list = [tuple(row.values()) for row in rows]
        affected = self.db_manager.execute_many(query, params_list, self.db_path)
        return affected

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        获取新闻统计信息

        Args:
            days: 统计天数

        Returns:
            统计信息字典
        """
        date_column = 'date' if self.source == NewsSource.CRYPTO else 'publish_date'
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        # 总数
        total_query = f"SELECT COUNT(*) as count FROM {self.table_name}"
        total_results = self.db_manager.execute_query(total_query, db_path=self.db_path)
        total_count = total_results[0]['count'] if total_results else 0

        # 最近N天数量
        recent_query = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE {date_column} >= ?"
        recent_results = self.db_manager.execute_query(recent_query, (start_date,), self.db_path)
        recent_count = recent_results[0]['count'] if recent_results else 0

        # 每日统计
        daily_query = f"""
        SELECT DATE({date_column}) as date, COUNT(*) as count
        FROM {self.table_name}
        WHERE {date_column} >= ?
        GROUP BY DATE({date_column})
        ORDER BY date DESC
        """
        daily_results = self.db_manager.execute_query(daily_query, (start_date,), self.db_path)

        return {
            'total_count': total_count,
            'recent_count': recent_count,
            'recent_days': days,
            'daily_stats': daily_results,
        }


# 便捷函数
def get_crypto_news_repository() -> NewsRepository:
    """获取加密货币新闻仓储"""
    return NewsRepository(source=NewsSource.CRYPTO)


def get_hkstocks_news_repository() -> NewsRepository:
    """获取港股新闻仓储"""
    return NewsRepository(source=NewsSource.HKSTOCKS)
