"""
新闻服务
提供新闻管理的高级业务逻辑
"""
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from src.data.repositories.news import NewsRepository
from src.data.repositories.keyword import KeywordRepository
from src.analyzers import get_keyword_extractor, get_summarizer
from src.core.models import News, NewsSource
from src.core.exceptions import ServiceException

logger = logging.getLogger(__name__)


class NewsService:
    """
    新闻服务

    功能：
    1. 新闻创建（自动提取关键词）
    2. 新闻更新
    3. 新闻查询（封装Repository）
    4. 摘要生成
    5. 批量处理
    """

    def __init__(self,
                 source: NewsSource = NewsSource.CRYPTO,
                 auto_extract_keywords: bool = True,
                 auto_generate_summary: bool = False):
        """
        初始化新闻服务

        Args:
            source: 新闻来源
            auto_extract_keywords: 是否自动提取关键词
            auto_generate_summary: 是否自动生成摘要
        """
        self.source = source
        self.auto_extract_keywords = auto_extract_keywords
        self.auto_generate_summary = auto_generate_summary

        # 初始化仓储
        self.news_repo = NewsRepository(source=source)
        # KeywordRepository使用与NewsRepository相同的db_path
        self.keyword_repo = KeywordRepository(db_path=self.news_repo.db_path)

        # 延迟加载分析器
        self._keyword_extractor = None
        self._summarizer = None

    @property
    def keyword_extractor(self):
        """延迟加载关键词提取器"""
        if self._keyword_extractor is None:
            self._keyword_extractor = get_keyword_extractor()
        return self._keyword_extractor

    @property
    def summarizer(self):
        """延迟加载摘要生成器"""
        if self._summarizer is None:
            self._summarizer = get_summarizer()
        return self._summarizer

    def create_news(self,
                   title: str,
                   content: Optional[str] = None,
                   date: Optional[str] = None,
                   channel_id: Optional[str] = None,
                   message_id: Optional[str] = None,
                   **kwargs) -> News:
        """
        创建新闻（自动提取关键词和生成摘要）

        Args:
            title: 标题
            content: 内容
            date: 日期
            channel_id: 频道ID（Crypto）
            message_id: 消息ID（Crypto）
            **kwargs: 其他字段

        Returns:
            创建的新闻对象
        """
        try:
            content_text = content if content is not None else kwargs.pop('text', '')
            if not content_text:
                raise ServiceException("News content cannot be empty")

            if self.source == NewsSource.CRYPTO and channel_id and message_id is not None:
                existing = self.news_repo.get_by_channel_message(channel_id, message_id)
                if existing:
                    logger.info(
                        "News already exists for channel=%s message_id=%s, returning existing record",
                        channel_id,
                        message_id,
                    )
                    return existing

            # 准备数据
            news_data = {
                'title': title,
                'content': content_text,
                'date': date or datetime.now().isoformat(),
                **kwargs
            }

            # Crypto特有字段
            if self.source == NewsSource.CRYPTO:
                if channel_id:
                    news_data['channel_id'] = channel_id
                if message_id:
                    news_data['message_id'] = message_id

            # 自动提取关键词
            if self.auto_extract_keywords:
                full_text = f"{title} {content_text}"
                extraction_result = self.keyword_extractor.extract_all(
                    full_text,
                    source=self.source
                )

                # 提取关键词字符串
                keywords = [kw for kw, _ in extraction_result['keywords']]
                news_data['keywords'] = ', '.join(keywords)

                # 提取币种/行业
                if self.source == NewsSource.CRYPTO:
                    currency = extraction_result.get('currency', [])
                    if currency:
                        news_data['currency'] = ', '.join(currency)
                else:  # HKSTOCKS
                    entities = extraction_result.get('entities', {})
                    orgs = entities.get('ORG', [])
                    if orgs:
                        news_data['industry'] = ', '.join(orgs[:3])  # 取前3个组织名

            # 自动生成摘要
            if self.auto_generate_summary and not news_data.get('summary'):
                try:
                    summary = self.summarizer.generate(content_text, max_length=150)
                    if summary:
                        news_data['summary'] = summary
                except Exception as e:
                    logger.warning(f"摘要生成失败: {e}")

            # 创建新闻
            news = self.news_repo.create(**news_data)

            # 保存关键词关联
            if news.keywords:
                self._save_keyword_associations(news)

            logger.info(f"新闻创建成功: {news.id}")
            return news

        except Exception as e:
            logger.error(f"新闻创建失败: {e}")
            raise ServiceException(f"Failed to create news: {e}")

    def update_news(self, news_id: str, **update_data) -> Optional[News]:
        """
        更新新闻

        Args:
            news_id: 新闻ID
            **update_data: 更新数据

        Returns:
            更新后的新闻对象
        """
        try:
            # 获取原新闻
            news = self.news_repo.get_by_id(news_id)
            if not news:
                logger.warning(f"新闻不存在: {news_id}")
                return None

            # 如果更新了内容，重新提取关键词
            if 'content' in update_data or 'title' in update_data:
                if self.auto_extract_keywords:
                    new_title = update_data.get('title', news.title)
                    new_content = update_data.get('content', news.content)
                    full_text = f"{new_title} {new_content}"

                    extraction_result = self.keyword_extractor.extract_all(
                        full_text,
                        source=self.source
                    )

                    keywords = [kw for kw, _ in extraction_result['keywords']]
                    update_data['keywords'] = ', '.join(keywords)

                    # 更新币种/行业
                    if self.source == NewsSource.CRYPTO:
                        currency = extraction_result.get('currency', [])
                        if currency:
                            update_data['currency'] = ', '.join(currency)

            # 更新新闻
            updated_news = self.news_repo.update(news_id, **update_data)

            # 更新关键词关联
            if updated_news and 'keywords' in update_data:
                self._save_keyword_associations(updated_news)

            logger.info(f"新闻更新成功: {news_id}")
            return updated_news

        except Exception as e:
            logger.error(f"新闻更新失败: {e}")
            raise ServiceException(f"Failed to update news: {e}")

    def delete_news(self, news_id: str) -> bool:
        """
        删除新闻

        Args:
            news_id: 新闻ID

        Returns:
            是否删除成功
        """
        try:
            success = self.news_repo.delete(news_id)
            if success:
                logger.info(f"新闻删除成功: {news_id}")
            return success
        except Exception as e:
            logger.error(f"新闻删除失败: {e}")
            raise ServiceException(f"Failed to delete news: {e}")

    def get_news(self, news_id: str) -> Optional[News]:
        """获取单条新闻"""
        return self.news_repo.get_by_id(news_id)

    def get_news_by_id(self, news_id: str) -> Optional[News]:
        """兼容 AI tools 中的 get_news_by_id 调用。"""
        return self.get_news(news_id)

    def get_all_news(self, limit: Optional[int] = None) -> List[News]:
        """获取所有新闻"""
        return self.news_repo.get_all(limit=limit)

    def get_news_by_date_range(self, start_date: str, end_date: str) -> List[News]:
        """按日期范围获取新闻"""
        return self.news_repo.get_by_date_range(start_date, end_date)

    def get_news_by_channel(self, channel_id: str, limit: Optional[int] = None) -> List[News]:
        """按频道获取新闻（仅Crypto）"""
        if self.source != NewsSource.CRYPTO:
            raise ServiceException("Channel filtering is only available for Crypto news")
        return self.news_repo.get_by_channel(channel_id, limit=limit)

    def get_news_by_source_message(self, channel_id: str, message_id: Union[str, int]) -> Optional[News]:
        """按 Telegram 唯一消息标识获取新闻。"""
        if self.source != NewsSource.CRYPTO:
            return None
        return self.news_repo.get_by_channel_message(channel_id, message_id)

    def get_news_by_keyword(self, keyword: str, limit: Optional[int] = None) -> List[News]:
        """按关键词获取新闻"""
        return self.news_repo.get_by_keyword(keyword, limit=limit)

    def generate_summary(self, news_id: str, force: bool = False) -> Optional[str]:
        """
        为新闻生成摘要

        Args:
            news_id: 新闻ID
            force: 是否强制重新生成（即使已有摘要）

        Returns:
            生成的摘要
        """
        try:
            news = self.news_repo.get_by_id(news_id)
            if not news:
                logger.warning(f"新闻不存在: {news_id}")
                return None

            # 如果已有摘要且不强制重新生成
            if news.summary and not force:
                return news.summary

            # 生成摘要
            summary = self.summarizer.generate(news.content, max_length=150)

            # 保存摘要
            if summary:
                self.news_repo.update(news_id, summary=summary)
                logger.info(f"摘要生成成功: {news_id}")

            return summary

        except Exception as e:
            logger.error(f"摘要生成失败: {e}")
            return None

    def batch_generate_summaries(self,
                                 news_ids: Optional[List[str]] = None,
                                 force: bool = False,
                                 limit: Optional[int] = None) -> Dict[str, str]:
        """
        批量生成摘要

        Args:
            news_ids: 新闻ID列表（None则处理所有）
            force: 是否强制重新生成
            limit: 限制处理数量

        Returns:
            {news_id: summary} 字典
        """
        try:
            # 获取新闻列表
            if news_ids:
                news_list = [self.news_repo.get_by_id(nid) for nid in news_ids]
                news_list = [n for n in news_list if n is not None]
            else:
                news_list = self.news_repo.get_all(limit=limit)

            # 过滤需要生成摘要的新闻
            if not force:
                news_list = [n for n in news_list if not n.summary]

            logger.info(f"开始批量生成摘要，共 {len(news_list)} 条新闻")

            # 批量生成
            results = {}
            for news in news_list:
                try:
                    summary = self.summarizer.generate(news.content, max_length=150)
                    if summary:
                        self.news_repo.update(news.id, summary=summary)
                        results[news.id] = summary
                except Exception as e:
                    logger.warning(f"新闻 {news.id} 摘要生成失败: {e}")
                    continue

            logger.info(f"批量生成完成，成功 {len(results)} 条")
            return results

        except Exception as e:
            logger.error(f"批量生成摘要失败: {e}")
            return {}

    def batch_extract_keywords(self,
                              news_ids: Optional[List[str]] = None,
                              force: bool = False,
                              limit: Optional[int] = None) -> Dict[str, List[str]]:
        """
        批量提取关键词

        Args:
            news_ids: 新闻ID列表（None则处理所有）
            force: 是否强制重新提取
            limit: 限制处理数量

        Returns:
            {news_id: [keywords]} 字典
        """
        try:
            # 获取新闻列表
            if news_ids:
                news_list = [self.news_repo.get_by_id(nid) for nid in news_ids]
                news_list = [n for n in news_list if n is not None]
            else:
                news_list = self.news_repo.get_all(limit=limit)

            # 过滤需要提取关键词的新闻
            if not force:
                news_list = [n for n in news_list if not n.keywords]

            logger.info(f"开始批量提取关键词，共 {len(news_list)} 条新闻")

            # 批量提取
            results = {}
            for news in news_list:
                try:
                    full_text = f"{news.title} {news.content}"
                    extraction_result = self.keyword_extractor.extract_all(
                        full_text,
                        source=self.source
                    )

                    keywords = [kw for kw, _ in extraction_result['keywords']]
                    keywords_str = ', '.join(keywords)

                    # 更新新闻
                    update_data = {'keywords': keywords_str}

                    # 更新币种/行业
                    if self.source == NewsSource.CRYPTO:
                        currency = extraction_result.get('currency', [])
                        if currency:
                            update_data['currency'] = ', '.join(currency)

                    self.news_repo.update(news.id, **update_data)

                    # 保存关键词关联
                    updated_news = self.news_repo.get_by_id(news.id)
                    if updated_news:
                        self._save_keyword_associations(updated_news)

                    results[news.id] = keywords

                except Exception as e:
                    logger.warning(f"新闻 {news.id} 关键词提取失败: {e}")
                    continue

            logger.info(f"批量提取完成，成功 {len(results)} 条")
            return results

        except Exception as e:
            logger.error(f"批量提取关键词失败: {e}")
            return {}

    def _save_keyword_associations(self, news: News) -> None:
        """
        保存关键词关联

        Args:
            news: 新闻对象
        """
        try:
            if not news.keywords:
                return

            keywords = news.keyword_list
            for keyword in keywords:
                self.keyword_repo.add_or_update_keyword(
                    keyword=keyword.strip(),
                    news_id=news.id,
                    news_date=news.date
                )
        except Exception as e:
            logger.warning(f"保存关键词关联失败: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取新闻统计信息

        Returns:
            统计信息字典
        """
        try:
            all_news = self.news_repo.get_all()

            # 基础统计
            total_count = len(all_news)
            with_keywords = len([n for n in all_news if n.keywords])
            with_abstract = len([n for n in all_news if getattr(n, 'abstract', None)])

            # 日期范围
            dates = [n.date for n in all_news if n.date]
            date_range = (min(dates), max(dates)) if dates else ('', '')

            # Crypto特有统计
            stats = {
                'total_count': total_count,
                'with_keywords': with_keywords,
                'with_summary': with_abstract,
                'keyword_rate': with_keywords / total_count if total_count > 0 else 0,
                'summary_rate': with_abstract / total_count if total_count > 0 else 0,
                'date_range': date_range,
            }

            if self.source == NewsSource.CRYPTO:
                channels = set(n.channel_id for n in all_news if n.channel_id)
                stats['channel_count'] = len(channels)

            return stats

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            import traceback
            traceback.print_exc()
            return {}


# 便捷函数
def get_news_service(source: NewsSource = NewsSource.CRYPTO,
                    auto_extract_keywords: bool = True,
                    auto_generate_summary: bool = False) -> NewsService:
    """
    获取新闻服务实例

    Args:
        source: 新闻来源
        auto_extract_keywords: 是否自动提取关键词
        auto_generate_summary: 是否自动生成摘要

    Returns:
        NewsService实例
    """
    return NewsService(
        source=source,
        auto_extract_keywords=auto_extract_keywords,
        auto_generate_summary=auto_generate_summary
    )
