"""
Telegram 实时链路状态追踪。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional, Union


class PipelineStatusTracker:
    """使用 Redis 保存跨进程可见的链路状态。"""

    def __init__(self, redis_client, queue_name: str):
        self.redis_client = redis_client
        self.queue_name = queue_name
        self.status_key = f"{queue_name}:status"

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat()

    def _set(self, **fields: Any) -> None:
        normalized = {}
        for key, value in fields.items():
            if isinstance(value, (dict, list)):
                normalized[key] = json.dumps(value, ensure_ascii=False)
            elif value is None:
                normalized[key] = ""
            else:
                normalized[key] = str(value)
        if normalized:
            self.redis_client.hset(self.status_key, mapping=normalized)

    def mark_producer_started(self, channels: list[str]) -> None:
        self._set(
            producer_status="running",
            producer_started_at=self._now(),
            producer_channels=channels,
            queue_length=self.queue_length(),
        )

    def mark_producer_stopped(self) -> None:
        self._set(producer_status="stopped", producer_stopped_at=self._now(), queue_length=self.queue_length())

    def mark_message_enqueued(self, channel: str, message_id: Union[str, int]) -> None:
        self._set(
            last_enqueued_at=self._now(),
            last_enqueued_channel=channel,
            last_enqueued_message_id=message_id,
            queue_length=self.queue_length(),
        )

    def mark_consumer_started(self) -> None:
        self._set(consumer_status="running", consumer_started_at=self._now(), queue_length=self.queue_length())

    def mark_consumer_stopped(self) -> None:
        self._set(consumer_status="stopped", consumer_stopped_at=self._now(), queue_length=self.queue_length())

    def mark_consumed(self, channel: str, message_id: Union[str, int]) -> None:
        self._set(
            last_consumed_at=self._now(),
            last_consumed_channel=channel,
            last_consumed_message_id=message_id,
            queue_length=self.queue_length(),
        )

    def mark_saved(self, news_id: int, channel: str, message_id: Union[str, int]) -> None:
        self._set(
            last_saved_at=self._now(),
            last_saved_news_id=news_id,
            last_saved_channel=channel,
            last_saved_message_id=message_id,
            queue_length=self.queue_length(),
        )

    def mark_duplicate(self, channel: str, message_id: Union[str, int]) -> None:
        self._set(
            last_duplicate_at=self._now(),
            last_duplicate_channel=channel,
            last_duplicate_message_id=message_id,
            queue_length=self.queue_length(),
        )

    def mark_error(self, stage: str, error: str) -> None:
        current = self.redis_client.hget(self.status_key, "error_count")
        try:
            error_count = int(current or 0) + 1
        except ValueError:
            error_count = 1
        self._set(
            last_error_at=self._now(),
            last_error_stage=stage,
            last_error=error,
            error_count=error_count,
            queue_length=self.queue_length(),
        )

    def queue_length(self) -> int:
        try:
            return int(self.redis_client.llen(self.queue_name))
        except Exception:
            return -1

    def get_status(self) -> dict[str, Any]:
        raw = self.redis_client.hgetall(self.status_key) or {}
        status: dict[str, Any] = dict(raw)
        for key in ("producer_channels",):
            if key in status and status[key]:
                try:
                    status[key] = json.loads(status[key])
                except json.JSONDecodeError:
                    pass
        if "queue_length" not in status:
            status["queue_length"] = self.queue_length()
        return status


def build_pipeline_status(redis_config) -> dict[str, Any]:
    """读取链路状态，供 API 健康检查使用。"""
    try:
        import redis
    except ImportError:
        return {
            "success": False,
            "queue_name": redis_config.queue_name,
            "error": "redis package is not installed",
        }

    client: Optional[redis.Redis] = None
    try:
        client = redis.Redis(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.db,
            password=redis_config.password,
            decode_responses=True,
        )
        client.ping()
        tracker = PipelineStatusTracker(client, redis_config.queue_name)
        return {
            "success": True,
            "queue_name": redis_config.queue_name,
            **tracker.get_status(),
        }
    except Exception as exc:
        return {
            "success": False,
            "queue_name": redis_config.queue_name,
            "error": str(exc),
        }
    finally:
        if client:
            client.close()
