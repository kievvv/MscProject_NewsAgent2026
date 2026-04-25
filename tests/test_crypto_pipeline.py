import json
from types import SimpleNamespace
from unittest.mock import Mock

from config.settings import settings
from src.api.routes import frontend as frontend_routes
from src.crawlers.telegram.config import RedisConfig
from src.crawlers.telegram.consumer import TelegramConsumer
from src.data.repositories.news import NewsRepository
from src.core.models import NewsSource
from src.services.personalization_service import PersonalizationService


class DummyTracker:
    def mark_consumed(self, *args, **kwargs):
        return None

    def mark_duplicate(self, *args, **kwargs):
        return None

    def mark_saved(self, *args, **kwargs):
        return None

    def mark_error(self, *args, **kwargs):
        return None

    def get_status(self):
        return {}


def test_crypto_repository_deduplicates_channel_message(monkeypatch, tmp_path):
    crypto_db = tmp_path / "crypto_pipeline.db"
    monkeypatch.setattr(settings, "CRYPTO_DB_PATH", str(crypto_db), raising=False)

    repo = NewsRepository(source=NewsSource.CRYPTO)

    first = repo.create(
        title="Bitcoin breaks out",
        content="Bitcoin rallies above resistance.",
        channel_id="@demo",
        message_id="1001",
        date="2026-04-05T10:00:00",
    )
    second = repo.create(
        title="Bitcoin breaks out",
        content="Bitcoin rallies above resistance.",
        channel_id="@demo",
        message_id="1001",
        date="2026-04-05T10:00:00",
    )

    assert first.id == second.id
    assert repo.count() == 1
    assert repo.get_by_channel_message("@demo", 1001).id == first.id


def test_consumer_updates_stats_for_saved_and_duplicate_messages():
    service = Mock()
    service.get_news_by_source_message.side_effect = [
        None,
        SimpleNamespace(id=1, channel_id="@demo", message_id=1001),
    ]
    service.create_news.return_value = SimpleNamespace(id=99)

    consumer = TelegramConsumer(RedisConfig(queue_name="test_queue"), news_service=service)
    consumer.status_tracker = DummyTracker()

    payload = json.dumps({
        "id": "1001",
        "channel": "@demo",
        "text": "Bitcoin ETF update",
        "date": "2026-04-05T10:00:00",
    }, ensure_ascii=False)

    import asyncio

    asyncio.run(consumer._process_message(payload))
    asyncio.run(consumer._process_message(payload))

    assert consumer.stats["saved"] == 1
    assert consumer.stats["duplicated"] == 1
    assert consumer.stats["failed"] == 0
    service.create_news.assert_called_once()


def test_consumer_tracks_json_errors():
    consumer = TelegramConsumer(RedisConfig(queue_name="test_queue"), news_service=Mock())
    consumer.status_tracker = DummyTracker()

    import asyncio

    asyncio.run(consumer._process_message("{bad json"))

    assert consumer.stats["failed"] == 1
    assert consumer.stats["json_errors"] == 1


def test_dashboard_snapshot_survives_market_failures(monkeypatch):
    mock_news_service = Mock()
    mock_news_service.get_statistics.return_value = {
        "total_count": 1,
        "with_keywords": 1,
        "keyword_rate": 1.0,
    }

    news = SimpleNamespace(
        id=1,
        title="Realtime BTC news",
        text="BTC makes a move",
        abstract=None,
        summary=None,
        keywords="btc,etf",
        channel_id="@demo",
        currency="BTC",
        industry=None,
        date="2026-04-05T10:00:00",
        source=NewsSource.CRYPTO,
        original_text="BTC makes a move",
        url="",
    )
    mock_search_service = Mock()
    mock_search_service.get_popular_keywords.return_value = [{"keyword": "btc", "count": 3}]
    mock_search_service.search_recent.return_value = [news]

    class FailingMarketService:
        def fetch_fear_greed_index(self):
            raise RuntimeError("fng down")

        def fetch_crypto_market_board(self, limit=20):
            raise RuntimeError("market down")

    monkeypatch.setattr(frontend_routes, "get_news_service", lambda **kwargs: mock_news_service)
    monkeypatch.setattr(frontend_routes, "get_search_service", lambda **kwargs: mock_search_service)
    monkeypatch.setattr(frontend_routes, "get_market_service", lambda **kwargs: FailingMarketService())

    snapshot = frontend_routes.build_dashboard_snapshot()

    assert snapshot["crypto_latest"]
    assert snapshot["fear_greed"]["classification"] == "数据不可用"
    assert snapshot["crypto_market_board"]["coins"] == []


def test_recommendations_fall_back_to_historical_news(monkeypatch, tmp_path):
    crypto_db = tmp_path / "historical_recommendations.db"
    monkeypatch.setattr(settings, "CRYPTO_DB_PATH", str(crypto_db), raising=False)

    repo = NewsRepository(source=NewsSource.CRYPTO)
    repo.create(
        content="Bitcoin ETF and AI infrastructure updates remain relevant.",
        channel_id="@demo",
        message_id="2001",
        keywords="BTC,ETF,AI",
        date="2020-01-01T10:00:00+00:00",
    )

    service = PersonalizationService()
    results, status = service.recommend_news_with_status(
        preferences={"focus_assets": ["BTC"], "focus_themes": ["AI", "ETF"]},
        limit=4,
        source=NewsSource.CRYPTO,
    )

    assert len(results) == 1
    assert status["mode"] == "historical_fallback"
    assert results[0]["recommendation_reasons"]
