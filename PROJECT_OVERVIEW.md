# Project Overview

## System Purpose

NewsAgent2025 collects Web3/Crypto and Hong Kong stock news, stores it in SQLite, enriches it with keywords and summaries, exposes search and trend APIs, and provides personalized recommendations through a web UI and AI Agent interface.

## Architecture

The code follows a layered structure:

1. Crawlers collect raw news.
2. Services apply business logic such as keyword extraction, summarization, recommendation, and Agent orchestration.
3. Repositories isolate SQLite access.
4. API routes expose JSON APIs, HTML pages, and WebSocket chat.
5. Frontend templates and static files provide the web experience.

Primary application entry:

```text
src.api.app:app
```

Main route groups:

- `/api/v1/news`: create, update, delete, list, summarize, and inspect news.
- `/api/v1/search`: keyword, similarity, date range, channel, currency, industry, advanced, and ranked search.
- `/api/v1/trend`: keyword trend, comparison, anomalies, growth velocity, lifecycle, prediction.
- `/api/v1/push`: subscriptions, alert checks, batch push statistics.
- `/api/v1/market`: market board, Fear & Greed, price-related interfaces.
- `/api/v1/agent`: chat, conversations, skills, profile, onboarding.
- `/ws/chat`: WebSocket chat and skill execution.
- `/api/analyze` and `/api/query-keyword`: analyzer UI support.

## Data Flow

### Crypto / Telegram

```text
Telegram channels
  -> TelegramProducer
  -> Redis list: crypto_news_queue
  -> TelegramConsumer
  -> NewsService
  -> NewsRepository
  -> data/testdb_cryptonews.db / messages
```

The consumer checks duplicates by `channel_id + message_id`, writes news, extracts keywords and currencies, and can optionally generate summaries. Pipeline status is tracked in Redis and exposed through `/api/crypto-pipeline/health`.

### HKStocks / AAStocks

```text
AAStocks pages
  -> HKStocksScraper
  -> NewsService
  -> NewsRepository
  -> data/testdb_history.db / hkstocks_news
```

The crawler fetches list pages, parses detail pages, extracts content and stock codes, then stores records through the same service/repository pattern.

### Web UI

The root page builds a dashboard snapshot from both news sources, personalization, trending keywords, latest news, recommendations, Fear & Greed, and a crypto market board. Search, analyzer, and chat pages call the API routes directly.

### AI Agent

`AIAgentService` handles chat requests. It first parses task intent with rule-based logic:

- `discover` and `focus`: personalized news recommendation.
- `understand`: `DeepDive` skill.
- `report`: `DailyBriefing` or `DeepDive` skill.
- `chat`: profile summary or fallback Agent graph.

If the rule flow does not handle the message, the request goes into the Agent graph:

- `CoordinatorAgent`
- `NewsAgent`
- `AnalysisAgent`
- `TradeAgent`
- `UserProfileAgent`
- simple chat node

LLM providers are abstracted behind `src/ai/llm/` and can use Ollama, OpenAI, or Anthropic. Ollama is the default configured provider.

## Important Modules

- `config/settings.py`: configuration and environment loading.
- `src/core/models.py`: domain dataclasses.
- `src/data/database.py`: SQLite connection helper.
- `src/data/repositories/`: repository layer for news, keywords, subscriptions, conversations, profiles.
- `src/services/news_service.py`: news creation, updates, keyword extraction, summary generation.
- `src/services/search_service.py`: search and ranking logic.
- `src/services/trend_service.py`: trend API service layer.
- `src/services/personalization_service.py`: user profile normalization, scoring, recommendations.
- `src/services/ai_agent_service.py`: Agent orchestration and skill execution.
- `src/analyzers/`: keyword extraction, similarity, summarization, trend analysis.
- `src/crawlers/telegram/`: Telegram producer, consumer, Redis status monitor.
- `src/crawlers/hkstocks/scraper.py`: AAStocks crawler.
- `src/api/app.py`: FastAPI app registration.
- `templates_UI/` and `static/`: web interface.

## Current Implementation Notes

- Crypto ingestion is the most complete production path.
- HKStocks ingestion works structurally, but schema compatibility is less mature than Crypto.
- Market service has real Fear & Greed and CoinGecko market board calls, while several price/history/correlation methods still use placeholder or empty data.
- WebSocket chat currently sends simulated chunks from a complete Agent response.
- Push service has subscription and alert structure, but external delivery integration is not fully productionized.
- Authentication, CORS, and rate limiting are still development-oriented.

## Cleanup Policy

Historical phase reports, one-off verification notes, and root-level legacy test scripts were removed. Canonical tests now live under `tests/`, and operational documentation is consolidated into `README.md` and this file.
