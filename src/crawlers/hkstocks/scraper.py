"""
港股新闻爬虫
从AAStocks网站爬取港股新闻
"""
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

from src.crawlers.base import BaseCrawler
from src.services import NewsService
from src.core.models import NewsSource

logger = logging.getLogger(__name__)


class HKStocksScraper(BaseCrawler):
    """
    港股新闻爬虫

    功能：
    1. 从AAStocks爬取港股新闻列表
    2. 解析新闻详情
    3. 生产者-消费者模式处理
    """

    BASE_URL = "https://www.aastocks.com"
    NEWS_LIST_URL = f"{BASE_URL}/tc/stocks/news/aafn-content/NOW.{{}}/0"

    def __init__(self, news_service: Optional[NewsService] = None):
        """
        初始化爬虫

        Args:
            news_service: 新闻服务
        """
        if requests is None or BeautifulSoup is None:
            raise ImportError("请安装 requests 和 beautifulsoup4: pip install requests beautifulsoup4")

        super().__init__(NewsSource.HKSTOCKS, news_service)

        # 请求配置
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.timeout = 10

    async def fetch(self, days: int = 1, max_count: int = 1000) -> List[Dict[str, Any]]:
        """
        抓取新闻列表

        Args:
            days: 抓取最近几天的新闻
            max_count: 最多抓取数量

        Returns:
            原始新闻数据列表
        """
        news_list = []
        page = 1

        try:
            while len(news_list) < max_count:
                logger.info(f"抓取第 {page} 页...")

                # 构建URL
                url = self.NEWS_LIST_URL.format(page)

                # 请求页面
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()

                # 解析HTML
                soup = BeautifulSoup(response.content, 'html.parser')

                # 查找新闻列表
                news_items = soup.find_all('div', class_='newshead4')

                if not news_items:
                    logger.info("没有更多新闻，停止抓取")
                    break

                # 解析每条新闻
                for item in news_items:
                    try:
                        # 提取链接和标题
                        link_tag = item.find('a')
                        if not link_tag:
                            continue

                        title = link_tag.get_text(strip=True)
                        href = link_tag.get('href', '')

                        # 提取日期
                        date_tag = item.find('span', class_='newstime')
                        date_str = date_tag.get_text(strip=True) if date_tag else ''

                        # 检查日期范围
                        if days > 0:
                            news_date = self._parse_date(date_str)
                            if news_date and (datetime.now() - news_date).days > days:
                                logger.info(f"超出日期范围，停止抓取")
                                return news_list

                        # 构建完整URL
                        full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"

                        news_list.append({
                            'title': title,
                            'url': full_url,
                            'date': date_str,
                            'page': page
                        })

                        if len(news_list) >= max_count:
                            break

                    except Exception as e:
                        logger.error(f"解析新闻项失败: {e}")
                        continue

                page += 1

        except Exception as e:
            logger.error(f"抓取新闻列表失败: {e}")

        logger.info(f"抓取完成，共 {len(news_list)} 条新闻")
        return news_list

    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析新闻详情

        Args:
            raw_data: 原始新闻数据

        Returns:
            解析后的新闻数据
        """
        try:
            # 请求详情页
            response = requests.get(raw_data['url'], headers=self.headers, timeout=self.timeout)
            response.raise_for_status()

            # 解析HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # 提取内容
            content_div = soup.find('div', class_='newstext4')
            content = content_div.get_text(strip=True) if content_div else ''

            # 提取股票代码
            stock_codes = self._extract_stock_codes(content)

            # 构建新闻数据
            news_data = {
                'title': raw_data['title'],
                'content': content,
                'date': self._parse_date(raw_data['date']).isoformat() if raw_data['date'] else datetime.now().isoformat(),
                'stock_code': ', '.join(stock_codes) if stock_codes else None,
            }

            return news_data

        except Exception as e:
            logger.error(f"解析新闻详情失败: {e}")
            # 返回基本信息
            return {
                'title': raw_data['title'],
                'content': raw_data['title'],
                'date': datetime.now().isoformat(),
            }

    def fetch_and_save_with_pipeline(
        self,
        days: int = 1,
        max_count: int = 1000,
        num_workers: int = 3,
        extract_keywords: bool = True
    ) -> Dict[str, int]:
        """
        使用生产者-消费者模式抓取和保存

        Args:
            days: 抓取最近几天的新闻
            max_count: 最多抓取数量
            num_workers: 工作线程数
            extract_keywords: 是否提取关键词

        Returns:
            统计信息
        """
        import asyncio

        # 重置统计
        self.reset_stats()

        # 1. 生产者：抓取新闻列表
        news_list = asyncio.run(self.fetch(days=days, max_count=max_count))
        self.stats['fetched'] = len(news_list)

        if not news_list:
            logger.warning("没有抓取到新闻")
            return self.stats

        # 2. 消费者：并发处理新闻
        logger.info(f"开始处理新闻，线程数: {num_workers}")

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # 提交任务
            futures = {
                executor.submit(self._process_single_news, news): news
                for news in news_list
            }

            # 等待完成
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"处理任务失败: {e}")

        logger.info(f"处理完成: {self.stats}")
        return self.stats

    def _process_single_news(self, raw_data: Dict[str, Any]):
        """
        处理单条新闻（线程安全）

        Args:
            raw_data: 原始新闻数据
        """
        import asyncio

        try:
            # 解析
            news_data = asyncio.run(self.parse(raw_data))

            # 保存
            asyncio.run(self.process(news_data))

        except Exception as e:
            logger.error(f"处理单条新闻失败: {e}")
            self.stats['failed'] += 1

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        解析日期字符串

        Args:
            date_str: 日期字符串（如 "2024-12-05 12:30"）

        Returns:
            datetime对象
        """
        try:
            # 尝试多种格式
            formats = [
                '%Y-%m-%d %H:%M',
                '%Y/%m/%d %H:%M',
                '%Y-%m-%d',
                '%Y/%m/%d',
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            return None

        except Exception:
            return None

    def _extract_stock_codes(self, text: str) -> List[str]:
        """
        从文本中提取港股代码

        Args:
            text: 文本内容

        Returns:
            股票代码列表
        """
        # 港股代码格式：0001-9999
        pattern = r'\b(0\d{3,4}|[1-9]\d{3,4})\b'
        matches = re.findall(pattern, text)

        # 去重并排序
        return sorted(list(set(matches)))
