"""
Agent tool registry
将现有手动能力统一封装为可编排工具。
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from src.core.models import NewsSource
from src.data.repositories.user_profile import UserProfileRepository
from src.services import (
    get_market_service,
    get_personalization_service,
    get_search_service,
    get_trend_service,
)


def _schema(properties: Dict[str, Any], required: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
    }


class AgentToolRegistry:
    def __init__(self):
        self.personalization_service = get_personalization_service()
        self.user_profile_repo = UserProfileRepository()
        self.search_service = get_search_service(source=NewsSource.CRYPTO)
        self.market_service = get_market_service(source=NewsSource.CRYPTO)
        self.trend_service = get_trend_service(source=NewsSource.CRYPTO)
        self._tools = self._build_tool_specs()

    def list_tools(self) -> List[Dict[str, Any]]:
        return [spec["meta"] for spec in self._tools.values()]

    def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        spec = self._tools.get(tool_id)
        return spec["meta"] if spec else None

    def execute(self, tool_id: str, **kwargs) -> Dict[str, Any]:
        spec = self._tools.get(tool_id)
        if not spec:
            raise ValueError(f"Unknown tool: {tool_id}")
        return spec["handler"](**kwargs)

    def _build_tool_specs(self) -> Dict[str, Dict[str, Any]]:
        return {
            "profile.read": {
                "meta": {
                    "id": "profile.read",
                    "display_name": "读取用户画像",
                    "description": "读取用户偏好、关注资产、主题与摘要",
                    "input_schema": _schema({"user_id": {"type": "string"}}),
                    "output_schema": _schema({"summary": {"type": "object"}}),
                    "latency_tier": "fast",
                    "data_source": "user_profile_db",
                    "supports_streaming": False,
                    "ui_block_type": "profile",
                },
                "handler": self._profile_read,
            },
            "news.search": {
                "meta": {
                    "id": "news.search",
                    "display_name": "搜索新闻",
                    "description": "按关键词、时间窗口、币种等条件搜索 Crypto 新闻",
                    "input_schema": _schema({
                        "keyword": {"type": "string"},
                        "days": {"type": "integer"},
                        "limit": {"type": "integer"},
                        "currency": {"type": "string"},
                    }),
                    "output_schema": _schema({"items": {"type": "array"}}),
                    "latency_tier": "medium",
                    "data_source": "crypto_news_db",
                    "supports_streaming": False,
                    "ui_block_type": "news_list",
                },
                "handler": self._news_search,
            },
            "news.similar_keywords": {
                "meta": {
                    "id": "news.similar_keywords",
                    "display_name": "查找相关关键词",
                    "description": "查找近似关键词、相关关键词与对应新闻",
                    "input_schema": _schema({
                        "keyword": {"type": "string"},
                        "top_n": {"type": "integer"},
                    }, required=["keyword"]),
                    "output_schema": _schema({"similar_keywords": {"type": "array"}}),
                    "latency_tier": "medium",
                    "data_source": "keyword_similarity",
                    "supports_streaming": False,
                    "ui_block_type": "analysis",
                },
                "handler": self._similar_keywords,
            },
            "news.filter": {
                "meta": {
                    "id": "news.filter",
                    "display_name": "过滤新闻结果",
                    "description": "按资产、主题和时间对新闻结果进一步过滤",
                    "input_schema": _schema({
                        "items": {"type": "array"},
                        "assets": {"type": "array"},
                        "themes": {"type": "array"},
                        "limit": {"type": "integer"},
                    }),
                    "output_schema": _schema({"items": {"type": "array"}}),
                    "latency_tier": "fast",
                    "data_source": "in_memory",
                    "supports_streaming": False,
                    "ui_block_type": "news_list",
                },
                "handler": self._news_filter,
            },
            "news.recommend": {
                "meta": {
                    "id": "news.recommend",
                    "display_name": "个性化推荐",
                    "description": "基于画像和历史兜底返回推荐新闻",
                    "input_schema": _schema({
                        "user_id": {"type": "string"},
                        "limit": {"type": "integer"},
                        "intent_filters": {"type": "object"},
                    }),
                    "output_schema": _schema({"recommended_news": {"type": "array"}}),
                    "latency_tier": "medium",
                    "data_source": "crypto_news_db+profile",
                    "supports_streaming": False,
                    "ui_block_type": "briefing",
                },
                "handler": self._recommend_news,
            },
            "analysis.keyword_trend": {
                "meta": {
                    "id": "analysis.keyword_trend",
                    "display_name": "关键词趋势",
                    "description": "分析关键词在最近窗口内的热度变化",
                    "input_schema": _schema({
                        "keyword": {"type": "string"},
                        "days": {"type": "integer"},
                    }, required=["keyword"]),
                    "output_schema": _schema({"trend": {"type": "object"}}),
                    "latency_tier": "medium",
                    "data_source": "keyword_trends",
                    "supports_streaming": False,
                    "ui_block_type": "analysis",
                },
                "handler": self._keyword_trend,
            },
            "analysis.news_correlation": {
                "meta": {
                    "id": "analysis.news_correlation",
                    "display_name": "新闻与市场关联",
                    "description": "分析新闻热度与价格变化、情绪的关联",
                    "input_schema": _schema({
                        "symbol": {"type": "string"},
                        "days": {"type": "integer"},
                    }, required=["symbol"]),
                    "output_schema": _schema({"correlation": {"type": "object"}}),
                    "latency_tier": "medium",
                    "data_source": "market+trend",
                    "supports_streaming": False,
                    "ui_block_type": "analysis",
                },
                "handler": self._news_correlation,
            },
            "market.snapshot": {
                "meta": {
                    "id": "market.snapshot",
                    "display_name": "市场快照",
                    "description": "获取 Fear & Greed 与主流币市场快照",
                    "input_schema": _schema({"limit": {"type": "integer"}}),
                    "output_schema": _schema({"snapshot": {"type": "object"}}),
                    "latency_tier": "medium",
                    "data_source": "coingecko+alternative.me",
                    "supports_streaming": False,
                    "ui_block_type": "market",
                },
                "handler": self._market_snapshot,
            },
            "market.asset_detail": {
                "meta": {
                    "id": "market.asset_detail",
                    "display_name": "资产行情详情",
                    "description": "获取单资产实时行情、24h 变化与相关新闻关联",
                    "input_schema": _schema({
                        "symbol": {"type": "string"},
                        "days": {"type": "integer"},
                    }, required=["symbol"]),
                    "output_schema": _schema({"asset": {"type": "object"}}),
                    "latency_tier": "medium",
                    "data_source": "coingecko+news",
                    "supports_streaming": False,
                    "ui_block_type": "market",
                },
                "handler": self._market_asset_detail,
            },
            "market.opportunity_scan": {
                "meta": {
                    "id": "market.opportunity_scan",
                    "display_name": "机会扫描",
                    "description": "围绕高波动与 Alpha 线索扫描潜在观察对象",
                    "input_schema": _schema({
                        "user_id": {"type": "string"},
                        "focus_assets": {"type": "array"},
                    }),
                    "output_schema": _schema({"opportunities": {"type": "array"}}),
                    "latency_tier": "slow",
                    "data_source": "skill_alpha_hunter",
                    "supports_streaming": False,
                    "ui_block_type": "opportunity",
                },
                "handler": self._market_opportunity_scan,
            },
            "report.compose": {
                "meta": {
                    "id": "report.compose",
                    "display_name": "生成报告",
                    "description": "将前序工具结果组合成 briefing / deep dive / scan report",
                    "input_schema": _schema({
                        "mission_type": {"type": "string"},
                        "context": {"type": "object"},
                    }, required=["mission_type"]),
                    "output_schema": _schema({"report": {"type": "object"}}),
                    "latency_tier": "fast",
                    "data_source": "orchestrator",
                    "supports_streaming": False,
                    "ui_block_type": "report",
                },
                "handler": self._compose_report,
            },
        }

    def _profile_read(self, *, user_id: str = "web_user", **_: Any) -> Dict[str, Any]:
        profile = self.user_profile_repo.get_or_create(user_id)
        preferences = self.personalization_service.normalize_preferences(profile.preferences)
        return {
            "preferences": preferences,
            "summary": self.personalization_service.summarize_profile(preferences),
        }

    def _news_search(
        self,
        *,
        keyword: str = "",
        days: int = 7,
        limit: int = 8,
        currency: Optional[str] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        results = self.search_service.search_by_keyword(keyword=keyword, exact=False, limit=max(limit * 3, 12))
        start_date = datetime.now() - timedelta(days=max(days, 1))
        items = []
        for news in results:
            news_date = getattr(news, "date", None)
            include = True
            if news_date:
                try:
                    parsed = datetime.fromisoformat(str(news_date).replace("Z", "+00:00").split("+")[0].replace("T", " "))
                    include = parsed >= start_date
                except Exception:
                    include = True
            if currency and currency.lower() not in (getattr(news, "currency", "") or "").lower():
                include = False
            if include:
                items.append(news.to_dict())
            if len(items) >= limit:
                break
        return {"items": items, "keyword": keyword, "days": days}

    def _similar_keywords(self, *, keyword: str, top_n: int = 6, **_: Any) -> Dict[str, Any]:
        results = self.search_service.search_by_similarity(keyword=keyword, top_n=top_n, min_similarity=0.35)
        payload = []
        for item in results:
            payload.append({
                "keyword": item["keyword"],
                "count": item["count"],
                "similarity": round(float(item["similarity"]), 3),
                "sample_titles": [news.title or news.text[:80] for news in item["news"][:3]],
            })
        return {"keyword": keyword, "similar_keywords": payload}

    def _news_filter(
        self,
        *,
        items: List[Dict[str, Any]],
        assets: Optional[List[str]] = None,
        themes: Optional[List[str]] = None,
        limit: int = 6,
        **_: Any,
    ) -> Dict[str, Any]:
        assets = [asset.lower() for asset in (assets or [])]
        themes = [theme.lower() for theme in (themes or [])]
        scored = []
        for item in items or []:
            text = " ".join([
                str(item.get("title", "")),
                str(item.get("text", "")),
                str(item.get("keywords", "")),
                str(item.get("currency", "")),
            ]).lower()
            score = 0
            score += sum(2 for asset in assets if asset in text)
            score += sum(1 for theme in themes if theme in text)
            scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        filtered = [item for _, item in scored[:limit]] if scored else (items or [])[:limit]
        return {"items": filtered, "count": len(filtered)}

    def _recommend_news(
        self,
        *,
        user_id: str = "web_user",
        limit: int = 6,
        intent_filters: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        profile = self.user_profile_repo.get_or_create(user_id)
        recommended_news, recommendation_status = self.personalization_service.recommend_news_with_status(
            preferences=profile.preferences,
            limit=limit,
            source=NewsSource.CRYPTO,
            intent_filters=intent_filters or {},
        )
        return {
            "recommended_news": recommended_news,
            "recommendation_status": recommendation_status,
        }

    def _keyword_trend(self, *, keyword: str, days: int = 30, **_: Any) -> Dict[str, Any]:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=max(days, 1))).strftime("%Y-%m-%d")
        trend = self.trend_service.analyze_keyword_trend(
            keyword=keyword,
            start_date=start_date,
            end_date=end_date,
        )
        data = trend.to_dict() if hasattr(trend, "to_dict") else trend
        return {"trend": data}

    def _news_correlation(self, *, symbol: str, days: int = 14, **_: Any) -> Dict[str, Any]:
        correlation = self.market_service.analyze_news_price_correlation(symbol=symbol, days=days)
        return {"correlation": correlation}

    def _market_snapshot(self, *, limit: int = 10, **_: Any) -> Dict[str, Any]:
        board = self.market_service.fetch_crypto_market_board(limit=limit)
        fng = self.market_service.fetch_fear_greed_index()
        coins = board.get("coins", []) if isinstance(board, dict) else []
        summary = []
        for coin in coins[:5]:
            summary.append({
                "symbol": coin.get("symbol", "").upper(),
                "price": coin.get("current_price"),
                "price_change_percentage_24h": coin.get("price_change_percentage_24h"),
                "market_cap": coin.get("market_cap"),
            })
        return {
            "snapshot": {
                "fear_greed": fng,
                "coins": summary,
                "last_updated": board.get("last_updated") if isinstance(board, dict) else None,
            }
        }

    def _market_asset_detail(self, *, symbol: str, days: int = 7, **_: Any) -> Dict[str, Any]:
        board = self.market_service.fetch_crypto_market_board(limit=50)
        coins = board.get("coins", []) if isinstance(board, dict) else []
        target = next((coin for coin in coins if str(coin.get("symbol", "")).lower() == symbol.lower()), None)
        correlation = self.market_service.analyze_news_price_correlation(symbol=symbol.upper(), days=days)
        recent_news = self.search_service.search_by_keyword(symbol.upper(), exact=False, limit=5)
        return {
            "asset": {
                "symbol": symbol.upper(),
                "market": target or {},
                "correlation": correlation,
                "related_news": [news.to_dict() for news in recent_news[:5]],
            }
        }

    def _market_opportunity_scan(
        self,
        *,
        user_id: str = "web_user",
        focus_assets: Optional[List[str]] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        from src.ai.skills.executor import get_skill_executor

        executor = get_skill_executor()
        result = executor.execute_skill("AlphaHunter", {"focus_assets": focus_assets or []})
        opportunities = ((result.structured_output or {}).get("sections", {}) or {}).get("opportunities", [])
        return {
            "opportunities": opportunities,
            "skill_result": result.to_dict(),
        }

    def _compose_report(
        self,
        *,
        mission_type: str,
        context: Dict[str, Any],
        **_: Any,
    ) -> Dict[str, Any]:
        key_findings = []
        evidence_items = []
        risks = []

        recommended = (context.get("news.recommend") or {}).get("recommended_news", [])
        searched = (context.get("news.search") or {}).get("items", [])
        trend = ((context.get("analysis.keyword_trend") or {}).get("trend") or {})
        snapshot = ((context.get("market.snapshot") or {}).get("snapshot") or {})
        opportunities = (context.get("market.opportunity_scan") or {}).get("opportunities", [])
        correlation = ((context.get("analysis.news_correlation") or {}).get("correlation") or {})
        similar_keywords = (context.get("news.similar_keywords") or {}).get("similar_keywords", [])

        if mission_type == "news_recommendation":
            key_findings.append(f"已按画像筛出 {len(recommended)} 条优先阅读资讯")
            evidence_items = recommended[:4]
            risks.append("若当前实时数据较少，结果可能更多来自历史高相关资讯。")
        elif mission_type == "market_briefing":
            fear_greed = (snapshot.get("fear_greed") or {}).get("classification", "未知")
            key_findings.append(f"市场情绪当前处于 {fear_greed}")
            key_findings.append(f"已结合 {len(searched)} 条相关新闻与市场看板生成结论")
            if trend:
                key_findings.append(f"{trend.get('keyword', '核心主题')} 在窗口内累计出现 {trend.get('total_count', 0)} 次")
            evidence_items = searched[:4]
            risks.append("市场快照依赖外部 API，可用性受上游影响。")
        elif mission_type == "theme_deep_dive":
            key_findings.append(f"已汇总 {len(searched)} 条相关新闻")
            key_findings.append(f"扩展到 {len(similar_keywords)} 个相关关键词")
            if correlation:
                key_findings.append(correlation.get("description", "已完成新闻与市场关联分析"))
            evidence_items = searched[:4]
            risks.append("深挖结果适合作为研究输入，不直接等价于交易信号。")
        elif mission_type == "opportunity_scan":
            key_findings.append(f"当前识别到 {len(opportunities)} 个机会候选")
            key_findings.extend([f"{item.get('symbol', '标的')}：{item.get('reason', '新闻与市场出现异常组合')}" for item in opportunities[:2]])
            evidence_items = opportunities[:4]
            risks.append("机会扫描更偏观察名单，不等于可直接执行。")
        else:
            key_findings.append("已聚合画像、新闻与市场上下文生成摘要")
            evidence_items = recommended[:3] or searched[:3]
            risks.append("建议继续追问以收敛到具体资产或主题。")

        top_topics = self._extract_top_topics(recommended or searched)
        if top_topics:
            key_findings.append(f"当前相关主题集中在 {', '.join(top_topics[:3])}")

        return {
            "report": {
                "summary": self._compose_summary(mission_type, key_findings),
                "key_findings": key_findings[:5],
                "evidence_items": evidence_items,
                "risks": risks,
                "recommended_actions": self._default_actions(mission_type),
                "generated_at": datetime.now().isoformat(),
            }
        }

    def _extract_top_topics(self, items: List[Dict[str, Any]]) -> List[str]:
        counter: Counter[str] = Counter()
        for item in items[:10]:
            raw = item.get("keywords") or item.get("keyword_list") or []
            keywords = raw if isinstance(raw, list) else [token.strip() for token in str(raw).split(",") if token.strip()]
            for keyword in keywords[:4]:
                counter[str(keyword)] += 1
        return [keyword for keyword, _ in counter.most_common(5)]

    def _compose_summary(self, mission_type: str, key_findings: List[str]) -> str:
        intro_map = {
            "news_recommendation": "我已经按你的画像完成一轮新闻推荐。",
            "market_briefing": "我已经围绕今天的市场状态完成一轮 briefing。",
            "theme_deep_dive": "我已经完成一轮主题深挖。",
            "opportunity_scan": "我已经完成一轮机会扫描。",
            "report_generation": "我已经整理出一份研究摘要。",
        }
        intro = intro_map.get(mission_type, "我已经完成当前任务。")
        if key_findings:
            intro += " " + key_findings[0]
        return intro

    def _default_actions(self, mission_type: str) -> List[str]:
        action_map = {
            "news_recommendation": ["只看 BTC", "换成过去 6 小时", "围绕其中一条新闻继续深挖"],
            "market_briefing": ["解释市场为什么这样走", "只看 ETH 和 AI", "刷新实时数据"],
            "theme_deep_dive": ["继续看过去 24 小时", "比较两个主题", "生成正式简报"],
            "opportunity_scan": ["只看短线候选", "围绕第一名机会继续深挖", "刷新实时数据"],
            "report_generation": ["扩展成深度报告", "只保留高相关证据", "切换到研究工作区"],
        }
        return action_map.get(mission_type, ["继续深挖", "换一个主题", "生成简报"])


_tool_registry: Optional[AgentToolRegistry] = None


def get_agent_tool_registry() -> AgentToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = AgentToolRegistry()
    return _tool_registry
