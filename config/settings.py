"""
统一配置管理
使用 pydantic-settings 进行类型安全的配置管理
"""
import os
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # ==================== 项目路径 ====================
    PROJECT_ROOT: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    DATA_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data")
    LOGS_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "logs")

    # ==================== 数据库配置 ====================
    DATABASE_PATH: str = Field(default="data/databases/news_analysis.db")
    HISTORY_DB_PATH: str = Field(default="testdb_history.db")
    CRYPTO_DB_PATH: str = Field(default="testdb_cryptonews.db")

    # ==================== Redis 配置 ====================
    REDIS_HOST: str = Field(default="127.0.0.1")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_STREAM_KEY: str = Field(default="news_stream")
    REDIS_CONSUMER_GROUP: str = Field(default="news_consumers")
    REDIS_MAX_LEN: int = Field(default=1000)

    # ==================== Telegram 配置 ====================
    TELEGRAM_SESSION: str = Field(default="tg_session")
    TELEGRAM_API_ID: int = Field(default=21418731)
    TELEGRAM_API_HASH: str = Field(default="388599319fac7e16bff0d202c9282cc8")
    TELEGRAM_PHONE: Optional[str] = Field(default=None)
    TELEGRAM_CHANNELS: List[str] = Field(
        default=[
            "@theblockbeats",
            "@news6551",
            "@MMSnews",
            "@TechFlowDaily"
        ]
    )
    TELEGRAM_BACKFILL_LIMIT: int = Field(default=500)

    # ==================== Crypto 启动采集配置 ====================
    AUTO_START_CRYPTO_CRAWLER: bool = Field(default=True)
    CRYPTO_STARTUP_BACKFILL_LIMIT: int = Field(default=2000)
    CRYPTO_BACKFILL_STALE_HOURS: int = Field(default=24)
    CRYPTO_STARTUP_NLP_MODE: str = Field(default="keywords")
    CRYPTO_REQUIRE_REDIS: bool = Field(default=True)

    # Telegram 代理配置
    TELEGRAM_PROXY_ENABLED: bool = Field(default=False)
    TELEGRAM_PROXY_TYPE: str = Field(default="http")
    TELEGRAM_PROXY_HOST: str = Field(default="127.0.0.1")
    TELEGRAM_PROXY_PORT: int = Field(default=7890)

    # ==================== AI 模型配置 ====================
    # KeyBERT 模型
    KEYBERT_MODEL: str = Field(default="paraphrase-multilingual-MiniLM-L12-v2")
    TOP_N_KEYWORDS: int = Field(default=10)
    KEYWORD_NGRAM_RANGE: tuple = Field(default=(1, 2))

    # spaCy 模型
    SPACY_MODEL: str = Field(default="zh_core_web_sm")
    SPACY_SIMILARITY_MODEL: str = Field(default="zh_core_web_md")

    # 摘要模型
    SUMMARY_MODEL: str = Field(default="facebook/bart-large-cnn")

    # Hugging Face 端点。为空时保持库默认行为；如需镜像可显式配置。
    HF_ENDPOINT: str = Field(default="")
    HF_ALLOW_REMOTE_DOWNLOADS: bool = Field(default=False)

    # ==================== 热度分析配置 ====================
    TREND_CACHE_HOURS: int = Field(default=1)
    SIMILARITY_THRESHOLD: float = Field(default=0.7)

    # ==================== Telegram Bot 推送配置 ====================
    TELEGRAM_BOT_TOKEN: str = Field(default="YOUR_BOT_TOKEN_HERE")
    PUSH_CHECK_INTERVAL: int = Field(default=300)
    MAX_PUSH_PER_USER: int = Field(default=50)

    # ==================== API 配置 ====================
    DEBUG: bool = Field(default=True)
    API_HOST: str = Field(default="127.0.0.1")
    API_PORT: int = Field(default=8000)
    API_DEBUG: bool = Field(default=True)
    API_RELOAD: bool = Field(default=True)

    # ==================== 日志配置 ====================
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # ==================== 可视化配置 ====================
    PLOT_STYLE: str = Field(default="seaborn-v0_8-darkgrid")
    PLOT_DPI: int = Field(default=100)
    PLOT_FIGSIZE: tuple = Field(default=(12, 6))

    # ==================== 港股爬虫配置 ====================
    HKSTOCKS_SOURCE_ID: str = Field(default="aastocks")
    HKSTOCKS_BASE_URL: str = Field(
        default="http://www.aastocks.com/tc/stocks/news/aafn"
    )
    HKSTOCKS_REQUEST_TIMEOUT: int = Field(default=30)
    HKSTOCKS_REQUEST_DELAY: float = Field(default=0.5)
    HKSTOCKS_HEADERS: Dict[str, str] = Field(
        default={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
    )

    # ==================== Dify 配置（预留） ====================
    DIFY_API_KEY: Optional[str] = Field(default=None)
    DIFY_BASE_URL: Optional[str] = Field(default="http://localhost/v1")

    # ==================== AI Agent 配置 ====================
    # Agent 开关
    AGENT_ENABLED: bool = Field(default=True)

    # LLM Provider 配置
    DEFAULT_LLM_PROVIDER: str = Field(default="ollama")  # ollama, openai, anthropic

    # Ollama 配置
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="llama3.1:latest")

    # OpenAI 配置
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_MODEL: str = Field(default="gpt-4-turbo-preview")
    OPENAI_BASE_URL: Optional[str] = Field(default=None)

    # Anthropic 配置
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    ANTHROPIC_MODEL: str = Field(default="claude-3-5-sonnet-20241022")

    # Agent 行为配置
    AGENT_MAX_ITERATIONS: int = Field(default=10)
    AGENT_TEMPERATURE: float = Field(default=0.7)
    AGENT_MAX_TOKENS: int = Field(default=2000)
    AGENT_TIMEOUT: int = Field(default=60)

    # Conversation 配置
    CONVERSATION_HISTORY_LIMIT: int = Field(default=20)
    CONVERSATION_MAX_AGE_DAYS: int = Field(default=30)

    # Skill 配置
    SKILL_EXECUTION_TIMEOUT: int = Field(default=120)
    SKILL_CACHE_ENABLED: bool = Field(default=True)
    SKILL_CACHE_TTL: int = Field(default=3600)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 仅在显式配置时覆盖 HF 端点，避免镜像不可用时阻断本地缓存加载。
        if self.HF_ENDPOINT:
            os.environ['HF_ENDPOINT'] = self.HF_ENDPOINT
        else:
            os.environ.pop('HF_ENDPOINT', None)
        # 创建必要的目录
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / "databases").mkdir(parents=True, exist_ok=True)
        (self.DATA_DIR / "models").mkdir(parents=True, exist_ok=True)

    @property
    def database_path_full(self) -> Path:
        """获取完整的数据库路径"""
        if Path(self.DATABASE_PATH).is_absolute():
            return Path(self.DATABASE_PATH)
        return self.PROJECT_ROOT / self.DATABASE_PATH

    @property
    def history_db_path_full(self) -> Path:
        """获取历史数据库完整路径"""
        if Path(self.HISTORY_DB_PATH).is_absolute():
            return Path(self.HISTORY_DB_PATH)
        return self.PROJECT_ROOT / self.HISTORY_DB_PATH

    @property
    def crypto_db_path_full(self) -> Path:
        """获取加密货币数据库完整路径"""
        if Path(self.CRYPTO_DB_PATH).is_absolute():
            return Path(self.CRYPTO_DB_PATH)
        return self.PROJECT_ROOT / self.CRYPTO_DB_PATH

    @property
    def log_file_path(self) -> Path:
        """获取日志文件路径"""
        return self.LOGS_DIR / "app.log"

    def get_telegram_config(self) -> dict:
        """获取 Telegram 配置"""
        return {
            "session": self.TELEGRAM_SESSION,
            "api_id": self.TELEGRAM_API_ID,
            "api_hash": self.TELEGRAM_API_HASH,
            "channels": self.TELEGRAM_CHANNELS.copy(),
            "backfill_limit": self.TELEGRAM_BACKFILL_LIMIT,
            "proxy": {
                "enabled": self.TELEGRAM_PROXY_ENABLED,
                "type": self.TELEGRAM_PROXY_TYPE,
                "host": self.TELEGRAM_PROXY_HOST,
                "port": self.TELEGRAM_PROXY_PORT,
            }
        }

    def get_redis_config(self) -> dict:
        """获取 Redis 配置"""
        return {
            "host": self.REDIS_HOST,
            "port": self.REDIS_PORT,
            "stream_key": self.REDIS_STREAM_KEY,
            "consumer_group": self.REDIS_CONSUMER_GROUP,
            "max_len": self.REDIS_MAX_LEN,
        }

    def get_llm_config(self) -> dict:
        """获取 LLM 配置"""
        config = {
            "provider": self.DEFAULT_LLM_PROVIDER,
            "temperature": self.AGENT_TEMPERATURE,
            "max_tokens": self.AGENT_MAX_TOKENS,
            "timeout": self.AGENT_TIMEOUT,
        }

        if self.DEFAULT_LLM_PROVIDER == "ollama":
            config.update({
                "base_url": self.OLLAMA_BASE_URL,
                "model": self.OLLAMA_MODEL,
            })
        elif self.DEFAULT_LLM_PROVIDER == "openai":
            config.update({
                "api_key": self.OPENAI_API_KEY,
                "model": self.OPENAI_MODEL,
                "base_url": self.OPENAI_BASE_URL,
            })
        elif self.DEFAULT_LLM_PROVIDER == "anthropic":
            config.update({
                "api_key": self.ANTHROPIC_API_KEY,
                "model": self.ANTHROPIC_MODEL,
            })

        return config

    def get_agent_config(self) -> dict:
        """获取 Agent 配置"""
        return {
            "enabled": self.AGENT_ENABLED,
            "max_iterations": self.AGENT_MAX_ITERATIONS,
            "conversation_history_limit": self.CONVERSATION_HISTORY_LIMIT,
            "conversation_max_age_days": self.CONVERSATION_MAX_AGE_DAYS,
            "skill_execution_timeout": self.SKILL_EXECUTION_TIMEOUT,
            "skill_cache_enabled": self.SKILL_CACHE_ENABLED,
            "skill_cache_ttl": self.SKILL_CACHE_TTL,
        }


# 全局配置实例
settings = Settings()


# 向后兼容的常量导出（供旧代码使用）
PROJECT_ROOT = settings.PROJECT_ROOT
DATA_DIR = settings.DATA_DIR
LOGS_DIR = settings.LOGS_DIR
DATABASE_PATH = str(settings.database_path_full)
HISTORY_DB_PATH = str(settings.history_db_path_full)
CRYPTO_DB_PATH = str(settings.crypto_db_path_full)
KEYBERT_MODEL = settings.KEYBERT_MODEL
TOP_N_KEYWORDS = settings.TOP_N_KEYWORDS
KEYWORD_NGRAM_RANGE = settings.KEYWORD_NGRAM_RANGE
SIMILARITY_THRESHOLD = settings.SIMILARITY_THRESHOLD
API_HOST = settings.API_HOST
API_PORT = settings.API_PORT
API_DEBUG = settings.API_DEBUG
TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
PLOT_STYLE = settings.PLOT_STYLE
PLOT_DPI = settings.PLOT_DPI
PLOT_FIGSIZE = settings.PLOT_FIGSIZE
