"""
个性化服务
负责用户画像、onboarding、推荐排序与个性化报告组装
"""
import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.models import NewsSource, News, PersonalizedReport
from src.services.search_service import SearchService

logger = logging.getLogger(__name__)


DEFAULT_PROFILE_PREFERENCES: Dict[str, Any] = {
    "profile_initialized": False,
    "risk_preference": "balanced",
    "trading_frequency": "medium",
    "holding_period": "swing",
    "focus_assets": ["BTC", "ETH"],
    "focus_themes": ["AI", "ETF"],
    "report_style": "balanced",
    "signal_sensitivity": "medium",
}


ONBOARDING_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "risk_preference",
        "title": "你的风险偏好更接近哪种？",
        "options": [
            {"value": "conservative", "label": "稳健型"},
            {"value": "balanced", "label": "平衡型"},
            {"value": "aggressive", "label": "进攻型"},
        ],
    },
    {
        "id": "trading_frequency",
        "title": "你的交易频率通常是？",
        "options": [
            {"value": "low", "label": "低频"},
            {"value": "medium", "label": "中频"},
            {"value": "high", "label": "高频"},
        ],
    },
    {
        "id": "holding_period",
        "title": "你的典型持仓周期是？",
        "options": [
            {"value": "intraday", "label": "日内"},
            {"value": "swing", "label": "波段"},
            {"value": "position", "label": "中长期"},
        ],
    },
    {
        "id": "focus_assets",
        "title": "你主要关注哪些资产？",
        "type": "multi",
        "options": [
            {"value": "BTC", "label": "BTC"},
            {"value": "ETH", "label": "ETH"},
            {"value": "majors", "label": "主流币"},
            {"value": "altcoins", "label": "山寨币"},
            {"value": "thematic", "label": "主题叙事"},
        ],
    },
    {
        "id": "focus_themes",
        "title": "你更关注哪些叙事主题？",
        "type": "multi",
        "options": [
            {"value": "ETF", "label": "ETF"},
            {"value": "AI", "label": "AI"},
            {"value": "DeFi", "label": "DeFi"},
            {"value": "infra", "label": "Infra"},
            {"value": "macro", "label": "Macro"},
        ],
    },
    {
        "id": "report_style",
        "title": "你偏好的报告风格是？",
        "options": [
            {"value": "concise", "label": "简洁"},
            {"value": "balanced", "label": "平衡"},
            {"value": "deep", "label": "深入"},
        ],
    },
    {
        "id": "signal_sensitivity",
        "title": "你希望系统对机会信号多敏感？",
        "options": [
            {"value": "low", "label": "谨慎"},
            {"value": "medium", "label": "标准"},
            {"value": "high", "label": "敏捷"},
        ],
    },
]


ASSET_HINTS = {
    "BTC": ["btc", "bitcoin", "比特币"],
    "ETH": ["eth", "ethereum", "以太坊"],
    "SOL": ["sol", "solana"],
    "ETF": ["etf"],
}

THEME_HINTS = {
    "AI": ["ai", "agent", "智能体"],
    "ETF": ["etf"],
    "DeFi": ["defi", "dex", "借贷", "流动性"],
    "infra": ["infra", "基础设施", "layer2", "模块化", "rollup"],
    "macro": ["macro", "宏观", "美联储", "利率"],
}


class PersonalizationService:
    """个性化能力服务"""

    def normalize_preferences(self, preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        merged = dict(DEFAULT_PROFILE_PREFERENCES)
        if preferences:
            merged.update(preferences)
        merged["focus_assets"] = self._normalize_list(merged.get("focus_assets"))
        merged["focus_themes"] = self._normalize_list(merged.get("focus_themes"))
        merged["profile_initialized"] = bool(merged.get("profile_initialized"))
        return merged

    def get_onboarding_questions(self) -> List[Dict[str, Any]]:
        return ONBOARDING_QUESTIONS

    def build_preferences_from_answers(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        prefs = self.normalize_preferences(answers)
        prefs["profile_initialized"] = True
        return prefs

    def summarize_profile(self, preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        prefs = self.normalize_preferences(preferences)
        summary = (
            f"你当前偏好{self._label_risk(prefs['risk_preference'])}、"
            f"{self._label_frequency(prefs['trading_frequency'])}交易、"
            f"{self._label_holding(prefs['holding_period'])}持仓，"
            f"重点关注 {', '.join(prefs['focus_assets'][:3])} / {', '.join(prefs['focus_themes'][:3])}。"
        )
        return {
            "summary": summary,
            "preferences": prefs,
            "profile_initialized": prefs["profile_initialized"],
        }

    def recommend_news(
        self,
        preferences: Optional[Dict[str, Any]],
        limit: int = 6,
        source: NewsSource = NewsSource.CRYPTO,
        intent_filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        results, _ = self.recommend_news_with_status(
            preferences=preferences,
            limit=limit,
            source=source,
            intent_filters=intent_filters,
        )
        return results

    def recommend_news_with_status(
        self,
        preferences: Optional[Dict[str, Any]],
        limit: int = 6,
        source: NewsSource = NewsSource.CRYPTO,
        intent_filters: Optional[Dict[str, Any]] = None,
    ) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        prefs = self.normalize_preferences(preferences)
        search_service = SearchService(source=source)
        news_list: List[News] = []
        selected_days: Optional[int] = None
        mode = "empty"

        for days in (7, 30, 90, 365):
            news_list = search_service.search_recent(days=days, limit=120)
            if news_list:
                selected_days = days
                mode = "recent" if days == 7 else "expanded"
                break

        if not news_list:
            news_list = search_service.news_repo.get_recent(limit=120)
            if news_list:
                mode = "historical_fallback"

        scored = []
        for news in news_list:
            score, reasons = self._score_news(news, prefs, intent_filters or {})
            if mode == "historical_fallback" and reasons == ["与你的画像存在一般相关性"]:
                reasons = ["暂无实时更新，先从历史库中挑选最新资讯"]
            scored.append((score, reasons, news))
        scored.sort(key=lambda item: (item[0], item[2].date or ""), reverse=True)

        results = []
        for score, reasons, news in scored[:limit]:
            item = news.to_dict()
            item["recommendation_score"] = round(score, 2)
            item["recommendation_reasons"] = reasons
            results.append(item)

        if not results:
            mode = "empty"

        return results, {
            "mode": mode,
            "lookback_days": selected_days,
            "last_refreshed_at": datetime.utcnow().isoformat(),
            "count": len(results),
        }

    def build_personalized_briefing(
        self,
        preferences: Optional[Dict[str, Any]],
        news_items: List[Dict[str, Any]],
        task_filters: Optional[Dict[str, Any]] = None,
    ) -> PersonalizedReport:
        prefs = self.normalize_preferences(preferences)
        focus_assets = task_filters.get("focus_assets") if task_filters else None
        focus_themes = task_filters.get("focus_themes") if task_filters else None
        headline = "为你生成的个性化市场简报"
        if focus_assets or focus_themes:
            bits = []
            if focus_assets:
                bits.append(" / ".join(focus_assets[:3]))
            if focus_themes:
                bits.append(" / ".join(focus_themes[:3]))
            headline = f"围绕 {' · '.join(bits)} 的个性化简报"

        key_points = []
        evidence_ids: List[int] = []
        for item in news_items[:3]:
            evidence_ids.append(item.get("id"))
            reasons = "、".join(item.get("recommendation_reasons", [])[:2]) or "与你的画像高度相关"
            key_points.append(f"{item.get('title') or item.get('text', '')[:40]}：{reasons}")

        risk_notes = self._build_risk_notes(prefs)
        next_actions = self._build_next_actions(prefs)
        summary = (
            f"基于你偏好{self._label_risk(prefs['risk_preference'])}与"
            f"{self._label_holding(prefs['holding_period'])}风格，"
            f"系统已优先筛出 {len(news_items)} 条最相关资讯。"
        )
        if prefs.get("report_style") == "deep":
            summary += " 当前结果更偏证据链与趋势延展。"
        elif prefs.get("report_style") == "concise":
            summary += " 当前结果更偏直接结论与行动提示。"

        return PersonalizedReport(
            title=headline,
            summary=summary,
            key_points=key_points,
            risk_notes=risk_notes,
            next_actions=next_actions,
            evidence_news_ids=evidence_ids,
            metadata={
                "focus_assets": focus_assets or prefs.get("focus_assets", []),
                "focus_themes": focus_themes or prefs.get("focus_themes", []),
                "report_style": prefs.get("report_style"),
            },
        )

    def _score_news(
        self,
        news: News,
        prefs: Dict[str, Any],
        intent_filters: Dict[str, Any],
    ) -> tuple[float, List[str]]:
        text = " ".join([
            news.title or "",
            news.text or "",
            news.keywords or "",
            news.currency or "",
        ]).lower()
        score = 0.0
        reasons: List[str] = []

        desired_assets = self._normalize_list(intent_filters.get("focus_assets")) or prefs.get("focus_assets", [])
        desired_themes = self._normalize_list(intent_filters.get("focus_themes")) or prefs.get("focus_themes", [])

        for asset in desired_assets:
            if self._matches_any(text, ASSET_HINTS.get(asset.upper(), [asset.lower()])):
                score += 3.0
                reasons.append(f"命中关注资产 {asset}")

        for theme in desired_themes:
            if self._matches_any(text, THEME_HINTS.get(theme, [theme.lower()])):
                score += 2.5
                reasons.append(f"命中关注主题 {theme}")

        if prefs.get("risk_preference") == "aggressive":
            if any(token in text for token in ["上涨", "暴涨", "融资", "收购", "alpha", "机会"]):
                score += 1.5
                reasons.append("更偏进攻型机会")
        elif prefs.get("risk_preference") == "conservative":
            if any(token in text for token in ["etf", "监管", "风险", "美联储", "宏观"]):
                score += 1.5
                reasons.append("更偏稳健型关注点")

        if prefs.get("signal_sensitivity") == "high" and any(token in text for token in ["突发", "最新", "breaking", "监测"]):
            score += 1.2
            reasons.append("适合高敏感信号偏好")

        if not reasons:
            reasons.append("与你的画像存在一般相关性")

        return score, reasons

    @staticmethod
    def _matches_any(text: str, patterns: List[str]) -> bool:
        return any(pattern.lower() in text for pattern in patterns if pattern)

    @staticmethod
    def _normalize_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            parts = re.split(r"[,\s/]+", value)
            return [part.strip() for part in parts if part.strip()]
        return [str(value).strip()]

    @staticmethod
    def _label_risk(value: str) -> str:
        return {
            "conservative": "稳健",
            "balanced": "平衡",
            "aggressive": "高弹性",
        }.get(value, "平衡")

    @staticmethod
    def _label_frequency(value: str) -> str:
        return {"low": "低频", "medium": "中频", "high": "高频"}.get(value, "中频")

    @staticmethod
    def _label_holding(value: str) -> str:
        return {
            "intraday": "日内",
            "swing": "波段",
            "position": "中长期",
        }.get(value, "波段")

    def _build_risk_notes(self, prefs: Dict[str, Any]) -> List[str]:
        if prefs.get("risk_preference") == "aggressive":
            return [
                "高弹性主题通常伴随更高波动，需关注突发回撤。",
                "建议结合实时新闻与量价变化二次确认。",
            ]
        if prefs.get("risk_preference") == "conservative":
            return [
                "优先关注监管、宏观与主流资产信号，避免被短期叙事噪声误导。",
                "建议在主题确认后再进入深挖或策略验证。",
            ]
        return [
            "当前结果兼顾机会与风险，建议结合后续追问进一步确认。",
        ]

    def _build_next_actions(self, prefs: Dict[str, Any]) -> List[str]:
        actions = [
            "继续深挖当前最重要的主题",
            "只看过去 12 小时与你画像最相关的新闻",
        ]
        if prefs.get("trading_frequency") == "high":
            actions.append("筛出更适合短线观察的高波动信号")
        else:
            actions.append("生成一份更偏中长期的主题观察报告")
        return actions


_service: Optional[PersonalizationService] = None


def get_personalization_service() -> PersonalizationService:
    global _service
    if _service is None:
        _service = PersonalizationService()
    return _service
