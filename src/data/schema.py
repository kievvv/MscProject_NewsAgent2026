"""
数据库表结构定义
"""

# 新闻消息表（Crypto新闻）
CREATE_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT,
    message_id INTEGER,
    text TEXT NOT NULL,
    url TEXT,
    keywords TEXT,
    currency TEXT,
    abstract TEXT,
    date TEXT NOT NULL,
    original_text TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

# 港股新闻表
CREATE_HKSTOCKS_NEWS_TABLE = """
CREATE TABLE IF NOT EXISTS hkstocks_news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    content TEXT NOT NULL,
    publish_date TEXT NOT NULL,
    source TEXT DEFAULT 'AAStocks',
    category TEXT,
    keywords TEXT,
    industry TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
"""

# 新闻关键词表
CREATE_NEWS_KEYWORDS_TABLE = """
CREATE TABLE IF NOT EXISTS news_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_id INTEGER NOT NULL,
    keyword TEXT NOT NULL,
    weight REAL NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (news_id) REFERENCES messages(id),
    UNIQUE(news_id, keyword)
);
"""

# 关键词热度趋势表
CREATE_KEYWORD_TRENDS_TABLE = """
CREATE TABLE IF NOT EXISTS keyword_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    date TEXT NOT NULL,
    count INTEGER DEFAULT 0,
    total_weight REAL DEFAULT 0.0,
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(keyword, date)
);
"""

# 关键词同义词映射表
CREATE_KEYWORD_SYNONYMS_TABLE = """
CREATE TABLE IF NOT EXISTS keyword_synonyms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    representative_keyword TEXT NOT NULL,
    similarity REAL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(keyword, representative_keyword)
);
"""

# 用户订阅表
CREATE_SUBSCRIPTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    telegram_chat_id TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, keyword)
);
"""

# 推送历史表
CREATE_PUSH_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS push_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER NOT NULL,
    news_id INTEGER NOT NULL,
    pushed_at TEXT DEFAULT (datetime('now')),
    status TEXT DEFAULT 'success',
    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id),
    FOREIGN KEY (news_id) REFERENCES messages(id)
);
"""

# 新闻摘要缓存表
CREATE_NEWS_SUMMARIES_TABLE = """
CREATE TABLE IF NOT EXISTS news_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_id INTEGER NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    method TEXT DEFAULT 'simple',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (news_id) REFERENCES messages(id)
);
"""

# 情感分析结果表（预留）
CREATE_SENTIMENT_ANALYSIS_TABLE = """
CREATE TABLE IF NOT EXISTS sentiment_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    news_id INTEGER NOT NULL UNIQUE,
    sentiment_score REAL,
    sentiment_label TEXT,
    confidence REAL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (news_id) REFERENCES messages(id)
);
"""

# ==================== 索引 ====================

# 新闻消息表索引
CREATE_MESSAGES_DATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_messages_date
ON messages(date DESC);
"""

CREATE_MESSAGES_CHANNEL_INDEX = """
CREATE INDEX IF NOT EXISTS idx_messages_channel
ON messages(channel_id, date);
"""

CREATE_MESSAGES_CHANNEL_MESSAGE_UNIQUE_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_channel_message_unique
ON messages(channel_id, message_id);
"""

# HKStocks新闻索引
CREATE_HKSTOCKS_URL_INDEX = """
CREATE INDEX IF NOT EXISTS idx_hkstocks_url
ON hkstocks_news(url);
"""

CREATE_HKSTOCKS_DATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_hkstocks_date
ON hkstocks_news(publish_date DESC);
"""

# 关键词索引
CREATE_NEWS_KEYWORDS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_keyword
ON news_keywords(keyword);
"""

CREATE_NEWS_ID_INDEX = """
CREATE INDEX IF NOT EXISTS idx_news_id
ON news_keywords(news_id);
"""

# 关键词热度趋势索引
CREATE_KEYWORD_TRENDS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_keyword_trends
ON keyword_trends(keyword, date);
"""

# 推送历史索引
CREATE_PUSH_HISTORY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_push_history_sub
ON push_history(subscription_id, news_id);
"""

# 所有表的创建语句列表（按依赖顺序）
ALL_TABLES = [
    # 主表
    CREATE_MESSAGES_TABLE,
    CREATE_HKSTOCKS_NEWS_TABLE,
    CREATE_NEWS_KEYWORDS_TABLE,
    CREATE_KEYWORD_TRENDS_TABLE,
    CREATE_KEYWORD_SYNONYMS_TABLE,
    CREATE_SUBSCRIPTIONS_TABLE,
    CREATE_PUSH_HISTORY_TABLE,
    CREATE_NEWS_SUMMARIES_TABLE,
    CREATE_SENTIMENT_ANALYSIS_TABLE,
    # 索引
    CREATE_MESSAGES_DATE_INDEX,
    CREATE_MESSAGES_CHANNEL_INDEX,
    CREATE_MESSAGES_CHANNEL_MESSAGE_UNIQUE_INDEX,
    CREATE_HKSTOCKS_URL_INDEX,
    CREATE_HKSTOCKS_DATE_INDEX,
    CREATE_NEWS_KEYWORDS_INDEX,
    CREATE_NEWS_ID_INDEX,
    CREATE_KEYWORD_TRENDS_INDEX,
    CREATE_PUSH_HISTORY_INDEX,
]


def init_database(db_manager):
    """
    初始化数据库表结构

    Args:
        db_manager: 数据库管理器实例
    """
    import logging
    logger = logging.getLogger(__name__)

    with db_manager.get_connection() as conn:
        cursor = conn.cursor()
        for sql in ALL_TABLES:
            try:
                cursor.execute(sql)
            except Exception as e:
                # 忽略"表已存在"错误
                if 'already exists' not in str(e).lower():
                    logger.warning(f"Failed to execute SQL: {e}")
        conn.commit()

    logger.info("Database schema initialized successfully")
