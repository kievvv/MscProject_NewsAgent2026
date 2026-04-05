"""
Telegram爬虫配置
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class TelegramConfig(BaseModel):
    """Telegram配置"""
    api_id: int = Field(..., description="Telegram API ID")
    api_hash: str = Field(..., description="Telegram API Hash")
    channels: List[str] = Field(default_factory=list, description="监听的频道列表")
    session_name: str = Field("news_crawler", description="会话名称")
    phone: Optional[str] = Field(None, description="手机号")

    @property
    def normalized_channels(self) -> List[str]:
        """用于匹配事件的标准化频道名，不带 @。"""
        return [channel.strip().lstrip('@').lower() for channel in self.channels if channel]

    @staticmethod
    def normalize_channel(channel: str) -> str:
        """标准化为带 @ 的展示名。"""
        normalized = (channel or "").strip().lstrip('@').lower()
        return f"@{normalized}" if normalized else ""


class RedisConfig(BaseModel):
    """Redis配置"""
    host: str = Field("localhost", description="Redis主机")
    port: int = Field(6379, description="Redis端口")
    db: int = Field(0, description="Redis数据库")
    password: Optional[str] = Field(None, description="Redis密码")
    queue_name: str = Field("crypto_news_queue", description="队列名称")
