"""
数据库连接管理
提供统一的数据库访问接口
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Generator
import logging

from config.settings import settings
from src.core.exceptions import DatabaseException

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = settings.history_db_path_full

        # 确保数据库目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self, db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
        """
        获取数据库连接（上下文管理器）

        Args:
            db_path: 数据库路径，默认使用主数据库

        Yields:
            sqlite3.Connection: 数据库连接对象
        """
        path = db_path or self.db_path
        try:
            conn = sqlite3.connect(str(path))
            conn.row_factory = sqlite3.Row  # 返回字典格式
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise DatabaseException(f"Failed to connect to database: {e}")
        finally:
            conn.close()

    def execute_query(self, query: str, params: Optional[tuple] = None,
                     db_path: Optional[Path] = None) -> list[dict]:
        """
        执行查询SQL

        Args:
            query: SQL查询语句
            params: 查询参数
            db_path: 数据库路径

        Returns:
            查询结果列表

        Raises:
            DatabaseException: 数据库操作失败
        """
        try:
            with self.get_connection(db_path) as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)

                columns = [col[0] for col in cursor.description] if cursor.description else []
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                return results
        except sqlite3.Error as e:
            logger.error(f"Query execution error: {e}, SQL: {query}")
            raise DatabaseException(f"Query failed: {e}")

    def execute_update(self, query: str, params: Optional[tuple] = None,
                      db_path: Optional[Path] = None) -> int:
        """
        执行更新SQL（INSERT/UPDATE/DELETE）

        Args:
            query: SQL语句
            params: 参数
            db_path: 数据库路径

        Returns:
            影响的行数

        Raises:
            DatabaseException: 数据库操作失败
        """
        try:
            with self.get_connection(db_path) as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"Update execution error: {e}, SQL: {query}")
            raise DatabaseException(f"Update failed: {e}")

    def execute_many(self, query: str, params_list: list[tuple],
                    db_path: Optional[Path] = None) -> int:
        """
        批量执行SQL

        Args:
            query: SQL语句
            params_list: 参数列表
            db_path: 数据库路径

        Returns:
            影响的行数

        Raises:
            DatabaseException: 数据库操作失败
        """
        try:
            with self.get_connection(db_path) as conn:
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"Batch execution error: {e}, SQL: {query}")
            raise DatabaseException(f"Batch execution failed: {e}")

    def get_last_insert_id(self, db_path: Optional[Path] = None) -> int:
        """
        获取最后插入的ID

        Args:
            db_path: 数据库路径

        Returns:
            最后插入的行ID
        """
        with self.get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT last_insert_rowid()")
            return cursor.fetchone()[0]

    def table_exists(self, table_name: str, db_path: Optional[Path] = None) -> bool:
        """
        检查表是否存在

        Args:
            table_name: 表名
            db_path: 数据库路径

        Returns:
            表是否存在
        """
        query = """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
        """
        results = self.execute_query(query, (table_name,), db_path)
        return len(results) > 0

    def get_table_columns(self, table_name: str, db_path: Optional[Path] = None) -> list[str]:
        """
        获取表的列名

        Args:
            table_name: 表名
            db_path: 数据库路径

        Returns:
            列名列表
        """
        query = f"PRAGMA table_info({table_name})"
        results = self.execute_query(query, db_path=db_path)
        return [row['name'] for row in results]


# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    获取数据库管理器单例

    Returns:
        DatabaseManager: 数据库管理器实例
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
