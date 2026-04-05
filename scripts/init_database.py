"""
数据库初始化脚本
创建所有必要的表结构
"""
import sqlite3
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings


def create_crypto_tables(conn: sqlite3.Connection):
    """创建Crypto数据库表"""
    cursor = conn.cursor()

    # messages表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            message_id INTEGER,
            text TEXT NOT NULL,
            url TEXT,
            date TEXT NOT NULL,
            keywords TEXT,
            summary TEXT,
            abstract TEXT,
            currency TEXT,
            original_text TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    cursor.execute("UPDATE messages SET abstract = COALESCE(abstract, summary) WHERE summary IS NOT NULL")
    cursor.execute("""
        DELETE FROM messages
        WHERE id NOT IN (
            SELECT MIN(id) FROM messages
            WHERE channel_id IS NOT NULL AND message_id IS NOT NULL
            GROUP BY channel_id, message_id
        )
        AND channel_id IS NOT NULL AND message_id IS NOT NULL
    """)
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_channel_message_unique ON messages(channel_id, message_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_channel_date ON messages(channel_id, date DESC)")

    # news_keywords表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id INTEGER NOT NULL,
            keyword TEXT NOT NULL,
            weight REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (news_id) REFERENCES messages(id),
            UNIQUE(news_id, keyword)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_keyword ON news_keywords(keyword)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_id ON news_keywords(news_id)")

    # keyword_trends表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keyword_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            date TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            total_weight REAL DEFAULT 0.0,
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(keyword, date)
        )
    """)

    # keyword_synonyms表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keyword_synonyms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            representative_keyword TEXT NOT NULL,
            similarity REAL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(keyword, representative_keyword)
        )
    """)

    # subscriptions表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            keyword TEXT NOT NULL,
            push_channel TEXT DEFAULT 'telegram',
            telegram_chat_id TEXT,
            wechat_id TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, keyword)
        )
    """)

    # push_history表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS push_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER NOT NULL,
            news_id INTEGER NOT NULL,
            pushed_at TEXT DEFAULT (datetime('now')),
            status TEXT,
            FOREIGN KEY (subscription_id) REFERENCES subscriptions(id),
            FOREIGN KEY (news_id) REFERENCES messages(id)
        )
    """)

    conn.commit()
    print("✅ Crypto tables created")


def create_hkstocks_tables(conn: sqlite3.Connection):
    """创建HKStocks数据库表"""
    cursor = conn.cursor()

    # hkstocks_news表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hkstocks_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            publish_date TEXT NOT NULL,
            source TEXT,
            url TEXT,
            keywords TEXT,
            summary TEXT,
            industry TEXT,
            stock_code TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hk_date ON hkstocks_news(publish_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hk_stock_code ON hkstocks_news(stock_code)")

    # news_keywords表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id INTEGER NOT NULL,
            keyword TEXT NOT NULL,
            weight REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (news_id) REFERENCES hkstocks_news(id),
            UNIQUE(news_id, keyword)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_keyword ON news_keywords(keyword)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_id ON news_keywords(news_id)")

    # keyword_trends表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keyword_trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            date TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            total_weight REAL DEFAULT 0.0,
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(keyword, date)
        )
    """)

    conn.commit()
    print("✅ HKStocks tables created")


def main():
    """主函数"""
    print("=" * 60)
    print("数据库初始化")
    print("=" * 60)

    # 创建Crypto数据库
    crypto_db_path = settings.crypto_db_path_full
    crypto_db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n初始化 Crypto 数据库: {crypto_db_path}")
    conn = sqlite3.connect(str(crypto_db_path))
    create_crypto_tables(conn)
    conn.close()

    # 创建HKStocks数据库
    history_db_path = settings.history_db_path_full
    history_db_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n初始化 HKStocks 数据库: {history_db_path}")
    conn = sqlite3.connect(str(history_db_path))
    create_hkstocks_tables(conn)
    conn.close()

    print("\n" + "=" * 60)
    print("数据库初始化完成！")
    print("=" * 60)
    print(f"Crypto DB: {crypto_db_path}")
    print(f"HKStocks DB: {history_db_path}")


if __name__ == "__main__":
    main()
