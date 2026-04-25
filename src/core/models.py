"""
核心领域模型
定义系统中的核心数据结构
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class NewsSource(str, Enum):
    """新闻来源枚举"""
    CRYPTO = "crypto"
    HKSTOCKS = "hkstocks"


class SubscriptionStatus(str, Enum):
    """订阅状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class News:
    """新闻模型"""
    id: Optional[int] = None
    source: NewsSource = NewsSource.CRYPTO
    channel_id: Optional[str] = None
    message_id: Optional[int] = None
    title: Optional[str] = None
    text: str = ""
    original_text: Optional[str] = None
    url: Optional[str] = None
    keywords: Optional[str] = None
    currency: Optional[str] = None
    industry: Optional[str] = None
    abstract: Optional[str] = None
    date: Optional[str] = None
    created_at: Optional[str] = None

    @property
    def content(self) -> str:
        """兼容旧代码中的 content 字段访问。"""
        return self.text

    @property
    def summary(self) -> Optional[str]:
        """兼容旧代码中的 summary 字段访问。"""
        return self.abstract

    @property
    def keyword_list(self) -> List[str]:
        """获取关键词列表"""
        if not self.keywords:
            return []
        return [k.strip() for k in self.keywords.split(',') if k.strip()]

    @property
    def currency_list(self) -> List[str]:
        """获取币种/行业列表"""
        field = self.currency if self.source == NewsSource.CRYPTO else self.industry
        if not field:
            return []
        return [c.strip() for c in field.split(',') if c.strip()]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'source': self.source,
            'channel_id': self.channel_id,
            'message_id': self.message_id,
            'title': self.title or (self.text[:80] if self.text else ""),
            'text': self.text,
            'original_text': self.original_text or self.text,
            'url': self.url or '',
            'keywords': self.keywords or '',
            'currency': self.currency or '',
            'industry': self.industry or '',
            'abstract': self.abstract or '',
            'date': self.date,
            'created_at': self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'News':
        """从字典创建"""
        source = data.get('source_type') or data.get('source', 'crypto')
        if isinstance(source, str):
            source = NewsSource.CRYPTO if source == 'crypto' else NewsSource.HKSTOCKS

        return cls(
            id=data.get('id'),
            source=source,
            channel_id=data.get('channel_id'),
            message_id=data.get('message_id'),
            title=data.get('title'),
            text=data.get('text', ''),
            original_text=data.get('original_text'),
            url=data.get('url'),
            keywords=data.get('keywords'),
            currency=data.get('currency'),
            industry=data.get('industry'),
            abstract=data.get('abstract') or data.get('summary'),
            date=data.get('date') or data.get('publish_date'),
            created_at=data.get('created_at'),
        )


@dataclass
class Keyword:
    """关键词模型"""
    id: Optional[int] = None
    news_id: int = 0
    keyword: str = ""
    weight: float = 0.0
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'news_id': self.news_id,
            'keyword': self.keyword,
            'weight': self.weight,
            'created_at': self.created_at,
        }


@dataclass
class KeywordTrend:
    """关键词热度趋势"""
    id: Optional[int] = None
    keyword: str = ""
    date: str = ""
    count: int = 0
    total_weight: float = 0.0
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'keyword': self.keyword,
            'date': self.date,
            'count': self.count,
            'total_weight': self.total_weight,
            'updated_at': self.updated_at,
        }


@dataclass
class Subscription:
    """订阅模型"""
    id: Optional[int] = None
    user_id: str = ""
    keyword: str = ""
    telegram_chat_id: Optional[str] = None
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    created_at: Optional[str] = None

    @property
    def is_active(self) -> bool:
        return self.status == SubscriptionStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'keyword': self.keyword,
            'telegram_chat_id': self.telegram_chat_id,
            'status': self.status,
            'is_active': self.is_active,
            'created_at': self.created_at,
        }


@dataclass
class PushHistory:
    """推送历史"""
    id: Optional[int] = None
    subscription_id: int = 0
    news_id: int = 0
    status: str = "success"
    pushed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'subscription_id': self.subscription_id,
            'news_id': self.news_id,
            'status': self.status,
            'pushed_at': self.pushed_at,
        }


@dataclass
class TrendAnalysis:
    """趋势分析结果"""
    keyword: str
    total_count: int
    active_days: int
    date_range: tuple[str, str]
    daily_trend: List[Dict[str, Any]] = field(default_factory=list)
    avg_daily_count: float = 0.0
    peak_date: Optional[str] = None
    peak_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'keyword': self.keyword,
            'total_count': self.total_count,
            'active_days': self.active_days,
            'date_range': list(self.date_range),
            'daily_trend': self.daily_trend,
            'avg_daily_count': self.avg_daily_count,
            'peak_date': self.peak_date,
            'peak_count': self.peak_count,
        }


@dataclass
class SearchResult:
    """搜索结果"""
    news: News
    similarity_score: Optional[float] = None
    rank: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        result = self.news.to_dict()
        if self.similarity_score is not None:
            result['similarity_score'] = self.similarity_score
        if self.rank is not None:
            result['rank'] = self.rank
        return result


# ==================== AI Agent Models ====================


@dataclass
class Conversation:
    """对话模型"""
    id: Optional[int] = None
    user_id: str = ""
    title: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'metadata': self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        import json
        metadata = data.get('metadata')
        if isinstance(metadata, str):
            metadata = json.loads(metadata) if metadata else None
        return cls(
            id=data.get('id'),
            user_id=data.get('user_id', ''),
            title=data.get('title'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            metadata=metadata,
        )


@dataclass
class Message:
    """消息模型"""
    id: Optional[int] = None
    conversation_id: int = 0
    role: str = "user"  # user, assistant, system
    content: str = ""
    agent_name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'agent_name': self.agent_name,
            'tool_calls': self.tool_calls or [],
            'created_at': self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        import json
        tool_calls = data.get('tool_calls')
        if isinstance(tool_calls, str):
            tool_calls = json.loads(tool_calls) if tool_calls else None
        return cls(
            id=data.get('id'),
            conversation_id=data.get('conversation_id', 0),
            role=data.get('role', 'user'),
            content=data.get('content', ''),
            agent_name=data.get('agent_name'),
            tool_calls=tool_calls,
            created_at=data.get('created_at'),
        )


@dataclass
class UserProfile:
    """用户画像模型"""
    id: Optional[int] = None
    user_id: str = ""
    preferences: Optional[Dict[str, Any]] = None
    conversation_count: int = 0
    last_active: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'preferences': self.preferences or {},
            'conversation_count': self.conversation_count,
            'last_active': self.last_active,
            'created_at': self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        import json
        preferences = data.get('preferences')
        if isinstance(preferences, str):
            preferences = json.loads(preferences) if preferences else None
        return cls(
            id=data.get('id'),
            user_id=data.get('user_id', ''),
            preferences=preferences,
            conversation_count=data.get('conversation_count', 0),
            last_active=data.get('last_active'),
            created_at=data.get('created_at'),
        )


@dataclass
class TaskIntent:
    """任务意图模型"""
    task_type: str = "chat"
    time_window: str = "24h"
    focus_assets: List[str] = field(default_factory=list)
    focus_themes: List[str] = field(default_factory=list)
    risk_mode: Optional[str] = None
    output_format: str = "brief"
    query: Optional[str] = None
    topic: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_type': self.task_type,
            'time_window': self.time_window,
            'focus_assets': self.focus_assets,
            'focus_themes': self.focus_themes,
            'risk_mode': self.risk_mode,
            'output_format': self.output_format,
            'query': self.query,
            'topic': self.topic,
        }


@dataclass
class AgentResultBlock:
    """Agent结构化结果块"""
    block_type: str
    title: str
    summary: str
    data: Any = None
    key_points: List[str] = field(default_factory=list)
    risk_notes: List[str] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)
    evidence_news_ids: List[int] = field(default_factory=list)
    source_labels: List[str] = field(default_factory=list)
    tool_trace_refs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'block_type': self.block_type,
            'title': self.title,
            'summary': self.summary,
            'data': self.data,
            'key_points': self.key_points,
            'risk_notes': self.risk_notes,
            'next_actions': self.next_actions,
            'evidence_news_ids': self.evidence_news_ids,
            'source_labels': self.source_labels,
            'tool_trace_refs': self.tool_trace_refs,
        }


@dataclass
class PersonalizedReport:
    """个性化报告结构"""
    title: str
    summary: str
    key_points: List[str] = field(default_factory=list)
    risk_notes: List[str] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)
    evidence_news_ids: List[int] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'summary': self.summary,
            'key_points': self.key_points,
            'risk_notes': self.risk_notes,
            'next_actions': self.next_actions,
            'evidence_news_ids': self.evidence_news_ids,
            'metadata': self.metadata,
        }


@dataclass
class AgentSkill:
    """Agent技能模型"""
    id: Optional[int] = None
    name: str = ""
    description: Optional[str] = None
    skill_type: str = "workflow"  # workflow, analysis, discovery
    prompt_template: Optional[str] = None
    tool_sequence: Optional[str] = None
    enabled: bool = True
    execution_count: int = 0
    created_at: Optional[str] = None

    @property
    def tool_list(self) -> List[str]:
        """获取工具列表"""
        if not self.tool_sequence:
            return []
        return [t.strip() for t in self.tool_sequence.split(',') if t.strip()]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'skill_type': self.skill_type,
            'prompt_template': self.prompt_template,
            'tool_sequence': self.tool_sequence,
            'tool_list': self.tool_list,
            'enabled': self.enabled,
            'execution_count': self.execution_count,
            'created_at': self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentSkill':
        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            description=data.get('description'),
            skill_type=data.get('skill_type', 'workflow'),
            prompt_template=data.get('prompt_template'),
            tool_sequence=data.get('tool_sequence'),
            enabled=bool(data.get('enabled', True)),
            execution_count=data.get('execution_count', 0),
            created_at=data.get('created_at'),
        )
