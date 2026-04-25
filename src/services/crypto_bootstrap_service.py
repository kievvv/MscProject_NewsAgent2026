"""
Crypto crawler startup bootstrap.

Runs a bounded Telegram history backfill in the background when the local
Crypto news database is empty or stale. Failures are reported through status
instead of blocking API startup.
"""
import asyncio
import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from config.settings import settings
from src.core.models import NewsSource
from src.crawlers.telegram import TelegramConfig, RedisConfig, TelegramProducer, TelegramConsumer
from src.data.repositories.news import NewsRepository
from src.services.news_service import get_news_service

logger = logging.getLogger(__name__)


class CryptoStartupBootstrapService:
    """Coordinates optional startup backfill for Crypto news."""

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._local_lock = asyncio.Lock()
        self._status: Dict[str, Any] = {
            "startup_backfill_enabled": settings.AUTO_START_CRYPTO_CRAWLER,
            "startup_backfill_status": "not_started",
            "startup_backfill_limit": settings.CRYPTO_STARTUP_BACKFILL_LIMIT,
            "last_backfill_error": None,
        }

    def get_status(self) -> Dict[str, Any]:
        status = dict(self._status)
        status["startup_backfill_enabled"] = settings.AUTO_START_CRYPTO_CRAWLER
        status["startup_backfill_limit"] = settings.CRYPTO_STARTUP_BACKFILL_LIMIT
        return status

    def schedule_startup_check(self) -> None:
        if not settings.AUTO_START_CRYPTO_CRAWLER:
            self._set_status("disabled")
            return
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run_startup_check(), name="crypto-startup-bootstrap")

    async def _run_startup_check(self) -> None:
        async with self._local_lock:
            try:
                should_backfill, reason = self._should_backfill()
                if not should_backfill:
                    self._set_status("skipped_fresh", reason=reason)
                    return
                await asyncio.to_thread(lambda: asyncio.run(self._run_backfill(reason)))
            except Exception as exc:
                logger.warning("Crypto startup bootstrap failed: %s", exc, exc_info=True)
                self._set_status("error", error=str(exc))

    def _should_backfill(self) -> tuple[bool, str]:
        pending_queue = self._pending_queue_length()
        if pending_queue > 0:
            return True, f"pending_queue_{pending_queue}"

        repo = NewsRepository(source=NewsSource.CRYPTO)
        total = repo.count()
        if total <= 0:
            return True, "empty_database"

        latest = repo.get_recent(limit=1)
        if not latest or not latest[0].date:
            return True, "missing_latest_date"

        latest_dt = self._parse_datetime(latest[0].date)
        if latest_dt is None:
            return True, "unparseable_latest_date"

        age_hours = (datetime.now(timezone.utc) - latest_dt).total_seconds() / 3600
        if age_hours >= settings.CRYPTO_BACKFILL_STALE_HOURS:
            return True, f"stale_{age_hours:.1f}h"
        return False, f"fresh_{age_hours:.1f}h"

    def _pending_queue_length(self) -> int:
        redis_client = None
        try:
            redis_client = self._connect_redis(log_errors=False)
            if redis_client is None:
                return 0
            return int(redis_client.llen("crypto_news_queue"))
        except Exception:
            return 0
        finally:
            if redis_client is not None:
                redis_client.close()

    @staticmethod
    def _parse_datetime(value: str) -> Optional[datetime]:
        text = (value or "").strip()
        if not text:
            return None
        try:
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return None

    async def _run_backfill(self, reason: str) -> None:
        redis_client = None
        lock_key = "crypto_news_queue:startup_bootstrap_lock"
        lock_token = str(uuid.uuid4())

        try:
            redis_client = self._connect_redis()
            if redis_client is None and settings.CRYPTO_REQUIRE_REDIS:
                self._set_status("error", reason=reason, error="Redis is required but unavailable")
                return

            if redis_client is not None:
                acquired = redis_client.set(lock_key, lock_token, nx=True, ex=7200)
                if not acquired:
                    self._set_status("skipped_already_running", reason=reason)
                    return

            self._set_status("running", reason=reason, started_at=datetime.utcnow().isoformat())
            await self._run_telegram_history_backfill(fetch_history=not reason.startswith("pending_queue_"))
            self._set_status("completed", reason=reason, completed_at=datetime.utcnow().isoformat())
        finally:
            if redis_client is not None:
                try:
                    if redis_client.get(lock_key) == lock_token:
                        redis_client.delete(lock_key)
                    redis_client.close()
                except Exception:
                    logger.debug("Failed to release startup bootstrap lock", exc_info=True)

    def _connect_redis(self, log_errors: bool = True):
        try:
            import redis
            client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
            )
            client.ping()
            return client
        except Exception as exc:
            if log_errors:
                logger.warning("Redis unavailable for startup bootstrap: %s", exc)
            return None

    async def _run_telegram_history_backfill(self, fetch_history: bool = True) -> None:
        telegram_config = TelegramConfig(
            api_id=settings.TELEGRAM_API_ID,
            api_hash=settings.TELEGRAM_API_HASH,
            channels=settings.TELEGRAM_CHANNELS,
            session_name="crypto_news_crawler",
            phone=settings.TELEGRAM_PHONE,
        )
        redis_config = RedisConfig(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            queue_name="crypto_news_queue",
        )
        news_service = get_news_service(
            source=NewsSource.CRYPTO,
            auto_extract_keywords=settings.CRYPTO_STARTUP_NLP_MODE == "keywords",
            auto_generate_summary=False,
        )
        producer = TelegramProducer(telegram_config, redis_config)
        consumer = TelegramConsumer(redis_config, news_service)
        channel_count = max(1, len(settings.TELEGRAM_CHANNELS))
        per_channel_limit = max(1, math.ceil(settings.CRYPTO_STARTUP_BACKFILL_LIMIT / channel_count))

        consumer.start()
        if fetch_history:
            await producer.start()
        try:
            if fetch_history:
                await producer.run_history_mode(limit=per_channel_limit)
            await consumer.run_history_mode()
        finally:
            if fetch_history:
                await producer.stop()
            consumer.stop()

    def _set_status(self, status: str, **fields: Any) -> None:
        self._status.update({
            "startup_backfill_status": status,
            "startup_backfill_enabled": settings.AUTO_START_CRYPTO_CRAWLER,
            "startup_backfill_limit": settings.CRYPTO_STARTUP_BACKFILL_LIMIT,
        })
        if "error" in fields:
            self._status["last_backfill_error"] = fields["error"]
        elif status in {"running", "completed", "skipped_fresh", "skipped_already_running", "disabled"}:
            self._status["last_backfill_error"] = None
        self._status.update(fields)


_crypto_startup_bootstrap_service: Optional[CryptoStartupBootstrapService] = None


def get_crypto_startup_bootstrap_service() -> CryptoStartupBootstrapService:
    global _crypto_startup_bootstrap_service
    if _crypto_startup_bootstrap_service is None:
        _crypto_startup_bootstrap_service = CryptoStartupBootstrapService()
    return _crypto_startup_bootstrap_service
