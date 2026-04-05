"""
Telegram消息消费者
从Redis队列读取消息并保存到数据库
"""
import json
import logging
import asyncio
from typing import Optional
from datetime import datetime

try:
    import redis
except ImportError:
    redis = None

from src.crawlers.telegram.config import RedisConfig
from src.crawlers.telegram.monitor import PipelineStatusTracker
from src.services import NewsService

logger = logging.getLogger(__name__)


class TelegramConsumer:
    """
    Telegram消息消费者

    功能：
    1. 从Redis队列读取消息
    2. 解析消息内容
    3. 保存到数据库（自动提取关键词）
    """

    def __init__(self, redis_config: RedisConfig, news_service: Optional[NewsService] = None):
        """
        初始化消费者

        Args:
            redis_config: Redis配置
            news_service: 新闻服务
        """
        if redis is None:
            raise ImportError("请安装 redis: pip install redis")

        self.redis_config = redis_config
        self.news_service = news_service

        # Redis客户端
        self.redis_client: Optional[redis.Redis] = None
        self.status_tracker: Optional[PipelineStatusTracker] = None

        # 统计信息
        self.stats = {
            'processed': 0,
            'saved': 0,
            'duplicated': 0,
            'failed': 0,
            'json_errors': 0,
            'db_errors': 0,
            'nlp_errors': 0,
            'last_processed_at': None,
            'last_saved_at': None,
            'last_error_at': None,
            'last_error': None,
        }

    def start(self):
        """启动消费者"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_config.host,
                port=self.redis_config.port,
                db=self.redis_config.db,
                password=self.redis_config.password,
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis连接成功")
            self.status_tracker = PipelineStatusTracker(self.redis_client, self.redis_config.queue_name)
            self.status_tracker.mark_consumer_started()

        except Exception as e:
            logger.error(f"启动失败: {e}")
            raise

    def stop(self):
        """停止消费者"""
        if self.redis_client:
            if self.status_tracker:
                self.status_tracker.mark_consumer_stopped()
            self.redis_client.close()
            logger.info("Redis连接已关闭")

    async def run_history_mode(self, batch_size: int = 100):
        """
        运行历史模式（处理队列中的所有消息）

        Args:
            batch_size: 批量处理大小
        """
        if not self.redis_client:
            raise RuntimeError("Redis客户端未启动")

        logger.info("开始处理历史消息...")

        while True:
            # 批量获取消息
            messages = []
            for _ in range(batch_size):
                msg = self.redis_client.lpop(self.redis_config.queue_name)
                if msg:
                    messages.append(msg)
                else:
                    break

            if not messages:
                logger.info("队列已空，历史消息处理完成")
                break

            # 处理消息
            for msg_str in messages:
                await self._process_message(msg_str)

            logger.info(f"已处理 {len(messages)} 条消息，统计: {self.stats}")

        logger.info(f"历史模式完成，总统计: {self.stats}")

    async def run_stream_mode(self, poll_interval: int = 1):
        """
        运行实时模式（持续监听队列）

        Args:
            poll_interval: 轮询间隔（秒）
        """
        if not self.redis_client:
            raise RuntimeError("Redis客户端未启动")

        logger.info("开始实时监听消息...")

        while True:
            try:
                # 阻塞式获取消息
                result = self.redis_client.blpop(
                    self.redis_config.queue_name,
                    timeout=poll_interval
                )

                if result:
                    _, msg_str = result
                    await self._process_message(msg_str)

            except KeyboardInterrupt:
                logger.info("收到中断信号，停止监听")
                break
            except Exception as e:
                logger.error(f"处理消息失败: {e}")
                await asyncio.sleep(1)

        logger.info(f"实时模式结束，总统计: {self.stats}")

    async def _process_message(self, msg_str: str):
        """
        处理单条消息

        Args:
            msg_str: 消息JSON字符串
        """
        try:
            # 解析消息
            msg_data = json.loads(msg_str)
            self.stats['processed'] += 1
            self.stats['last_processed_at'] = datetime.utcnow().isoformat()
            if self.status_tracker:
                self.status_tracker.mark_consumed(msg_data.get('channel', ''), msg_data.get('id', ''))

            # 构建新闻数据
            news_data = {
                'title': msg_data['text'][:100],  # 取前100字符作为标题
                'content': msg_data['text'],
                'date': msg_data['date'],
                'channel_id': msg_data['channel'],
                'message_id': msg_data['id'],
            }

            # 保存到数据库
            if self.news_service:
                existing = self.news_service.get_news_by_source_message(
                    channel_id=msg_data['channel'],
                    message_id=msg_data['id'],
                )

                if existing:
                    self.stats['duplicated'] += 1
                    if self.status_tracker:
                        self.status_tracker.mark_duplicate(msg_data['channel'], msg_data['id'])
                    logger.info(
                        "telegram_consumer duplicate channel=%s message_id=%s",
                        msg_data['channel'],
                        msg_data['id'],
                    )
                    return

                created = self.news_service.create_news(**news_data)
                self.stats['saved'] += 1
                self.stats['last_saved_at'] = datetime.utcnow().isoformat()
                if self.status_tracker:
                    self.status_tracker.mark_saved(created.id, msg_data['channel'], msg_data['id'])
                logger.info(
                    "telegram_consumer saved channel=%s message_id=%s news_id=%s",
                    msg_data['channel'],
                    msg_data['id'],
                    created.id,
                )

        except json.JSONDecodeError as e:
            logger.error(f"消息解析失败: {e}")
            self.stats['failed'] += 1
            self.stats['json_errors'] += 1
            self.stats['last_error_at'] = datetime.utcnow().isoformat()
            self.stats['last_error'] = str(e)
            if self.status_tracker:
                self.status_tracker.mark_error("consumer_json_decode", str(e))
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            self.stats['failed'] += 1
            self.stats['last_error_at'] = datetime.utcnow().isoformat()
            self.stats['last_error'] = str(e)
            error_text = str(e).lower()
            if "keyword" in error_text or "spacy" in error_text or "summary" in error_text:
                self.stats['nlp_errors'] += 1
            else:
                self.stats['db_errors'] += 1
            if self.status_tracker:
                self.status_tracker.mark_error("consumer_process", str(e))

    def get_stats(self) -> dict:
        """获取统计信息"""
        return self.stats.copy()

    def get_health(self) -> dict:
        """获取消费者健康状态。"""
        health = self.get_stats()
        health["queue_name"] = self.redis_config.queue_name
        health["queue_length"] = self.redis_client.llen(self.redis_config.queue_name) if self.redis_client else None
        if self.status_tracker:
            health["pipeline_status"] = self.status_tracker.get_status()
        return health

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'processed': 0,
            'saved': 0,
            'duplicated': 0,
            'failed': 0,
            'json_errors': 0,
            'db_errors': 0,
            'nlp_errors': 0,
            'last_processed_at': None,
            'last_saved_at': None,
            'last_error_at': None,
            'last_error': None,
        }
