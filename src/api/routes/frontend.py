"""
前端路由
提供Web界面
"""
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Form, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from src.services import get_news_service, get_search_service, get_market_service, get_personalization_service
from src.core.models import NewsSource
from src.data.repositories.user_profile import UserProfileRepository

logger = logging.getLogger(__name__)

# 初始化模板
templates_dir = Path(__file__).parent.parent.parent.parent / "templates_UI"
templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter(tags=["frontend"])

# 频道映射
CHANNEL_MAP = {
    "1": ("-1001387109317", "@theblockbeats"),
    "2": ("-1001735732363", "@TechFlowDaily"),
    "3": ("-1002395608815", "@news6551"),
    "4": ("-1002117032512", "@MMSnews"),
}

CHANNEL_KEY_TO_NAME = {key: meta[1] for key, meta in CHANNEL_MAP.items()}
CHANNEL_ID_TO_NAME = {meta[0]: meta[1] for meta in CHANNEL_MAP.values()}

SOURCE_OPTIONS = [
    {"key": "crypto", "label": "Web3 新闻"},
    {"key": "hkstocks", "label": "港股新闻"}
]
SOURCE_LABEL_MAP = {item["key"]: item["label"] for item in SOURCE_OPTIONS}
DEFAULT_SOURCE = "crypto"
SOURCE_BADGES = {"crypto": "Web3", "hkstocks": "港股"}
DEFAULT_HOME_TASKS = [
    {"task": "discover", "label": "推荐适合我的新闻", "prompt": "推荐适合我的新闻，优先看过去12小时最值得关注的变化"},
    {"task": "understand", "label": "分析今天市场局势", "prompt": "分析一下今天的市场局势，给我3个最重要的结论"},
    {"task": "focus", "label": "只看高波动机会", "prompt": "帮我筛出过去6小时更适合短线关注的高波动机会"},
    {"task": "report", "label": "生成个性化简报", "prompt": "生成一份适合我的个性化市场简报"},
]


def build_recommendations_snapshot(user_id: str = "web_user", limit: int = 4) -> Dict[str, Any]:
    personalization_service = get_personalization_service()
    user_profile_repo = UserProfileRepository()
    profile = user_profile_repo.get_or_create(user_id)
    recommended_news, recommendation_status = personalization_service.recommend_news_with_status(
        preferences=profile.preferences,
        limit=limit,
        source=NewsSource.CRYPTO,
    )
    _enhance_news_results(recommended_news)
    return {
        "success": True,
        "recommended_news": recommended_news,
        "recommendation_status": recommendation_status,
    }


def normalize_source(source: Optional[str]) -> str:
    """标准化数据源"""
    if not source:
        return DEFAULT_SOURCE
    key = str(source).lower()
    return key if key in SOURCE_LABEL_MAP else DEFAULT_SOURCE


def _split_keywords(raw_keywords: Optional[str]) -> List[str]:
    """分割关键词字符串"""
    return [k.strip() for k in str(raw_keywords or "").split(',') if k.strip()]


def _resolve_channel_label(raw_source: Optional[str], raw_channel_id: Optional[str]) -> Optional[str]:
    """解析频道标签"""
    candidates = []
    if raw_source is not None:
        candidates.append(str(raw_source).strip())
    if raw_channel_id is not None:
        candidates.append(str(raw_channel_id).strip())
    for candidate in candidates:
        if not candidate:
            continue
        if candidate.startswith('@'):
            return candidate
        if candidate in CHANNEL_KEY_TO_NAME:
            return CHANNEL_KEY_TO_NAME[candidate]
        if candidate in CHANNEL_ID_TO_NAME:
            return CHANNEL_ID_TO_NAME[candidate]
    return None


def _enhance_news_results(results: List[Dict]):
    """增强新闻结果"""
    for news in results:
        news.setdefault('source_type', 'crypto')
        news['source_badge'] = SOURCE_BADGES.get(news['source_type'], 'News')
        if not news.get('summary') and news.get('abstract'):
            news['summary'] = news['abstract']
        news['keyword_list'] = _split_keywords(news.get('keywords', ''))
        if not news.get('title'):
            news['title'] = (news.get('text') or '')[:80]
        resolved_source = _resolve_channel_label(news.get('source'), news.get('channel_id'))
        original_source = news.get('source') or news.get('channel_id')
        news['source'] = resolved_source or original_source or 'Web3 Feed'


def _news_to_dict(news) -> Dict[str, Any]:
    """将News对象转换为字典"""
    summary_text = getattr(news, 'abstract', None) or getattr(news, 'summary', '') or ''
    original_text = getattr(news, 'original_text', None) or news.text or ''
    return {
        'id': news.id,
        'title': news.title,
        'text': news.text,
        'content': news.text,
        'date': news.date,
        'keywords': news.keywords,
        'summary': summary_text,
        'abstract': summary_text,
        'channel_id': news.channel_id if hasattr(news, 'channel_id') else None,
        'currency': news.currency if hasattr(news, 'currency') else None,
        'industry': news.industry if hasattr(news, 'industry') else None,
        'stock_code': getattr(news, 'stock_code', None),
        'source_type': news.source.value,
        'source': news.channel_id if hasattr(news, 'channel_id') else None,
        'original_text': original_text,
        'url': getattr(news, 'url', None) or '',
    }


def build_dashboard_snapshot(user_id: str = "web_user") -> Dict[str, Any]:
    """构建仪表板快照"""
    try:
        personalization_service = get_personalization_service()
        user_profile_repo = UserProfileRepository()
        profile = user_profile_repo.get_or_create(user_id)
        profile_summary = personalization_service.summarize_profile(profile.preferences)

        # 获取Crypto统计
        crypto_service = get_news_service(source=NewsSource.CRYPTO, auto_extract_keywords=False)
        crypto_stats = crypto_service.get_statistics()

        # 获取HKStocks统计
        hk_service = get_news_service(source=NewsSource.HKSTOCKS, auto_extract_keywords=False)
        hk_stats = hk_service.get_statistics()

        # 获取Crypto热门关键词和最新新闻
        crypto_search = get_search_service(source=NewsSource.CRYPTO)
        crypto_popular = crypto_search.get_popular_keywords(top_n=6)
        crypto_latest = crypto_search.search_recent(days=365, limit=4)

        # 获取HK热门关键词和最新新闻
        hk_search = get_search_service(source=NewsSource.HKSTOCKS)
        hk_popular = hk_search.get_popular_keywords(top_n=6)
        hk_latest = hk_search.search_recent(days=365, limit=4)

        fear_greed = {
            "value": None,
            "classification": "数据不可用",
            "value_class": "neutral",
            "timestamp": None,
        }
        crypto_market_board = {
            "coins": [],
            "last_updated": None,
        }
        try:
            market_service = get_market_service(source=NewsSource.CRYPTO)
            fear_greed = market_service.fetch_fear_greed_index()
        except Exception as market_exc:
            logger.warning(f"Fear & Greed 获取失败，但新闻快照继续返回: {market_exc}")

        try:
            market_service = get_market_service(source=NewsSource.CRYPTO)
            crypto_market_board = market_service.fetch_crypto_market_board(limit=20)
        except Exception as market_exc:
            logger.warning(f"市场看板获取失败，但新闻快照继续返回: {market_exc}")

        # 转换为前端需要的格式
        crypto_trending = [
            {"keyword": kw['keyword'], "count": kw['count'], "symbol": None}
            for kw in crypto_popular
        ]

        hk_trending = [
            {"keyword": kw['keyword'], "count": kw['count'], "symbol": None}
            for kw in hk_popular
        ]

        crypto_latest_data = [_news_to_dict(news) for news in crypto_latest]
        _enhance_news_results(crypto_latest_data)

        recommendation_snapshot = build_recommendations_snapshot(user_id=user_id, limit=4)
        recommended_news = recommendation_snapshot["recommended_news"]
        recommendation_status = recommendation_snapshot["recommendation_status"]

        hk_latest_data = [_news_to_dict(news) for news in hk_latest]
        _enhance_news_results(hk_latest_data)

        return {
            "total_crypto_news": crypto_stats.get('total_count', 0),
            "total_hk_news": hk_stats.get('total_count', 0),
            "crypto_keyword_rate": crypto_stats.get('keyword_rate', 0),
            "hk_keyword_rate": hk_stats.get('keyword_rate', 0),
            "crypto_trending": crypto_trending,
            "hk_trending": hk_trending,
            "crypto_latest": crypto_latest_data,
            "recommended_news": recommended_news,
            "recommendation_status": recommendation_status,
            "hk_latest": hk_latest_data,
            "profile_summary": profile_summary,
            "home_tasks": DEFAULT_HOME_TASKS,
            "spotlight_symbols": [],
            "fear_greed": fear_greed,
            "crypto_market_board": crypto_market_board,
        }
    except Exception as e:
        logger.error(f"构建仪表板失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            "total_crypto_news": 0,
            "total_hk_news": 0,
            "crypto_keyword_rate": 0,
            "hk_keyword_rate": 0,
            "crypto_trending": [],
            "hk_trending": [],
            "crypto_latest": [],
            "recommended_news": [],
            "recommendation_status": {
                "mode": "empty",
                "lookback_days": None,
                "last_refreshed_at": None,
                "count": 0,
            },
            "hk_latest": [],
            "profile_summary": {
                "summary": "暂未获取到你的画像摘要。",
                "preferences": {},
                "profile_initialized": False,
            },
            "home_tasks": DEFAULT_HOME_TASKS,
            "spotlight_symbols": [],
            "fear_greed": {
                "value": None,
                "classification": "数据不可用",
                "value_class": "neutral",
                "timestamp": None,
            },
            "crypto_market_board": {
                "coins": [],
                "last_updated": None,
            },
        }


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """主页"""
    user_id = request.query_params.get("user_id", "web_user")
    snapshot = build_dashboard_snapshot(user_id=user_id)
    context = {
        "request": request,
        "user_id": user_id,
        "source_options": SOURCE_OPTIONS,
        "auto_refresh": True,
        "refresh_interval": 60,
        **snapshot,
    }
    return templates.TemplateResponse("home.html", context)


@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    keyword: Optional[str] = None,
    source: str = DEFAULT_SOURCE
):
    """搜索页面"""
    return await _search_news_action(request, keyword or "", source)


@router.get("/analyzer", response_class=HTMLResponse)
async def analyzer_page(request: Request):
    """分析器页面"""
    return templates.TemplateResponse("analyzer.html", {"request": request})


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """AI聊天页面"""
    user_id = request.query_params.get("user_id", "web_user")
    conversation_id = request.query_params.get("conversation_id")
    open_onboarding = request.query_params.get("open_onboarding", "0")
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "user_id": user_id,
            "conversation_id": conversation_id,
            "open_onboarding": open_onboarding,
        }
    )


@router.get("/search_action", response_class=HTMLResponse)
async def search_news_action_get(
    request: Request,
    keyword: str = Query(""),
    source: str = Query(DEFAULT_SOURCE)
):
    """搜索动作（GET）"""
    return await _search_news_action(request, keyword, source)


@router.post("/search_action", response_class=HTMLResponse)
async def search_news_action_post(
    request: Request,
    keyword: str = Form(""),
    source: str = Form(DEFAULT_SOURCE)
):
    """搜索动作（POST）"""
    return await _search_news_action(request, keyword, source)


async def _search_news_action(
    request: Request,
    keyword: str,
    source: str
):
    """搜索动作实现"""
    try:
        # 标准化数据源
        source_key = normalize_source(source)
        source_enum = NewsSource.CRYPTO if source_key == "crypto" else NewsSource.HKSTOCKS

        # 获取服务
        search_service = get_search_service(source=source_enum)

        # 清理关键词
        clean_keyword = keyword.strip()
        keyword_mode = bool(clean_keyword)

        # 执行搜索
        if keyword_mode:
            # 关键词搜索
            news_list = search_service.search_by_keyword(clean_keyword, exact=False, limit=50)
            keyword_heading = f'关键词 "{clean_keyword}"'
            result_summary = f"共 {len(news_list)} 条结果"
        else:
            # 获取最新新闻
            news_list = search_service.search_recent(days=365, limit=20)
            keyword_heading = "最新快讯"
            result_summary = f"展示最新 {len(news_list)} 条资讯"

        # 转换为字典
        results = [_news_to_dict(news) for news in news_list]

        # 增强结果
        _enhance_news_results(results)

        # 获取热门关键词
        popular_keywords = search_service.get_popular_keywords(top_n=20)
        top_keywords_counts = [
            {"keyword": kw['keyword'], "count": kw['count']}
            for kw in popular_keywords
        ]

        max_count = max([item["count"] for item in top_keywords_counts]) if top_keywords_counts else 1
        min_count = min([item["count"] for item in top_keywords_counts]) if top_keywords_counts else 0

        # 构建上下文
        context = {
            "request": request,
            "source_options": SOURCE_OPTIONS,
            "results": results,
            "keyword": clean_keyword,
            "source": source_key,
            "keyword_heading": keyword_heading,
            "result_summary": result_summary,
            "top_keywords": top_keywords_counts,
            "max_count": max_count,
            "min_count": min_count,
            "trading_symbol": None,
            "related_symbols": [],
        }

        return templates.TemplateResponse("search_results.html", context)

    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": str(e),
                "message": "搜索失败，请稍后重试"
            }
        )


@router.get("/api/dashboard")
async def dashboard_api(user_id: str = "web_user"):
    """仪表板API"""
    return build_dashboard_snapshot(user_id=user_id)


@router.get("/api/recommendations/refresh")
async def refresh_recommendations_api(user_id: str = "web_user"):
    """刷新个性化推荐。"""
    return build_recommendations_snapshot(user_id=user_id, limit=4)
