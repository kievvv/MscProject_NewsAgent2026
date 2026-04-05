"""
Telegram消息生产者
从Telegram频道抓取消息并放入Redis队列
"""
import json
import logging
from typing import Optional
from datetime import datetime

try:
    from telethon import TelegramClient
    from telethon.tl.types import Message
    import redis
except ImportError:
    TelegramClient = None
    Message = None
    redis = None

from src.crawlers.telegram.config import TelegramConfig, RedisConfig
from src.crawlers.telegram.monitor import PipelineStatusTracker

logger = logging.getLogger(__name__)


class TelegramProducer:
    """
    Telegram消息生产者

    功能：
    1. 连接Telegram客户端
    2. 监听指定频道消息
    3. 将消息推送到Redis队列
    """

    def __init__(self, telegram_config: TelegramConfig, redis_config: RedisConfig):
        """
        初始化生产者

        Args:
            telegram_config: Telegram配置
            redis_config: Redis配置
        """
        if TelegramClient is None or redis is None:
            raise ImportError("请安装 telethon 和 redis: pip install telethon redis")

        self.telegram_config = telegram_config
        self.redis_config = redis_config

        # Telegram客户端
        self.client: Optional[TelegramClient] = None

        # Redis客户端
        self.redis_client: Optional[redis.Redis] = None
        self.status_tracker: Optional[PipelineStatusTracker] = None

    async def start(self):
        """启动客户端"""
        try:
            # 连接Telegram
            self.client = TelegramClient(
                self.telegram_config.session_name,
                self.telegram_config.api_id,
                self.telegram_config.api_hash
            )
            await self.client.start(phone=self.telegram_config.phone)
            logger.info("Telegram客户端连接成功")

            # 连接Redis
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
            await self._validate_channels()
            self.status_tracker.mark_producer_started(self.telegram_config.channels)

        except Exception as e:
            logger.error(f"启动失败: {e}")
            raise

    async def stop(self):
        """停止客户端"""
        if self.client:
            await self.client.disconnect()
            logger.info("Telegram客户端已断开")

        if self.redis_client:
            if self.status_tracker:
                self.status_tracker.mark_producer_stopped()
            self.redis_client.close()
            logger.info("Redis连接已关闭")

    async def _validate_channels(self):
        """校验频道配置并确认 Telegram 侧可访问。"""
        invalid_channels = []
        for channel in self.telegram_config.channels:
            if not isinstance(channel, str) or not channel.strip():
                invalid_channels.append(channel)
                continue
            normalized = channel.strip()
            if self.client:
                try:
                    await self.client.get_entity(normalized)
                except Exception as exc:
                    invalid_channels.append(f"{channel} ({exc})")
        if invalid_channels:
            raise ValueError(f"Invalid Telegram channels: {invalid_channels}")

    async def fetch_history(self, channel: str, limit: int = 100) -> int:
        """
        抓取历史消息

        Args:
            channel: 频道名称
            limit: 限制数量

        Returns:
            抓取的消息数量
        """
        if not self.client:
            raise RuntimeError("Telegram客户端未启动")

        count = 0
        try:
            logger.info(f"开始抓取频道 {channel} 的历史消息（限制 {limit} 条）...")
            display_channel = TelegramConfig.normalize_channel(channel)

            async for message in self.client.iter_messages(channel, limit=limit):
                if message.text:
                    await self._push_message(message, display_channel)
                    count += 1

            logger.info(f"频道 {channel} 历史消息抓取完成，共 {count} 条")
            return count

        except Exception as e:
            logger.error(f"抓取历史消息失败: {e}")
            return count

    async def run_history_mode(self, limit: int = 100) -> int:
        """
        运行历史模式（抓取所有频道的历史消息）

        Args:
            limit: 每个频道的限制数量

        Returns:
            总抓取数量
        """
        total = 0
        for channel in self.telegram_config.channels:
            count = await self.fetch_history(channel, limit)
            total += count

        logger.info(f"历史模式完成，总共抓取 {total} 条消息")
        return total

    async def run_stream_mode(self):
        """
        运行实时模式（监听新消息）
        """
        if not self.client:
            raise RuntimeError("Telegram客户端未启动")

        logger.info("开始实时监听新消息...")

        @self.client.on(Message)
        async def handler(event):
            """消息处理器"""
            message = event.message
            channel = await event.get_chat()

            # 检查是否在监听列表中
            channel_username = (getattr(channel, 'username', None) or "").lower()
            if channel_username in self.telegram_config.normalized_channels:
                if message.text:
                    await self._push_message(message, TelegramConfig.normalize_channel(channel_username))

        # 保持运行
        await self.client.run_until_disconnected()

    async def _push_message(self, message, channel: str):
        """
        推送消息到Redis队列

        Args:
            message: Telegram消息对象
            channel: 频道名称
        """
        try:
            # 构建消息数据
            message_data = {
                'id': str(message.id),
                'channel': channel,
                'text': message.text,
                'date': message.date.isoformat() if message.date else datetime.now().isoformat(),
                'views': getattr(message, 'views', 0),
                'forwards': getattr(message, 'forwards', 0),
            }

            # 推送到Redis
            if self.redis_client:
                self.redis_client.rpush(
                    self.redis_config.queue_name,
                    json.dumps(message_data, ensure_ascii=False)
                )
                if self.status_tracker:
                    self.status_tracker.mark_message_enqueued(channel, message.id)
                logger.debug(f"消息已推送: {channel}/{message.id}")

        except Exception as e:
            if self.status_tracker:
                self.status_tracker.mark_error("producer_push", str(e))
            logger.error(f"推送消息失败: {e}")
