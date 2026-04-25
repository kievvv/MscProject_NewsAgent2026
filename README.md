# NewsAgent2025

NewsAgent2025 is a FastAPI-based news aggregation and analysis system for Web3/Crypto and Hong Kong stock news. It combines crawling, SQLite storage, keyword and trend analysis, personalized recommendations, and an AI Agent interface.

## Current Entry Points

Run the API and web UI:

```bash
uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

Useful pages and endpoints:

- Web home: `http://127.0.0.1:8000/`
- Search UI: `http://127.0.0.1:8000/search`
- Analyzer UI: `http://127.0.0.1:8000/analyzer`
- Chat UI: `http://127.0.0.1:8000/chat`
- API docs: `http://127.0.0.1:8000/docs`
- Health check: `GET /api/health`
- Crypto pipeline status: `GET /api/crypto-pipeline/health`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/init_database.py
```

Configuration is loaded from `.env` through `config/settings.py`. Important settings include database paths, Telegram credentials, Redis settings, API host/port, and LLM provider settings.

## Main Commands

Initialize databases:

```bash
python scripts/init_database.py
```

Run the Crypto Telegram crawler:

```bash
python scripts/run_crypto_crawler.py -mode history --limit 100
python scripts/run_crypto_crawler.py -mode stream
python scripts/run_crypto_crawler.py -mode hybrid --limit 500
```

Run only one crawler component:

```bash
python scripts/run_crypto_crawler.py -mode stream --component producer
python scripts/run_crypto_crawler.py -mode stream --component consumer
```

Run the HKStocks crawler:

```bash
python scripts/run_hkstocks_crawler.py --days 1 --max-count 100
```

Run tests:

```bash
pytest
```

## Data Stores

- Crypto news: `data/testdb_cryptonews.db`, table `messages`
- HKStocks news: `data/testdb_history.db`, table `hkstocks_news`
- Agent conversations and user profiles: `data/databases/news_analysis.db`

## Documentation

See [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for the architecture, data flow, module map, and known implementation gaps.
