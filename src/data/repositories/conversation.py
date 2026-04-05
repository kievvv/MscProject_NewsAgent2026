"""
Conversation Repository
对话会话和消息的数据访问层
"""
import sqlite3
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.core.models import Conversation, Message
from config.settings import settings

logger = logging.getLogger(__name__)


class ConversationRepository:
    """对话仓储"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(settings.database_path_full)

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        创建新对话

        Args:
            user_id: 用户ID
            title: 对话标题
            metadata: 元数据

        Returns:
            Conversation对象
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None

        try:
            cursor.execute("""
                INSERT INTO conversations (user_id, title, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, title, now, now, metadata_json))

            conn.commit()
            conversation_id = cursor.lastrowid

            logger.info(f"Created conversation {conversation_id} for user {user_id}")

            return Conversation(
                id=conversation_id,
                user_id=user_id,
                title=title,
                created_at=now,
                updated_at=now,
                metadata=metadata
            )

        finally:
            conn.close()

    def get_by_id(self, conversation_id: int) -> Optional[Conversation]:
        """根据ID获取对话"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM conversations WHERE id = ?
            """, (conversation_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return Conversation.from_dict(dict(row))

        finally:
            conn.close()

    def get_by_user(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Conversation]:
        """
        获取用户的对话列表

        Args:
            user_id: 用户ID
            limit: 限制数量
            offset: 偏移量

        Returns:
            对话列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM conversations
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """, (user_id, limit, offset))

            rows = cursor.fetchall()
            return [Conversation.from_dict(dict(row)) for row in rows]

        finally:
            conn.close()

    def update_conversation_title(self, conversation_id: int, title: str) -> bool:
        """更新对话标题"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE conversations
                SET title = ?, updated_at = ?
                WHERE id = ?
            """, (title, datetime.now().isoformat(), conversation_id))

            conn.commit()
            return cursor.rowcount > 0

        finally:
            conn.close()

    def delete_conversation(self, conversation_id: int) -> bool:
        """删除对话（级联删除消息）"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            conn.commit()
            return cursor.rowcount > 0

        finally:
            conn.close()

    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        agent_name: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> Message:
        """
        添加消息到对话

        Args:
            conversation_id: 对话ID
            role: 角色 (user/assistant/system)
            content: 消息内容
            agent_name: Agent名称
            tool_calls: 工具调用记录

        Returns:
            Message对象
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        tool_calls_json = json.dumps(tool_calls) if tool_calls else None

        try:
            cursor.execute("""
                INSERT INTO messages (conversation_id, role, content, agent_name, tool_calls, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (conversation_id, role, content, agent_name, tool_calls_json, now))

            conn.commit()
            message_id = cursor.lastrowid

            # 更新对话的updated_at
            cursor.execute("""
                UPDATE conversations SET updated_at = ? WHERE id = ?
            """, (now, conversation_id))
            conn.commit()

            return Message(
                id=message_id,
                conversation_id=conversation_id,
                role=role,
                content=content,
                agent_name=agent_name,
                tool_calls=tool_calls,
                created_at=now
            )

        finally:
            conn.close()

    def get_messages(
        self,
        conversation_id: int,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        获取对话的消息列表

        Args:
            conversation_id: 对话ID
            limit: 限制数量（从最新开始）

        Returns:
            消息列表（按时间正序）
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            if limit:
                # 获取最近N条消息
                cursor.execute("""
                    SELECT * FROM messages
                    WHERE conversation_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (conversation_id, limit))
                rows = cursor.fetchall()
                # 反转顺序，使其按时间正序
                rows = list(reversed(rows))
            else:
                # 获取所有消息
                cursor.execute("""
                    SELECT * FROM messages
                    WHERE conversation_id = ?
                    ORDER BY created_at ASC
                """, (conversation_id,))
                rows = cursor.fetchall()

            return [Message.from_dict(dict(row)) for row in rows]

        finally:
            conn.close()

    def get_message_count(self, conversation_id: int) -> int:
        """获取对话的消息数量"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT COUNT(*) FROM messages WHERE conversation_id = ?
            """, (conversation_id,))

            return cursor.fetchone()[0]

        finally:
            conn.close()
