"""
API请求和响应模型
使用Pydantic定义数据结构
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from src.core.models import NewsSource


# ============= 通用响应模型 =============

class Response(BaseModel):
    """通用响应模型"""
    success: bool = Field(..., description="是否成功")
    message: Optional[str] = Field(None, description="消息")
    data: Optional[Any] = Field(None, description="数据")


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    success: bool = True
    data: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============= 新闻相关模型 =============

class NewsBase(BaseModel):
    """新闻基础模型"""
    title: Optional[str] = Field(None, description="标题")
    content: str = Field(..., description="内容")
    date: Optional[str] = Field(None, description="日期")
    summary: Optional[str] = Field(None, description="摘要")
    keywords: Optional[str] = Field(None, description="关键词")


class NewsCreate(NewsBase):
    """创建新闻请求"""
    channel_id: Optional[str] = Field(None, description="频道ID（Crypto）")
    message_id: Optional[str] = Field(None, description="消息ID（Crypto）")
    currency: Optional[str] = Field(None, description="币种（Crypto）")
    industry: Optional[str] = Field(None, description="行业（HKStocks）")
    stock_code: Optional[str] = Field(None, description="股票代码（HKStocks）")


class NewsUpdate(BaseModel):
    """更新新闻请求"""
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    keywords: Optional[str] = None
    currency: Optional[str] = None
    industry: Optional[str] = None


class NewsResponse(NewsBase):
    """新闻响应"""
    id: int
    channel_id: Optional[str] = None
    message_id: Optional[int] = None
    currency: Optional[str] = None
    industry: Optional[str] = None
    stock_code: Optional[str] = None
    url: Optional[str] = None
    original_text: Optional[str] = None
    source_type: Optional[str] = None

    class Config:
        from_attributes = True


class BatchGenerateRequest(BaseModel):
    """批量生成请求"""
    news_ids: Optional[List[str]] = Field(None, description="新闻ID列表（None则处理所有）")
    force: bool = Field(False, description="是否强制重新生成")
    limit: Optional[int] = Field(None, description="限制处理数量")


# ============= 搜索相关模型 =============

class SearchRequest(BaseModel):
    """搜索请求"""
    keyword: Optional[str] = Field(None, description="关键词")
    keywords: Optional[List[str]] = Field(None, description="关键词列表")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    channel_ids: Optional[List[str]] = Field(None, description="频道ID列表")
    currencies: Optional[List[str]] = Field(None, description="币种列表")
    industries: Optional[List[str]] = Field(None, description="行业列表")
    has_summary: Optional[bool] = Field(None, description="是否有摘要")
    exact: bool = Field(False, description="是否精确匹配")
    limit: Optional[int] = Field(100, description="限制返回数量")


class SimilaritySearchRequest(BaseModel):
    """相似度搜索请求"""
    keyword: str = Field(..., description="关键词")
    top_n: int = Field(10, description="返回前N个相似词")
    min_similarity: float = Field(0.5, description="最小相似度阈值")


class SearchRankRequest(BaseModel):
    """搜索排序请求"""
    query: str = Field(..., description="查询字符串")
    top_n: int = Field(20, description="返回前N条")
    use_similarity: bool = Field(True, description="是否使用相似度搜索")


# ============= 趋势相关模型 =============

class TrendAnalysisRequest(BaseModel):
    """趋势分析请求"""
    keyword: str = Field(..., description="关键词")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    granularity: str = Field("day", description="时间粒度（day/week/month）")


class CompareKeywordsRequest(BaseModel):
    """关键词对比请求"""
    keywords: List[str] = Field(..., description="关键词列表")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")


class AnomalyDetectionRequest(BaseModel):
    """异常检测请求"""
    keyword: str = Field(..., description="关键词")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    sensitivity: float = Field(2.0, description="敏感度")


class CorrelationAnalysisRequest(BaseModel):
    """关联分析请求"""
    keyword1: str = Field(..., description="关键词1")
    keyword2: str = Field(..., description="关键词2")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")


class TrendPredictionRequest(BaseModel):
    """趋势预测请求"""
    keyword: str = Field(..., description="关键词")
    days: int = Field(7, description="预测未来N天")


class TrendingKeywordsRequest(BaseModel):
    """热门关键词请求"""
    days: int = Field(7, description="统计最近N天")
    top_n: int = Field(10, description="返回前N个")
    min_count: int = Field(5, description="最小出现次数")


# ============= 推送相关模型 =============

class SubscribeRequest(BaseModel):
    """订阅请求"""
    user_id: str = Field(..., description="用户ID")
    keyword: str = Field(..., description="关键词")
    options: Optional[Dict[str, Any]] = Field(None, description="其他选项")


class UnsubscribeRequest(BaseModel):
    """取消订阅请求"""
    subscription_id: str = Field(..., description="订阅ID")


class AnomalyAlertRequest(BaseModel):
    """异常告警请求"""
    keywords: Optional[List[str]] = Field(None, description="关键词列表")
    sensitivity: float = Field(2.0, description="敏感度")


class CustomAlertRequest(BaseModel):
    """自定义告警请求"""
    user_id: str = Field(..., description="用户ID")
    alert_type: str = Field(..., description="告警类型")
    conditions: Dict[str, Any] = Field(..., description="条件字典")


class BatchPushRequest(BaseModel):
    """批量推送请求"""
    user_ids: List[str] = Field(..., description="用户ID列表")
    news_id: str = Field(..., description="新闻ID")
    message: Optional[str] = Field(None, description="推送消息")


# ============= 市场相关模型 =============

class PriceRequest(BaseModel):
    """价格查询请求"""
    symbol: str = Field(..., description="交易对符号")
    currency: str = Field("USD", description="计价货币")


class HistoricalPriceRequest(BaseModel):
    """历史价格请求"""
    symbol: str = Field(..., description="交易对符号")
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    currency: str = Field("USD", description="计价货币")


class PriceChangeRequest(BaseModel):
    """价格变化请求"""
    symbol: str = Field(..., description="交易对符号")
    days: int = Field(7, description="统计天数")


class CorrelationRequest(BaseModel):
    """新闻价格关联请求"""
    symbol: str = Field(..., description="交易对符号")
    days: int = Field(30, description="统计天数")


class SentimentRequest(BaseModel):
    """市场情绪请求"""
    symbol: Optional[str] = Field(None, description="交易对符号")
    days: int = Field(7, description="统计天数")


# ============= 统计相关模型 =============

class StatisticsResponse(BaseModel):
    """统计响应"""
    total_count: int
    with_keywords: int
    with_summary: int
    keyword_rate: float
    summary_rate: float
    date_range: tuple
    channel_count: Optional[int] = None


class KeywordStatsResponse(BaseModel):
    """关键词统计响应"""
    keyword: str
    count: int
    news_count: Optional[int] = None
    trend: Optional[str] = None
    similarity: Optional[float] = None


# ============= 数据源配置 =============

class SourceConfig(BaseModel):
    """数据源配置"""
    source: NewsSource = Field(NewsSource.CRYPTO, description="数据源类型")
