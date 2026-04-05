"""
Crypto新闻爬虫启动脚本
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from src.crawlers.telegram import (
    TelegramProducer,
    TelegramConsumer,
    TelegramConfig,
    RedisConfig
)
from src.services import get_news_service
from src.core.models import NewsSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_history(producer: TelegramProducer, consumer: TelegramConsumer, limit: int = 100):
    """
    运行历史模式

    Args:
        producer: 生产者
        consumer: 消费者
        limit: 每个频道的消息限制
    """
    logger.info(">>> 开始历史模式")

    # 生产者：抓取历史消息
    count = await producer.run_history_mode(limit=limit)
    logger.info(f"生产者完成，共抓取 {count} 条消息")

    # 消费者：处理队列中的消息
    await consumer.run_history_mode()
    logger.info(">>> 历史消息处理完成")


async def run_stream(producer: TelegramProducer, consumer: TelegramConsumer):
    """
    运行实时模式

    Args:
        producer: 生产者
        consumer: 消费者
    """
    logger.info(">>> 开始实时模式")

    # 并发运行生产者和消费者
    producer_task = asyncio.create_task(
        producer.run_stream_mode(),
        name="crypto-news-producer"
    )
    consumer_task = asyncio.create_task(
        consumer.run_stream_mode(),
        name="crypto-news-consumer"
    )

    await asyncio.gather(producer_task, consumer_task)


async def run_hybrid(producer: TelegramProducer, consumer: TelegramConsumer, limit: int = 100):
    """
    先回溯历史消息，再进入实时监听。
    """
    logger.info(">>> 开始组合模式：先回溯历史消息，再实时监听")
    await run_history(producer, consumer, limit=limit)
    logger.info(">>> 历史回溯完成，切换到实时监听")
    await run_stream(producer, consumer)


async def run_component(component: str,
                        mode: str,
                        producer: TelegramProducer,
                        consumer: TelegramConsumer,
                        limit: int = 100):
    """按组件模式运行链路。"""
    if component == "producer":
        await producer.start()
        try:
            if mode == "history":
                count = await producer.run_history_mode(limit=limit)
                logger.info(f"Producer only completed, queued {count} messages")
            elif mode == "hybrid":
                count = await producer.run_history_mode(limit=limit)
                logger.info(f"Producer history backfill completed, queued {count} messages")
                await producer.run_stream_mode()
            else:
                await producer.run_stream_mode()
        finally:
            await producer.stop()
        return

    if component == "consumer":
        consumer.start()
        try:
            if mode == "history":
                await consumer.run_history_mode()
            elif mode == "hybrid":
                await consumer.run_history_mode()
                await consumer.run_stream_mode()
            else:
                await consumer.run_stream_mode()
        finally:
            consumer.stop()
        return

    await producer.start()
    consumer.start()
    try:
        if mode == "history":
            await run_history(producer, consumer, limit=limit)
        elif mode == "hybrid":
            await run_hybrid(producer, consumer, limit=limit)
        else:
            await run_stream(producer, consumer)
    finally:
        await producer.stop()
        consumer.stop()


async def main(mode: str = "stream", limit: int = 100, component: str = "pipeline", generate_summary: bool = True):
    """
    主函数

    Args:
        mode: 运行模式（history/stream）
        limit: 历史模式的消息限制
    """
    # 配置
    telegram_config = TelegramConfig(
        api_id=settings.TELEGRAM_API_ID,
        api_hash=settings.TELEGRAM_API_HASH,
        channels=settings.TELEGRAM_CHANNELS,
        session_name="crypto_news_crawler",
        phone=settings.TELEGRAM_PHONE
    )

    redis_config = RedisConfig(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        queue_name="crypto_news_queue"
    )

    # 创建服务
    news_service = get_news_service(
        source=NewsSource.CRYPTO,
        auto_extract_keywords=True,
        auto_generate_summary=generate_summary
    )

    # 创建生产者和消费者
    try:
        producer = TelegramProducer(telegram_config, redis_config)
        consumer = TelegramConsumer(redis_config, news_service)

        logger.info("生产者和消费者初始化成功")

    except Exception as e:
        logger.error(f"初始化失败: {e}")
        return

    # 启动
    try:
        await run_component(component, mode, producer, consumer, limit=limit)

    except KeyboardInterrupt:
        logger.info("收到中断信号")
    except Exception as e:
        logger.error(f"运行错误: {e}")
    finally:
        logger.info("爬虫已停止")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="Crypto新闻爬虫")

    parser.add_argument(
        "-mode",
        choices=["history", "stream", "hybrid"],
        default="stream",
        help="运行模式：history(历史回溯)、stream(实时监听) 或 hybrid(先回溯再监听)"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=settings.TELEGRAM_BACKFILL_LIMIT,
        help=f"历史模式：每个频道的消息限制（默认{settings.TELEGRAM_BACKFILL_LIMIT}）"
    )

    parser.add_argument(
        "--component",
        choices=["pipeline", "producer", "consumer"],
        default="pipeline",
        help="运行组件：pipeline(完整链路)、producer(仅抓取入队)、consumer(仅消费入库)"
    )

    parser.add_argument(
        "--disable-summary",
        action="store_true",
        help="禁用入库时自动摘要生成"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(
        main(
            mode=args.mode,
            limit=args.limit,
            component=args.component,
            generate_summary=not args.disable_summary,
        )
    )
