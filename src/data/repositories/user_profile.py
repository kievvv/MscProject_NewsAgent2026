"""
User Profile Repository
用户画像的数据访问层
"""
import sqlite3
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from src.core.models import UserProfile
from config.settings import settings

logger = logging.getLogger(__name__)


class UserProfileRepository:
    """用户画像仓储"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(settings.database_path_full)

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_or_create(self, user_id: str) -> UserProfile:
        """
        获取或创建用户画像

        Args:
            user_id: 用户ID

        Returns:
            UserProfile对象
        """
        profile = self.get_by_user_id(user_id)
        if profile:
            return profile

        # 创建新用户画像
        return self.create(user_id)

    def create(self, user_id: str, preferences: Optional[Dict[str, Any]] = None) -> UserProfile:
        """创建用户画像"""
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        preferences_json = json.dumps(preferences) if preferences else None

        try:
            cursor.execute("""
                INSERT INTO user_profiles (user_id, preferences, conversation_count, last_active, created_at)
                VALUES (?, ?, 0, ?, ?)
            """, (user_id, preferences_json, now, now))

            conn.commit()
            profile_id = cursor.lastrowid

            logger.info(f"Created user profile for {user_id}")

            return UserProfile(
                id=profile_id,
                user_id=user_id,
                preferences=preferences,
                conversation_count=0,
                last_active=now,
                created_at=now
            )

        finally:
            conn.close()

    def get_by_user_id(self, user_id: str) -> Optional[UserProfile]:
        """根据用户ID获取画像"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM user_profiles WHERE user_id = ?
            """, (user_id,))

            row = cursor.fetchone()
            if not row:
                return None

            return UserProfile.from_dict(dict(row))

        finally:
            conn.close()

    def update_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> bool:
        """更新用户偏好"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE user_profiles
                SET preferences = ?, last_active = ?
                WHERE user_id = ?
            """, (json.dumps(preferences), datetime.now().isoformat(), user_id))

            conn.commit()
            return cursor.rowcount > 0

        finally:
            conn.close()

    def increment_conversation_count(self, user_id: str) -> bool:
        """增加对话计数"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE user_profiles
                SET conversation_count = conversation_count + 1,
                    last_active = ?
                WHERE user_id = ?
            """, (datetime.now().isoformat(), user_id))

            conn.commit()
            return cursor.rowcount > 0

        finally:
            conn.close()

    def update_last_active(self, user_id: str) -> bool:
        """更新最后活跃时间"""
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE user_profiles
                SET last_active = ?
                WHERE user_id = ?
            """, (datetime.now().isoformat(), user_id))

            conn.commit()
            return cursor.rowcount > 0

        finally:
            conn.close()
