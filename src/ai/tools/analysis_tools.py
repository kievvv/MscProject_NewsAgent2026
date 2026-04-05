"""
Analysis Tools
工具包装：关键词提取、趋势分析、相似度分析
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .base import BaseTool, ToolResult
from src.services import get_trend_service, get_search_service
from src.analyzers import get_keyword_extractor
from src.core.models import NewsSource

logger = logging.getLogger(__name__)


class KeywordExtractionTool(BaseTool):
    """关键词提取工具"""

    def __init__(self, source: NewsSource = NewsSource.CRYPTO):
        super().__init__(
            name="keyword_extraction",
            description="从文本中提取关键词。参数: text(文本内容), top_n(返回top N个关键词,默认5)"
        )
        self.keyword_extractor = get_keyword_extractor()

    def execute(self, text: str, top_n: int = 5, **kwargs) -> ToolResult:
        """
        从文本提取关键词

        Args:
            text: 输入文本
            top_n: 返回top N个关键词

        Returns:
            ToolResult包含关键词列表
        """
        try:
            if not text or not text.strip():
                raise ValueError("text is required")

            # 提取关键词
            keywords = self.keyword_extractor.extract_keywords(text, top_n=top_n)

            # 格式化结果
            keyword_list = []
            for item in keywords:
                if isinstance(item, dict):
                    keyword_list.append({
                        'keyword': item.get('keyword', ''),
                        'score': float(item.get('score', 0.0))
                    })
                else:
                    kw, score = item
                    keyword_list.append({'keyword': kw, 'score': float(score)})

            return ToolResult(
                success=True,
                data=keyword_list,
                metadata={'top_n': top_n, 'text_length': len(text)}
            )

        except Exception as e:
            logger.error(f"KeywordExtractionTool error: {e}")
            return ToolResult(
                success=False,
                data=[],
                error=str(e)
            )


class TrendAnalysisTool(BaseTool):
    """趋势分析工具"""

    def __init__(self, source: NewsSource = NewsSource.CRYPTO):
        super().__init__(
            name="trend_analysis",
            description="分析关键词趋势。参数: keyword(关键词), days(分析最近N天,默认30)"
        )
        self.trend_service = get_trend_service(source=source)

    def execute(self, keyword: str, days: int = 30, **kwargs) -> ToolResult:
        """
        分析关键词趋势

        Args:
            keyword: 关键词
            days: 分析时间范围(天)

        Returns:
            ToolResult包含趋势数据
        """
        try:
            # 计算日期范围
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            # 执行趋势分析
            trend = self.trend_service.analyze_keyword_trend(
                keyword=keyword,
                start_date=start_date,
                end_date=end_date
            )

            # 格式化结果
            if isinstance(trend, dict):
                result = {
                    'keyword': trend.get('keyword'),
                    'total_count': trend.get('total_count', 0),
                    'active_days': trend.get('active_days', 0),
                    'avg_daily_count': round(float(trend.get('avg_daily_count', 0.0)), 2),
                    'peak_date': trend.get('peak_date'),
                    'peak_count': trend.get('peak_count', 0),
                    'daily_trend': (trend.get('daily_trend') or [])[:10],
                }
            else:
                result = {
                    'keyword': trend.keyword,
                    'total_count': trend.total_count,
                    'active_days': trend.active_days,
                    'avg_daily_count': round(trend.avg_daily_count, 2),
                    'peak_date': trend.peak_date,
                    'peak_count': trend.peak_count,
                    'daily_trend': trend.daily_trend[:10],  # 只返回最近10天
                }

            return ToolResult(
                success=True,
                data=result,
                metadata={'date_range': f"{start_date} to {end_date}"}
            )

        except Exception as e:
            logger.error(f"TrendAnalysisTool error: {e}")
            return ToolResult(
                success=False,
                data={},
                error=str(e)
            )


class SimilarityTool(BaseTool):
    """相似度搜索工具"""

    def __init__(self, source: NewsSource = NewsSource.CRYPTO):
        super().__init__(
            name="similarity_search",
            description="查找相似新闻。参数: text(参考文本), limit(返回条数,默认5), threshold(相似度阈值,默认0.7)"
        )
        self.search_service = get_search_service(source=source)

    def execute(
        self,
        text: str,
        limit: int = 5,
        threshold: float = 0.7,
        **kwargs
    ) -> ToolResult:
        """
        查找相似新闻

        Args:
            text: 参考文本
            limit: 返回条数
            threshold: 相似度阈值

        Returns:
            ToolResult包含相似新闻列表
        """
        try:
            if not text or not text.strip():
                raise ValueError("text is required")

            candidates = self.search_service.search_by_similarity(
                keyword=text.strip(),
                top_n=limit,
                min_similarity=threshold
            )

            # 格式化结果
            similar_news = [
                {
                    'keyword': result['keyword'],
                    'similarity_score': round(result['similarity'], 3),
                    'count': result['count'],
                    'news': [
                        {
                            'id': news.id,
                            'title': news.title or news.text[:80],
                            'text': news.text[:200],
                            'date': news.date,
                        }
                        for news in result['news'][:3]
                    ],
                }
                for result in candidates
            ]

            return ToolResult(
                success=True,
                data=similar_news,
                metadata={
                    'total': len(similar_news),
                    'threshold': threshold
                }
            )

        except Exception as e:
            logger.error(f"SimilarityTool error: {e}")
            return ToolResult(
                success=False,
                data=[],
                error=str(e)
            )
