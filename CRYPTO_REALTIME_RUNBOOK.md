# Crypto/Telegram 实时链路运行手册

## 1. 启动 Redis
```bash
redis-server
```

检查 Redis：
```bash
redis-cli ping
```

## 2. 初始化数据库
```bash
source .venv/bin/activate
env -u DEBUG .venv/bin/python scripts/init_database.py
```

## 3. 启动 API 服务
```bash
source .venv/bin/activate
env -u DEBUG .venv/bin/python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

关键页面与接口：
- 首页：`http://127.0.0.1:8000/`
- 搜索页：`http://127.0.0.1:8000/search`
- 聊天页：`http://127.0.0.1:8000/chat`
- Dashboard API：`http://127.0.0.1:8000/api/dashboard`
- Crypto 链路健康检查：`http://127.0.0.1:8000/api/crypto-pipeline/health`

## 4. 启动 Telegram 实时链路

### 完整链路
```bash
source .venv/bin/activate
env -u DEBUG .venv/bin/python scripts/run_crypto_crawler.py -mode stream --component pipeline
```

### 仅生产者
```bash
env -u DEBUG .venv/bin/python scripts/run_crypto_crawler.py -mode stream --component producer
```

### 仅消费者
```bash
env -u DEBUG .venv/bin/python scripts/run_crypto_crawler.py -mode stream --component consumer
```

### 历史回放
```bash
env -u DEBUG .venv/bin/python scripts/run_crypto_crawler.py -mode history --limit 10 --component pipeline
```

## 5. 观察链路状态

检查 Redis 队列长度：
```bash
redis-cli LLEN crypto_news_queue
```

查看链路健康：
```bash
curl -sS http://127.0.0.1:8000/api/crypto-pipeline/health
```

关键字段：
- `queue_length`
- `last_enqueued_at`
- `last_consumed_at`
- `last_saved_at`
- `last_error`
- `error_count`

## 6. 人工验收步骤

1. 启动 Redis、API、Crypto crawler 完整链路。
2. 向配置中的 Telegram 测试频道发送一条新消息。
3. 访问 `/api/crypto-pipeline/health`，确认 `last_enqueued_at`、`last_consumed_at`、`last_saved_at` 更新。
4. 在首页等待最多 60 秒，确认 `Crypto 最新新闻` 区出现该消息。
5. 在搜索页按消息中的关键词搜索，确认能命中。
6. 在聊天页提问“某关键词最新新闻”，确认 Agent 能返回新数据。

## 7. 常见问题

### Redis 健康检查失败
- 确认 `redis-server` 已启动
- 确认 `.env` 中 `REDIS_HOST/REDIS_PORT/REDIS_DB` 正确

### Producer 能启动但没有抓到实时消息
- 确认 `TELEGRAM_API_ID/API_HASH/PHONE` 正确
- 确认 `TELEGRAM_CHANNELS` 中的频道可访问
- 确认 Telegram 频道用户名与配置一致

### 队列有消息但数据库没更新
- 看 `/api/crypto-pipeline/health` 的 `last_error`
- 查看 consumer 日志中的 `telegram_consumer saved/duplicate/error`

### 首页没更新
- 首页默认每 60 秒轮询一次 `/api/dashboard`
- 先直接请求 `/api/dashboard`，确认 `crypto_latest` 是否已包含新消息
