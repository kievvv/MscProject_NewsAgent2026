"""
爬虫基类
定义爬虫的通用接口
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from src.services import NewsService
from src.core.models import NewsSource

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """
    爬虫基类

    定义所有爬虫的通用接口和行为
    """

    def __init__(self, source: NewsSource, news_service: Optional[NewsService] = None):
        """
        初始化爬虫

        Args:
            source: 新闻来源
            news_service: 新闻服务（用于保存新闻）
        """
        self.source = source
        self.news_service = news_service
        self.stats = {
            'fetched': 0,
            'saved': 0,
            'updated': 0,
            'duplicated': 0,
            'failed': 0
        }

    @abstractmethod
    async def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        """
        抓取新闻

        Args:
            **kwargs: 抓取参数

        Returns:
            新闻数据列表
        """
        pass

    @abstractmethod
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析原始数据

        Args:
            raw_data: 原始数据

        Returns:
            解析后的新闻数据
        """
        pass

    async def process(self, news_data: Dict[str, Any]) -> bool:
        """
        处理新闻（保存到数据库）

        Args:
            news_data: 新闻数据

        Returns:
            是否成功
        """
        try:
            if not self.news_service:
                logger.warning("新闻服务未初始化，跳过保存")
                return False

            # 检查是否重复
            existing = self.news_service.get_news(news_data.get('id', ''))
            if existing:
                self.stats['duplicated'] += 1
                return False

            # 创建新闻
            self.news_service.create_news(**news_data)
            self.stats['saved'] += 1
            return True

        except Exception as e:
            logger.error(f"处理新闻失败: {e}")
            self.stats['failed'] += 1
            return False

    async def run(self, **kwargs) -> Dict[str, int]:
        """
        运行爬虫（完整流程）

        Args:
            **kwargs: 运行参数

        Returns:
            统计信息
        """
        try:
            logger.info(f"开始爬取 {self.source} 新闻...")

            # 1. 抓取
            raw_data_list = await self.fetch(**kwargs)
            self.stats['fetched'] = len(raw_data_list)
            logger.info(f"抓取到 {self.stats['fetched']} 条原始数据")

            # 2. 解析和处理
            for raw_data in raw_data_list:
                try:
                    news_data = await self.parse(raw_data)
                    await self.process(news_data)
                except Exception as e:
                    logger.error(f"处理单条数据失败: {e}")
                    self.stats['failed'] += 1

            logger.info(f"爬取完成: {self.stats}")
            return self.stats

        except Exception as e:
            logger.error(f"爬虫运行失败: {e}")
            return self.stats

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'fetched': 0,
            'saved': 0,
            'updated': 0,
            'duplicated': 0,
            'failed': 0
        }
