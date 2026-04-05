"""
News Tools
工具包装：新闻搜索和摘要
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .base import BaseTool, ToolResult
from src.services import get_search_service, get_news_service
from src.core.models import NewsSource

logger = logging.getLogger(__name__)


class NewsSearchTool(BaseTool):
    """新闻搜索工具"""

    def __init__(self, source: NewsSource = NewsSource.CRYPTO):
        super().__init__(
            name="news_search",
            description="搜索相关新闻。参数: keyword(关键词), days(最近几天,默认7), limit(最多返回条数,默认10)"
        )
        self.search_service = get_search_service(source=source)
        self.news_service = get_news_service(source=source, auto_extract_keywords=False)

    def execute(
        self,
        keyword: str,
        days: int = 7,
        limit: int = 10,
        **kwargs
    ) -> ToolResult:
        """
        执行新闻搜索

        Args:
            keyword: 搜索关键词
            days: 搜索最近N天的新闻
            limit: 最多返回条数

        Returns:
            ToolResult包含新闻列表
        """
        try:
            if not keyword or not keyword.strip():
                raise ValueError("keyword is required")

            # 执行搜索（SearchService已自动按时间排序，返回最新的）
            results = self.search_service.search_by_keyword(
                keyword=keyword.strip(),
                exact=False,
                limit=limit
            )

            # 格式化结果
            news_list = [
                {
                    'id': news.id,
                    'title': news.title or news.text[:80],
                    'text': news.text[:200] + '...' if len(news.text) > 200 else news.text,
                    'date': news.date,
                    'url': news.url,
                    'keywords': news.keyword_list,
                }
                for news in results
            ]

            return ToolResult(
                success=True,
                data=news_list,
                metadata={
                    'total': len(news_list),
                    'keyword': keyword,
                }
            )

        except Exception as e:
            logger.error(f"NewsSearchTool error: {e}")
            return ToolResult(
                success=False,
                data=[],
                error=str(e)
            )


class NewsSummaryTool(BaseTool):
    """新闻摘要工具"""

    def __init__(self, source: NewsSource = NewsSource.CRYPTO):
        super().__init__(
            name="news_summary",
            description="获取指定新闻的摘要。参数: news_id(新闻ID)"
        )
        self.news_service = get_news_service(source=source, auto_extract_keywords=False)

    def execute(self, news_id: int, **kwargs) -> ToolResult:
        """
        获取新闻摘要

        Args:
            news_id: 新闻ID

        Returns:
            ToolResult包含摘要文本
        """
        try:
            news = self.news_service.get_news_by_id(news_id)
            if not news:
                return ToolResult(
                    success=False,
                    data=None,
                    error=f"News {news_id} not found"
                )

            summary = {
                'id': news.id,
                'title': news.title,
                'abstract': news.abstract,
                'keywords': news.keyword_list,
                'date': news.date,
            }

            return ToolResult(
                success=True,
                data=summary,
                metadata={'news_id': news_id}
            )

        except Exception as e:
            logger.error(f"NewsSummaryTool error: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e)
            )
