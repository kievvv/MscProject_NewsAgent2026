"""
搜索服务
提供新闻搜索和过滤功能
"""
import logging
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timedelta

from src.data.repositories.news import NewsRepository
from src.analyzers import get_similarity_analyzer
from src.core.models import News, NewsSource
from src.core.exceptions import ServiceException

logger = logging.getLogger(__name__)


class SearchService:
    """
    搜索服务

    功能：
    1. 关键词搜索（精确/模糊）
    2. 相似度搜索（基于spaCy）
    3. 日期范围搜索
    4. 多条件组合搜索
    5. 高级过滤
    """

    def __init__(self, source: NewsSource = NewsSource.CRYPTO):
        """
        初始化搜索服务

        Args:
            source: 新闻来源
        """
        self.source = source
        self.news_repo = NewsRepository(source=source)

        # 延迟加载分析器
        self._similarity_analyzer = None

    @property
    def similarity_analyzer(self):
        """延迟加载相似度分析器"""
        if self._similarity_analyzer is None:
            self._similarity_analyzer = get_similarity_analyzer()
        return self._similarity_analyzer

    def search_by_keyword(self,
                         keyword: str,
                         exact: bool = False,
                         limit: Optional[int] = None) -> List[News]:
        """
        按关键词搜索

        Args:
            keyword: 关键词
            exact: 是否精确匹配
            limit: 限制返回数量

        Returns:
            新闻列表
        """
        try:
            if exact:
                # 精确匹配：直接使用Repository
                return self.news_repo.get_by_keyword(keyword, limit=limit)
            else:
                # 模糊匹配：搜索标题和内容
                all_news = self.news_repo.get_all(limit=10000)
                keyword_lower = keyword.lower()

                results = []
                for news in all_news:
                    # 在标题、内容、关键词中搜索
                    title_match = keyword_lower in (news.title or "").lower()
                    text_match = keyword_lower in (news.text or "").lower()
                    keyword_match = keyword_lower in (news.keywords or "").lower()

                    if title_match or text_match or keyword_match:
                        results.append(news)
                        if limit and len(results) >= limit:
                            break

                return results

        except Exception as e:
            logger.error(f"关键词搜索失败: {e}")
            raise ServiceException(f"Failed to search by keyword: {e}")

    def search_by_similarity(self,
                           keyword: str,
                           top_n: int = 10,
                           min_similarity: float = 0.5) -> List[Dict[str, Any]]:
        """
        相似度搜索（查找相似关键词的新闻）

        Args:
            keyword: 关键词
            top_n: 返回前N个相似词
            min_similarity: 最小相似度阈值

        Returns:
            [{'keyword': str, 'count': int, 'similarity': float, 'news': List[News]}]
        """
        try:
            # 获取关键词统计
            stats = self.similarity_analyzer.get_keyword_statistics(
                source=self.source
            )

            # 查找相似词
            exists, similar_words = self.similarity_analyzer.find_similar_words(
                keyword,
                stats['keyword_counter'],
                top_n=top_n
            )

            # 过滤低相似度
            similar_words = [
                (word, count, sim)
                for word, count, sim in similar_words
                if sim >= min_similarity
            ]

            # 获取每个相似词的新闻
            results = []
            for word, count, similarity in similar_words:
                news_list = self.news_repo.get_by_keyword(word, limit=100)
                results.append({
                    'keyword': word,
                    'count': count,
                    'similarity': similarity,
                    'news': news_list
                })

            return results

        except Exception as e:
            logger.error(f"相似度搜索失败: {e}")
            raise ServiceException(f"Failed to search by similarity: {e}")

    def search_by_date_range(self,
                           start_date: str,
                           end_date: str,
                           limit: Optional[int] = None) -> List[News]:
        """
        按日期范围搜索

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            limit: 限制返回数量

        Returns:
            新闻列表
        """
        try:
            news_list = self.news_repo.get_by_date_range(start_date, end_date)
            if limit:
                return news_list[:limit]
            return news_list

        except Exception as e:
            logger.error(f"日期范围搜索失败: {e}")
            raise ServiceException(f"Failed to search by date range: {e}")

    def search_recent(self, days: int = 7, limit: Optional[int] = None) -> List[News]:
        """
        搜索最近N天的新闻

        Args:
            days: 天数
            limit: 限制返回数量

        Returns:
            新闻列表
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            return self.search_by_date_range(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                limit=limit
            )

        except Exception as e:
            logger.error(f"最近新闻搜索失败: {e}")
            raise ServiceException(f"Failed to search recent news: {e}")

    def search_by_channel(self,
                         channel_id: str,
                         limit: Optional[int] = None) -> List[News]:
        """
        按频道搜索（仅Crypto）

        Args:
            channel_id: 频道ID
            limit: 限制返回数量

        Returns:
            新闻列表
        """
        if self.source != NewsSource.CRYPTO:
            raise ServiceException("Channel search is only available for Crypto news")

        try:
            return self.news_repo.get_by_channel(channel_id, limit=limit)
        except Exception as e:
            logger.error(f"频道搜索失败: {e}")
            raise ServiceException(f"Failed to search by channel: {e}")

    def search_by_currency(self,
                          currency: str,
                          limit: Optional[int] = None) -> List[News]:
        """
        按币种搜索（仅Crypto）

        Args:
            currency: 币种（如 BTC, ETH）
            limit: 限制返回数量

        Returns:
            新闻列表
        """
        if self.source != NewsSource.CRYPTO:
            raise ServiceException("Currency search is only available for Crypto news")

        try:
            all_news = self.news_repo.get_all(limit=10000)
            currency_lower = currency.lower()

            results = []
            for news in all_news:
                if news.currency and currency_lower in news.currency.lower():
                    results.append(news)
                    if limit and len(results) >= limit:
                        break

            return results

        except Exception as e:
            logger.error(f"币种搜索失败: {e}")
            raise ServiceException(f"Failed to search by currency: {e}")

    def search_by_industry(self,
                          industry: str,
                          limit: Optional[int] = None) -> List[News]:
        """
        按行业搜索（仅HKStocks）

        Args:
            industry: 行业名称
            limit: 限制返回数量

        Returns:
            新闻列表
        """
        if self.source != NewsSource.HKSTOCKS:
            raise ServiceException("Industry search is only available for HKStocks news")

        try:
            all_news = self.news_repo.get_all(limit=10000)
            industry_lower = industry.lower()

            results = []
            for news in all_news:
                if news.industry and industry_lower in news.industry.lower():
                    results.append(news)
                    if limit and len(results) >= limit:
                        break

            return results

        except Exception as e:
            logger.error(f"行业搜索失败: {e}")
            raise ServiceException(f"Failed to search by industry: {e}")

    def advanced_search(self,
                       keywords: Optional[List[str]] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       channel_ids: Optional[List[str]] = None,
                       currencies: Optional[List[str]] = None,
                       industries: Optional[List[str]] = None,
                       has_summary: Optional[bool] = None,
                       limit: Optional[int] = None) -> List[News]:
        """
        高级搜索（多条件组合）

        Args:
            keywords: 关键词列表（OR关系）
            start_date: 开始日期
            end_date: 结束日期
            channel_ids: 频道ID列表（OR关系，仅Crypto）
            currencies: 币种列表（OR关系，仅Crypto）
            industries: 行业列表（OR关系，仅HKStocks）
            has_summary: 是否有摘要
            limit: 限制返回数量

        Returns:
            新闻列表
        """
        try:
            # 获取初始新闻列表
            if start_date and end_date:
                news_list = self.news_repo.get_by_date_range(start_date, end_date)
            else:
                news_list = self.news_repo.get_all(limit=10000)

            # 应用过滤器
            filtered = news_list

            # 关键词过滤（OR）
            if keywords:
                keywords_lower = [k.lower() for k in keywords]
                filtered = [
                    news for news in filtered
                    if any(
                        kw in (news.title or "").lower() or
                        kw in (news.content or "").lower() or
                        (news.keywords and kw in news.keywords.lower())
                        for kw in keywords_lower
                    )
                ]

            # 频道过滤（OR）
            if channel_ids and self.source == NewsSource.CRYPTO:
                channel_set = set(channel_ids)
                filtered = [
                    news for news in filtered
                    if news.channel_id in channel_set
                ]

            # 币种过滤（OR）
            if currencies and self.source == NewsSource.CRYPTO:
                currencies_lower = [c.lower() for c in currencies]
                filtered = [
                    news for news in filtered
                    if news.currency and any(
                        curr in news.currency.lower()
                        for curr in currencies_lower
                    )
                ]

            # 行业过滤（OR）
            if industries and self.source == NewsSource.HKSTOCKS:
                industries_lower = [i.lower() for i in industries]
                filtered = [
                    news for news in filtered
                    if news.industry and any(
                        ind in news.industry.lower()
                        for ind in industries_lower
                    )
                ]

            # 摘要过滤
            if has_summary is not None:
                filtered = [
                    news for news in filtered
                    if bool(news.summary) == has_summary
                ]

            # 限制数量
            if limit:
                filtered = filtered[:limit]

            return filtered

        except Exception as e:
            logger.error(f"高级搜索失败: {e}")
            raise ServiceException(f"Failed to perform advanced search: {e}")

    def search_and_rank(self,
                       query: str,
                       top_n: int = 20,
                       use_similarity: bool = True) -> List[Dict[str, Any]]:
        """
        搜索并按相关性排序

        Args:
            query: 查询字符串
            top_n: 返回前N条
            use_similarity: 是否使用相似度搜索

        Returns:
            [{'news': News, 'score': float, 'match_type': str}]
        """
        try:
            query_lower = query.lower()
            all_news = self.news_repo.get_all(limit=10000)

            results = []

            for news in all_news:
                score = 0.0
                match_type = 'none'

                # 标题完全匹配（高分）
                if query_lower in (news.title or "").lower():
                    score += 10.0
                    match_type = 'title'

                # 关键词匹配（中等分）
                if news.keywords and query_lower in news.keywords.lower():
                    score += 5.0
                    if match_type == 'none':
                        match_type = 'keyword'

                # 内容匹配（低分）
                if query_lower in (news.content or "").lower():
                    score += 1.0
                    if match_type == 'none':
                        match_type = 'content'

                if score > 0:
                    results.append({
                        'news': news,
                        'score': score,
                        'match_type': match_type
                    })

            # 按分数排序
            results.sort(key=lambda x: x['score'], reverse=True)

            # 如果使用相似度搜索，补充相似词的新闻
            if use_similarity and len(results) < top_n:
                try:
                    similar_results = self.search_by_similarity(
                        query,
                        top_n=5,
                        min_similarity=0.6
                    )

                    existing_ids = {r['news'].id for r in results}

                    for sim_result in similar_results:
                        for news in sim_result['news']:
                            if news.id not in existing_ids:
                                results.append({
                                    'news': news,
                                    'score': sim_result['similarity'] * 3,
                                    'match_type': 'similar'
                                })
                                existing_ids.add(news.id)

                    # 重新排序
                    results.sort(key=lambda x: x['score'], reverse=True)

                except Exception as e:
                    logger.warning(f"相似度搜索失败: {e}")

            return results[:top_n]

        except Exception as e:
            logger.error(f"搜索排序失败: {e}")
            raise ServiceException(f"Failed to search and rank: {e}")

    def get_popular_keywords(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        获取热门关键词

        Args:
            top_n: 返回前N个

        Returns:
            [{'keyword': str, 'count': int, 'news_count': int}]
        """
        try:
            stats = self.similarity_analyzer.get_keyword_statistics(source=self.source)
            keyword_counter = stats['keyword_counter']
            keyword_occurrence = stats['keyword_occurrence']

            # 构建结果
            results = []
            for keyword, total_count in keyword_counter.most_common(top_n):
                results.append({
                    'keyword': keyword,
                    'count': total_count,
                    'news_count': keyword_occurrence[keyword]
                })

            return results

        except Exception as e:
            logger.error(f"获取热门关键词失败: {e}")
            return []

    def get_popular_currencies(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        获取热门币种（仅Crypto）

        Args:
            top_n: 返回前N个

        Returns:
            [{'currency': str, 'count': int, 'news_count': int}]
        """
        if self.source != NewsSource.CRYPTO:
            raise ServiceException("Currency statistics is only available for Crypto news")

        try:
            stats = self.similarity_analyzer.get_keyword_statistics(source=self.source)
            currency_counter = stats['currency_counter']
            currency_occurrence = stats['currency_occurrence']

            # 构建结果
            results = []
            for currency, total_count in currency_counter.most_common(top_n):
                results.append({
                    'currency': currency,
                    'count': total_count,
                    'news_count': currency_occurrence[currency]
                })

            return results

        except Exception as e:
            logger.error(f"获取热门币种失败: {e}")
            return []


# 便捷函数
def get_search_service(source: NewsSource = NewsSource.CRYPTO) -> SearchService:
    """
    获取搜索服务实例

    Args:
        source: 新闻来源

    Returns:
        SearchService实例
    """
    return SearchService(source=source)
