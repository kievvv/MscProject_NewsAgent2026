"""
基础仓储类
实现通用的CRUD操作
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TypeVar, Generic
from pathlib import Path

from src.data.database import DatabaseManager, get_db_manager
from src.core.exceptions import DatabaseException, NotFoundException

# 泛型类型变量
T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    基础仓储类
    提供通用的数据访问方法
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None,
                 db_path: Optional[Path] = None):
        """
        初始化仓储

        Args:
            db_manager: 数据库管理器
            db_path: 数据库路径
        """
        self.db_manager = db_manager or get_db_manager()
        self.db_path = db_path

    @property
    @abstractmethod
    def table_name(self) -> str:
        """表名"""
        pass

    @abstractmethod
    def _row_to_model(self, row: Dict[str, Any]) -> T:
        """
        将数据库行转换为模型对象

        Args:
            row: 数据库行

        Returns:
            模型对象
        """
        pass

    @abstractmethod
    def _model_to_row(self, model: T) -> Dict[str, Any]:
        """
        将模型对象转换为数据库行

        Args:
            model: 模型对象

        Returns:
            数据库行字典
        """
        pass

    def get_by_id(self, id: int) -> Optional[T]:
        """
        根据ID获取记录

        Args:
            id: 记录ID

        Returns:
            模型对象或None
        """
        query = f"SELECT * FROM {self.table_name} WHERE id = ?"
        results = self.db_manager.execute_query(query, (id,), self.db_path)
        if results:
            return self._row_to_model(results[0])
        return None

    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """
        获取所有记录

        Args:
            limit: 限制数量
            offset: 偏移量

        Returns:
            模型对象列表
        """
        query = f"SELECT * FROM {self.table_name}"
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"

        results = self.db_manager.execute_query(query, db_path=self.db_path)
        return [self._row_to_model(row) for row in results]

    def create(self, model: T) -> T:
        """
        创建新记录

        Args:
            model: 模型对象

        Returns:
            创建后的模型对象（包含ID）

        Raises:
            DatabaseException: 创建失败
        """
        row = self._model_to_row(model)
        # 移除id字段（如果存在）
        row.pop('id', None)

        columns = ', '.join(row.keys())
        placeholders = ', '.join(['?' for _ in row])
        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"

        self.db_manager.execute_update(query, tuple(row.values()), self.db_path)
        new_id = self.db_manager.get_last_insert_id(self.db_path)

        return self.get_by_id(new_id)

    def update(self, id: int, model: T) -> Optional[T]:
        """
        更新记录

        Args:
            id: 记录ID
            model: 新的模型对象

        Returns:
            更新后的模型对象或None

        Raises:
            NotFoundException: 记录不存在
            DatabaseException: 更新失败
        """
        if not self.exists(id):
            raise NotFoundException(f"Record with id {id} not found in {self.table_name}")

        row = self._model_to_row(model)
        row.pop('id', None)  # 移除id字段

        set_clause = ', '.join([f"{k} = ?" for k in row.keys()])
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?"

        params = list(row.values()) + [id]
        self.db_manager.execute_update(query, tuple(params), self.db_path)

        return self.get_by_id(id)

    def delete(self, id: int) -> bool:
        """
        删除记录

        Args:
            id: 记录ID

        Returns:
            是否删除成功
        """
        query = f"DELETE FROM {self.table_name} WHERE id = ?"
        affected = self.db_manager.execute_update(query, (id,), self.db_path)
        return affected > 0

    def exists(self, id: int) -> bool:
        """
        检查记录是否存在

        Args:
            id: 记录ID

        Returns:
            是否存在
        """
        query = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE id = ?"
        results = self.db_manager.execute_query(query, (id,), self.db_path)
        return results[0]['count'] > 0 if results else False

    def count(self, where_clause: str = "", params: Optional[tuple] = None) -> int:
        """
        统计记录数

        Args:
            where_clause: WHERE子句（不包含WHERE关键字）
            params: 查询参数

        Returns:
            记录数
        """
        query = f"SELECT COUNT(*) as count FROM {self.table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"

        results = self.db_manager.execute_query(query, params, self.db_path)
        return results[0]['count'] if results else 0

    def find(self, where_clause: str, params: Optional[tuple] = None,
             order_by: str = "", limit: Optional[int] = None) -> List[T]:
        """
        按条件查询

        Args:
            where_clause: WHERE子句（不包含WHERE关键字）
            params: 查询参数
            order_by: 排序子句（不包含ORDER BY关键字）
            limit: 限制数量

        Returns:
            模型对象列表
        """
        query = f"SELECT * FROM {self.table_name} WHERE {where_clause}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit}"

        results = self.db_manager.execute_query(query, params, self.db_path)
        return [self._row_to_model(row) for row in results]

    def find_one(self, where_clause: str, params: Optional[tuple] = None) -> Optional[T]:
        """
        查询单条记录

        Args:
            where_clause: WHERE子句
            params: 查询参数

        Returns:
            模型对象或None
        """
        results = self.find(where_clause, params, limit=1)
        return results[0] if results else None
