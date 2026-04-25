"""
AI Agent Service
高层编排服务，负责统一工具层、任务规划与执行轨迹输出。
"""
from __future__ import annotations

import logging
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.ai.agents.graph import create_agent_graph
from src.ai.agents.state import create_initial_state
from src.ai.llm.base import LLMMessage
from src.ai.llm.factory import get_llm_provider
from src.ai.skills.executor import get_skill_executor
from src.core.models import AgentResultBlock, Message, NewsSource, TaskIntent
from src.data.repositories.conversation import ConversationRepository
from src.data.repositories.user_profile import UserProfileRepository
from src.services import (
    get_agent_execution_store,
    get_agent_tool_registry,
    get_personalization_service,
)

logger = logging.getLogger(__name__)


TASK_TYPE_TO_MISSION = {
    "retrieve": "news_retrieval",
    "discover": "news_recommendation",
    "focus": "opportunity_scan",
    "understand": "market_briefing",
    "report": "report_generation",
    "chat": "chat",
}


class AIAgentService:
    """AI Agent编排服务"""

    def __init__(self):
        self.conversation_repo = ConversationRepository()
        self.user_profile_repo = UserProfileRepository()
        self.personalization_service = get_personalization_service()
        self.tool_registry = get_agent_tool_registry()
        self.execution_store = get_agent_execution_store()
        self.agent_graph = None
        self._llm_provider = None

    def _get_agent_graph(self):
        if self.agent_graph is None:
            self.agent_graph = create_agent_graph()
        return self.agent_graph

    def _get_llm_provider(self):
        if self._llm_provider is not None:
            return self._llm_provider
        try:
            self._llm_provider = get_llm_provider()
        except Exception as exc:
            logger.warning("LLM provider unavailable, falling back to rule-based behavior: %s", exc)
            self._llm_provider = False
        return self._llm_provider or None

    def chat(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        try:
            logger.info("Processing chat for user %s", user_id)

            user_profile = self.user_profile_repo.get_or_create(user_id)
            self.user_profile_repo.update_last_active(user_id)
            preferences = self.personalization_service.normalize_preferences(user_profile.preferences)

            if conversation_id:
                conversation = self.conversation_repo.get_by_id(conversation_id)
                if not conversation:
                    raise ValueError(f"Conversation {conversation_id} not found")
            else:
                conversation = self.conversation_repo.create_conversation(
                    user_id=user_id,
                    title=message[:50],
                    metadata={"short_term_memory": {}}
                )
                conversation_id = conversation.id
                self.user_profile_repo.increment_conversation_count(user_id)

            self.conversation_repo.add_message(
                conversation_id=conversation_id,
                role="user",
                content=message
            )

            history_messages = self.conversation_repo.get_messages(conversation_id=conversation_id, limit=10)
            short_term_memory = ((conversation.metadata or {}).get("short_term_memory", {}) if conversation else {})
            task_intent = self._parse_task_intent(message, preferences, history_messages, short_term_memory)
            mission_type = self._resolve_mission_type(task_intent, message)
            execution_plan = self._build_execution_plan(mission_type, task_intent, preferences)

            execution = self.execution_store.create(
                user_id=user_id,
                mission_type=mission_type,
                message=message,
                conversation_id=conversation_id,
                execution_plan=execution_plan,
            )
            execution_id = execution["execution_id"]

            if mission_type == "chat":
                flow_result = self._handle_profile_or_chat(
                    user_id=user_id,
                    message=message,
                    preferences=preferences,
                    task_intent=task_intent,
                    short_term_memory=short_term_memory,
                    execution_id=execution_id,
                )
            else:
                flow_result = self._execute_planned_mission(
                    user_id=user_id,
                    message=message,
                    mission_type=mission_type,
                    task_intent=task_intent,
                    preferences=preferences,
                    short_term_memory=short_term_memory,
                    execution_id=execution_id,
                    execution_plan=execution_plan,
                )

            if flow_result is None:
                flow_result = self._fallback_to_graph(
                    user_id=user_id,
                    message=message,
                    preferences=preferences,
                    conversation_id=conversation_id,
                    task_intent=task_intent,
                    short_term_memory=short_term_memory,
                    execution_id=execution_id,
                )

            reply = flow_result["reply"]
            self.conversation_repo.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=reply,
                agent_name="task_orchestrator",
                tool_calls=flow_result.get("tool_calls", []),
            )

            updated_metadata = conversation.metadata or {}
            updated_metadata["short_term_memory"] = flow_result.get("memory_update", short_term_memory)
            self.conversation_repo.update_metadata(conversation_id, updated_metadata)

            preference_update = flow_result.get("preference_update")
            if preference_update:
                merged_preferences = dict(preferences)
                merged_preferences.update(preference_update)
                self.user_profile_repo.update_preferences(user_id, merged_preferences)
                preferences = merged_preferences

            response = {
                "success": True,
                "reply": reply,
                "final_answer": flow_result.get("final_answer", reply),
                "conversation_id": conversation_id,
                "agent": "task_orchestrator",
                "task_type": task_intent.task_type,
                "mission_type": mission_type,
                "execution_id": execution_id,
                "structured_filters": task_intent.to_dict(),
                "structured_query": flow_result.get("structured_query"),
                "answer_blocks": flow_result.get("answer_blocks", []),
                "result_blocks": flow_result.get("result_blocks", []),
                "suggested_followups": flow_result.get("suggested_followups", []),
                "recommended_actions": flow_result.get("recommended_actions", []),
                "profile_summary": self.personalization_service.summarize_profile(preferences),
                "tool_results": flow_result.get("tool_calls", []),
                "execution_plan": flow_result.get("execution_plan", execution_plan),
                "execution_trace_summary": flow_result.get("execution_trace_summary", {}),
                "data_freshness": flow_result.get("data_freshness", {}),
                "capability_labels": flow_result.get("capability_labels", []),
                "execution_state": flow_result.get("execution_state", {}),
            }
            self.execution_store.complete(execution_id, response)
            return response

        except Exception as e:
            logger.error("Chat error: %s", e, exc_info=True)
            return {
                "success": False,
                "reply": f"抱歉，处理您的请求时出错了：{str(e)}",
                "conversation_id": conversation_id,
                "error": str(e),
            }

    def _parse_task_intent(
        self,
        message: str,
        preferences: Dict[str, Any],
        history_messages: Optional[List[Message]] = None,
        short_term_memory: Optional[Dict[str, Any]] = None,
    ) -> TaskIntent:
        text = (message or "").strip()
        lowered = text.lower()
        task_type = "chat"
        if any(token in text for token in ["筛选", "找出", "列出", "检索", "查一下", "查看", "有关的新闻", "相关新闻"]):
            task_type = "retrieve"
        if any(token in text for token in ["推荐", "适合我", "值得看", "最近有什么", "看一下新闻"]):
            task_type = "discover"
        if any(token in text for token in ["分析", "局势", "为什么", "解读"]):
            task_type = "understand"
        if any(token in text for token in ["高波动", "机会", "alpha", "短线", "异动", "观察名单"]):
            task_type = "focus"
        if any(token in text for token in ["报告", "简报", "快报", "总结", "日报", "briefing"]):
            task_type = "report"
        if any(token in lowered for token in ["深挖", "deep dive"]) or any(token in text for token in ["围绕", "主题"]):
            task_type = "understand"

        time_window = "24h"
        match = re.search(r"(过去|最近)\s*(\d+)\s*(小时|天)", text)
        if match:
            count = match.group(2)
            unit = match.group(3)
            time_window = f"{count}{unit}"
        elif "12小时" in text:
            time_window = "12h"
        elif "6小时" in text:
            time_window = "6h"
        elif "7天" in text:
            time_window = "7d"
        elif any(token in text for token in ["这一周", "本周", "最近一周"]):
            time_window = "7d"
        elif any(token in text for token in ["这个月", "最近一个月"]):
            time_window = "30d"
        elif "今天" in text:
            time_window = "24h"

        explicit_assets = self._extract_assets(text)
        explicit_themes = self._extract_themes(text)
        focus_assets = explicit_assets or (short_term_memory.get("focus_assets", []) if short_term_memory else [])
        focus_themes = explicit_themes or (short_term_memory.get("focus_themes", []) if short_term_memory else [])
        use_profile_defaults = task_type in {"discover", "report"} and not explicit_assets and not explicit_themes
        if not focus_assets and use_profile_defaults:
            focus_assets = preferences.get("focus_assets", [])[:3]
        if not focus_themes and use_profile_defaults:
            focus_themes = preferences.get("focus_themes", [])[:3]

        topic = None
        if task_type in {"understand", "report", "retrieve"}:
            prioritize_theme = any(token in lowered for token in ["围绕", "主题", "defi", "ai", "etf", "macro", "infra"])
            candidates = (focus_themes + focus_assets) if prioritize_theme else (focus_assets + focus_themes)
            if candidates:
                topic = candidates[0]

        output_format = "brief"
        if task_type in {"understand", "report"} or any(token in text for token in ["深度", "详细", "完整"]):
            output_format = "detailed"

        return TaskIntent(
            task_type=task_type,
            time_window=time_window,
            focus_assets=focus_assets,
            focus_themes=focus_themes,
            risk_mode=preferences.get("risk_preference"),
            output_format=output_format,
            query=text,
            topic=topic,
        )

    def _resolve_mission_type(self, task_intent: TaskIntent, message: str) -> str:
        lowered = (message or "").lower()
        if task_intent.task_type == "retrieve":
            return "news_retrieval"
        if any(token in lowered for token in ["高波动", "机会", "alpha", "短线"]):
            return "opportunity_scan"
        if any(token in lowered for token in ["深挖", "deep dive"]) or any(token in message for token in ["围绕", "主题"]):
            return "theme_deep_dive"
        if any(token in lowered for token in ["报告", "简报", "briefing", "总结", "日报"]):
            return "report_generation"
        return TASK_TYPE_TO_MISSION.get(task_intent.task_type, "chat")

    def _build_execution_plan(
        self,
        mission_type: str,
        task_intent: TaskIntent,
        preferences: Dict[str, Any],
    ) -> Dict[str, Any]:
        plans = {
            "news_retrieval": [
                "news.search",
            ],
            "news_recommendation": [
                "profile.read",
                "news.recommend",
                "report.compose",
            ],
            "market_briefing": [
                "profile.read",
                "market.snapshot",
                "news.search",
                "analysis.keyword_trend",
                "report.compose",
            ],
            "theme_deep_dive": [
                "profile.read",
                "news.search",
                "news.similar_keywords",
                "analysis.keyword_trend",
                "analysis.news_correlation",
                "report.compose",
            ],
            "opportunity_scan": [
                "profile.read",
                "market.opportunity_scan",
                "news.search",
                "report.compose",
            ],
            "report_generation": [
                "profile.read",
                "market.snapshot",
                "news.recommend",
                "report.compose",
            ],
        }
        tool_sequence = plans.get(mission_type, [])
        focus = task_intent.topic or (task_intent.focus_assets[:1] + task_intent.focus_themes[:1])
        return {
            "mission_type": mission_type,
            "goal": task_intent.query or "",
            "tool_sequence": tool_sequence,
            "real_time_sources": [tool for tool in tool_sequence if tool.startswith("market.")],
            "historical_sources": [tool for tool in tool_sequence if tool.startswith("news.") or tool.startswith("analysis.")],
            "focus": focus[0] if isinstance(focus, list) and focus else focus,
            "risk_mode": preferences.get("risk_preference"),
        }

    def _handle_profile_or_chat(
        self,
        *,
        user_id: str,
        message: str,
        preferences: Dict[str, Any],
        task_intent: TaskIntent,
        short_term_memory: Dict[str, Any],
        execution_id: str,
    ) -> Optional[Dict[str, Any]]:
        if any(token in message for token in ["我的画像", "我的偏好", "画像", "偏好"]):
            profile_payload = self._run_tool("profile.read", execution_id, user_id=user_id)
            profile_summary = profile_payload["summary"]
            result_blocks = [
                AgentResultBlock(
                    block_type="profile",
                    title="你的画像摘要",
                    summary=profile_summary["summary"],
                    data=profile_summary,
                    key_points=[
                        f"风险偏好：{preferences.get('risk_preference')}",
                        f"交易频率：{preferences.get('trading_frequency')}",
                        f"重点关注：{', '.join(preferences.get('focus_assets', [])[:3])}",
                    ],
                    next_actions=["推荐适合我的新闻", "分析今天市场局势"],
                    source_labels=["用户画像"],
                    tool_trace_refs=["profile.read"],
                ).to_dict()
            ]
            tool_calls = self.execution_store.get(execution_id).get("tool_calls", [])
            return {
                "reply": profile_summary["summary"],
                "final_answer": profile_summary["summary"],
                "answer_blocks": [
                    {
                        "type": "profile_summary",
                        "title": "当前画像",
                        "summary": profile_summary["summary"],
                        "data": profile_summary,
                    }
                ],
                "result_blocks": result_blocks,
                "suggested_followups": ["推荐适合我的新闻", "分析今天市场局势"],
                "recommended_actions": ["推荐适合我的新闻", "生成一份个性化简报"],
                "structured_query": None,
                "memory_update": self._build_memory_update(task_intent, short_term_memory),
                "tool_calls": tool_calls,
                "execution_trace_summary": self._build_execution_trace_summary(tool_calls),
                "capability_labels": ["读取画像", "个性化推荐", "连续研究"],
                "execution_state": self._build_execution_state(tool_calls),
            }
        return None

    def _execute_planned_mission(
        self,
        *,
        user_id: str,
        message: str,
        mission_type: str,
        task_intent: TaskIntent,
        preferences: Dict[str, Any],
        short_term_memory: Dict[str, Any],
        execution_id: str,
        execution_plan: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        context: Dict[str, Any] = {}
        for tool_id in execution_plan["tool_sequence"]:
            params = self._build_tool_params(
                tool_id=tool_id,
                user_id=user_id,
                message=message,
                mission_type=mission_type,
                task_intent=task_intent,
                preferences=preferences,
                context=context,
            )
            context[tool_id] = self._run_tool(tool_id, execution_id, **params)

        tool_calls = self.execution_store.get(execution_id).get("tool_calls", [])
        structured_query = self._build_structured_query(task_intent, mission_type, context, message)
        report = ((context.get("report.compose") or {}).get("report") or {})
        final_answer = self._build_final_answer(
            mission_type=mission_type,
            task_intent=task_intent,
            context=context,
            report=report,
            structured_query=structured_query,
        )
        answer_blocks = self._build_answer_blocks(
            mission_type=mission_type,
            task_intent=task_intent,
            context=context,
            report=report,
        )

        return {
            "reply": final_answer,
            "final_answer": final_answer,
            "answer_blocks": answer_blocks,
            "structured_query": structured_query,
            "result_blocks": [],
            "suggested_followups": report.get("recommended_actions", []),
            "recommended_actions": report.get("recommended_actions", []),
            "memory_update": self._build_memory_update(task_intent, short_term_memory),
            "tool_calls": tool_calls,
            "execution_plan": execution_plan,
            "execution_trace_summary": self._build_execution_trace_summary(tool_calls),
            "data_freshness": self._build_data_freshness(context),
            "capability_labels": self._plan_capability_labels(execution_plan["tool_sequence"]),
            "execution_state": self._build_execution_state(tool_calls),
        }

    def _fallback_to_graph(
        self,
        *,
        user_id: str,
        message: str,
        preferences: Dict[str, Any],
        conversation_id: int,
        task_intent: TaskIntent,
        short_term_memory: Dict[str, Any],
        execution_id: str,
    ) -> Dict[str, Any]:
        initial_state = create_initial_state(
            user_id=user_id,
            user_message=message,
            conversation_id=conversation_id,
            user_profile=preferences,
            short_term_memory=short_term_memory,
            task_intent=task_intent.to_dict(),
        )
        graph = self._get_agent_graph()
        final_state = graph.invoke(initial_state)
        reply = final_state.get("final_response", "抱歉，我遇到了一些问题。")
        tool_calls = final_state.get("tool_results", [])
        self.execution_store.add_event(execution_id, "graph_fallback", {"current_agent": final_state.get("current_agent")})
        self.execution_store.set_tool_calls(execution_id, tool_calls)
        return {
            "reply": reply,
            "final_answer": reply,
            "answer_blocks": [],
            "structured_query": None,
            "result_blocks": [],
            "suggested_followups": [],
            "recommended_actions": [],
            "tool_calls": tool_calls,
            "execution_trace_summary": self._build_execution_trace_summary(tool_calls),
            "execution_state": self._build_execution_state(tool_calls),
        }

    def _build_tool_params(
        self,
        *,
        tool_id: str,
        user_id: str,
        message: str,
        mission_type: str,
        task_intent: TaskIntent,
        preferences: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        topic = task_intent.topic or (task_intent.focus_assets[0] if task_intent.focus_assets else None) or (task_intent.focus_themes[0] if task_intent.focus_themes else None) or "bitcoin"
        days = self._parse_days(task_intent.time_window)
        if tool_id == "profile.read":
            return {"user_id": user_id}
        if tool_id == "news.recommend":
            return {"user_id": user_id, "limit": 6, "intent_filters": task_intent.to_dict()}
        if tool_id == "news.search":
            keyword = self._pick_search_keyword(task_intent, mission_type, message)
            return {"keyword": keyword, "days": days if days else 7, "limit": 6, "currency": task_intent.focus_assets[0] if task_intent.focus_assets else None}
        if tool_id == "news.similar_keywords":
            return {"keyword": topic, "top_n": 6}
        if tool_id == "analysis.keyword_trend":
            return {"keyword": topic, "days": max(days, 7)}
        if tool_id == "analysis.news_correlation":
            symbol = task_intent.focus_assets[0] if task_intent.focus_assets else "BTC"
            return {"symbol": symbol, "days": max(days, 7)}
        if tool_id == "market.snapshot":
            return {"limit": 10}
        if tool_id == "market.asset_detail":
            symbol = task_intent.focus_assets[0] if task_intent.focus_assets else "BTC"
            return {"symbol": symbol, "days": max(days, 7)}
        if tool_id == "market.opportunity_scan":
            return {"user_id": user_id, "focus_assets": task_intent.focus_assets}
        if tool_id == "report.compose":
            return {"mission_type": mission_type, "context": context}
        if tool_id == "news.filter":
            base_items = ((context.get("news.search") or {}).get("items") or [])
            return {"items": base_items, "assets": task_intent.focus_assets, "themes": task_intent.focus_themes, "limit": 6}
        return {}

    def _run_tool(self, tool_id: str, execution_id: str, **kwargs) -> Dict[str, Any]:
        tool_meta = self.tool_registry.get_tool(tool_id) or {"display_name": tool_id}
        started_at = datetime.now().isoformat()
        input_preview = self._preview_data(kwargs)
        self.execution_store.add_event(execution_id, "tool_started", {
            "tool_id": tool_id,
            "title": tool_meta.get("display_name", tool_id),
            "input_preview": input_preview,
        })
        try:
            result = self.tool_registry.execute(tool_id, **kwargs)
            status = "completed"
            error = None
            output_preview = self._preview_data(result)
        except Exception as exc:
            logger.error("Tool %s failed: %s", tool_id, exc, exc_info=True)
            result = {}
            status = "failed"
            error = str(exc)
            output_preview = ""

        ended_at = datetime.now().isoformat()
        existing = self.execution_store.get(execution_id) or {}
        tool_calls = existing.get("tool_calls", [])
        tool_call = {
            "tool_id": tool_id,
            "title": tool_meta.get("display_name", tool_id),
            "status": status,
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_ms": self._duration_ms(started_at, ended_at),
            "input_preview": input_preview,
            "output_preview": output_preview,
            "source_labels": [tool_meta.get("data_source", "internal")],
            "error": error,
        }
        tool_calls.append(tool_call)
        self.execution_store.set_tool_calls(execution_id, tool_calls)
        self.execution_store.add_event(execution_id, "tool_finished", tool_call)
        if error:
            raise RuntimeError(error)
        return result

    def _build_result_blocks(
        self,
        *,
        mission_type: str,
        task_intent: TaskIntent,
        context: Dict[str, Any],
        report: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        mission_block = AgentResultBlock(
            block_type="mission",
            title="任务理解",
            summary=f"识别为 {mission_type}，聚焦 {task_intent.topic or ', '.join(task_intent.focus_assets + task_intent.focus_themes) or '全市场'}。",
            data={
                "mission_type": mission_type,
                "query": task_intent.query,
                "time_window": task_intent.time_window,
                "focus_assets": task_intent.focus_assets,
                "focus_themes": task_intent.focus_themes,
            },
            key_points=[
                f"时间范围：{task_intent.time_window}",
                f"关注资产：{', '.join(task_intent.focus_assets) if task_intent.focus_assets else '未指定'}",
                f"关注主题：{', '.join(task_intent.focus_themes) if task_intent.focus_themes else '未指定'}",
            ],
            next_actions=[],
            source_labels=["任务理解"],
            tool_trace_refs=[],
        ).to_dict()

        plan_block = AgentResultBlock(
            block_type="execution_plan",
            title="执行计划",
            summary="本轮会按顺序调用平台能力，先拿画像，再补齐新闻/市场/分析证据。",
            data={"tool_sequence": [call["tool_id"] for call in tool_calls]},
            key_points=[call["title"] for call in tool_calls[:6]],
            next_actions=[],
            source_labels=["Agent Orchestrator"],
            tool_trace_refs=[call["tool_id"] for call in tool_calls],
        ).to_dict()

        trace_block = AgentResultBlock(
            block_type="execution_trace",
            title="执行轨迹",
            summary=f"本轮共调用 {len(tool_calls)} 个工具，所有关键步骤都可追溯。",
            data=tool_calls,
            key_points=[
                f"{call['title']} · {call['status']} · {call['duration_ms']}ms"
                for call in tool_calls[:6]
            ],
            next_actions=[],
            source_labels=["工具调用"],
            tool_trace_refs=[call["tool_id"] for call in tool_calls],
        ).to_dict()

        evidence_items = report.get("evidence_items", [])
        evidence_ids = [item.get("id") for item in evidence_items if isinstance(item, dict) and item.get("id")]
        result_block = AgentResultBlock(
            block_type="result",
            title="结果输出",
            summary=report.get("summary", self._default_reply(mission_type)),
            data={
                "key_findings": report.get("key_findings", []),
                "evidence_items": evidence_items,
                "risks": report.get("risks", []),
            },
            key_points=report.get("key_findings", []),
            risk_notes=report.get("risks", []),
            next_actions=report.get("recommended_actions", []),
            evidence_news_ids=evidence_ids,
            source_labels=sorted({label for call in tool_calls for label in call.get("source_labels", [])}),
            tool_trace_refs=[call["tool_id"] for call in tool_calls],
        ).to_dict()

        actions_block = AgentResultBlock(
            block_type="recommended_actions",
            title="下一步动作",
            summary="你可以沿着当前证据链继续追问，而不需要重新开始。",
            data={"actions": report.get("recommended_actions", [])},
            key_points=report.get("recommended_actions", []),
            next_actions=report.get("recommended_actions", []),
            source_labels=["连续研究"],
            tool_trace_refs=[],
        ).to_dict()

        return [mission_block, plan_block, trace_block, result_block, actions_block]

    def _build_execution_state(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "status": "completed",
            "tool_count": len(tool_calls),
            "tool_titles": [call.get("title") for call in tool_calls if call.get("title")],
        }

    def _build_structured_query(
        self,
        task_intent: TaskIntent,
        mission_type: str,
        context: Dict[str, Any],
        message: str,
    ) -> Optional[Dict[str, Any]]:
        if mission_type != "news_retrieval":
            return None
        search_payload = context.get("news.search") or {}
        return {
            "intent_type": "news_retrieval",
            "query": task_intent.query or message,
            "keywords": [search_payload.get("keyword")] if search_payload.get("keyword") else [],
            "assets": task_intent.focus_assets,
            "themes": task_intent.focus_themes,
            "time_range": task_intent.time_window,
            "sort_by": "relevance",
            "need_summary": True,
        }

    def _build_final_answer(
        self,
        *,
        mission_type: str,
        task_intent: TaskIntent,
        context: Dict[str, Any],
        report: Dict[str, Any],
        structured_query: Optional[Dict[str, Any]],
    ) -> str:
        if mission_type == "news_retrieval":
            items = ((context.get("news.search") or {}).get("items") or [])[:6]
            query_target = " / ".join(task_intent.focus_assets + task_intent.focus_themes) or task_intent.topic or "相关主题"
            time_label = task_intent.time_window or "最近窗口"
            if not items:
                return (
                    f"近 {time_label} 内没有找到与 **{query_target}** 明确相关的新闻。\n\n"
                    "可以继续缩小或放宽条件，例如改成具体币种、主题，或把时间窗口切到 30 天。"
                )
            lines = [
                f"近 **{time_label}** 内共筛出 **{len(items)}** 条与 **{query_target}** 相关的新闻，先看这几条：",
                "",
            ]
            for item in items[:5]:
                title = item.get("title") or "未命名资讯"
                summary = item.get("summary") or item.get("text") or item.get("original_text") or ""
                summary = str(summary).strip().replace("\n", " ")
                summary = (summary[:120] + "…") if len(summary) > 120 else summary
                lines.append(f"- **{title}**")
                if summary:
                    lines.append(f"  - {summary}")
            lines.append("")
            lines.append("点开新闻可查看原文、关键词、币种和关联内容。")
            return "\n".join(lines)

        llm_markdown = self._maybe_llm_synthesize_markdown(
            mission_type=mission_type,
            task_intent=task_intent,
            context=context,
            report=report,
        )
        if llm_markdown:
            return llm_markdown

        summary = report.get("summary") or self._default_reply(mission_type)
        key_findings = report.get("key_findings") or []
        risks = report.get("risks") or []
        actions = report.get("recommended_actions") or []
        lines = [summary]
        if key_findings:
            lines.extend(["", "## 结论", *[f"- {item}" for item in key_findings[:4]]])
        if risks:
            lines.extend(["", "## 风险", *[f"- {item}" for item in risks[:2]]])
        if actions:
            lines.extend(["", "## 下一步", *[f"- {item}" for item in actions[:3]]])
        return "\n".join(lines)

    def _build_answer_blocks(
        self,
        *,
        mission_type: str,
        task_intent: TaskIntent,
        context: Dict[str, Any],
        report: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        if mission_type == "news_retrieval":
            items = ((context.get("news.search") or {}).get("items") or [])[:8]
            return [{
                "type": "news_list",
                "title": "筛选结果",
                "items": [self._normalize_news_item(item) for item in items],
            }]

        if mission_type == "news_recommendation":
            items = ((context.get("news.recommend") or {}).get("recommended_news") or [])[:6]
            return [{
                "type": "news_list",
                "title": "推荐新闻",
                "items": [self._normalize_news_item(item) for item in items],
            }]

        if mission_type == "market_briefing":
            snapshot = ((context.get("market.snapshot") or {}).get("snapshot") or {})
            news_items = ((context.get("news.search") or {}).get("items") or [])[:4]
            return [
                {
                    "type": "market_snapshot",
                    "title": "市场快照",
                    "summary": report.get("summary"),
                    "data": snapshot,
                },
                {
                    "type": "news_list",
                    "title": "相关资讯",
                    "items": [self._normalize_news_item(item) for item in news_items],
                },
            ]

        if mission_type == "theme_deep_dive":
            news_items = ((context.get("news.search") or {}).get("items") or [])[:5]
            keywords = ((context.get("news.similar_keywords") or {}).get("similar_keywords") or [])[:6]
            return [
                {
                    "type": "keyword_list",
                    "title": "相关关键词",
                    "items": keywords,
                },
                {
                    "type": "news_list",
                    "title": "主题相关资讯",
                    "items": [self._normalize_news_item(item) for item in news_items],
                },
            ]

        if mission_type == "opportunity_scan":
            opportunities = ((context.get("market.opportunity_scan") or {}).get("opportunities") or [])[:6]
            return [{
                "type": "opportunity_list",
                "title": "观察名单",
                "items": opportunities,
            }]

        evidence_items = report.get("evidence_items") or []
        normalized_news = [self._normalize_news_item(item) for item in evidence_items if isinstance(item, dict) and (item.get("title") or item.get("id"))]
        blocks: List[Dict[str, Any]] = []
        if normalized_news:
            blocks.append({
                "type": "news_list",
                "title": "相关内容",
                "items": normalized_news[:6],
            })
        return blocks

    def _normalize_news_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id"),
            "title": item.get("title") or item.get("text") or "未命名资讯",
            "summary": item.get("summary") or item.get("abstract") or item.get("text") or item.get("original_text") or "",
            "date": item.get("date"),
            "url": item.get("url"),
            "keyword_list": item.get("keyword_list") or item.get("keywords") or [],
            "currency_list": item.get("currency_list") or item.get("currency") or [],
            "source_badge": item.get("source_badge") or item.get("source_label") or "Crypto",
        }

    def _maybe_llm_synthesize_markdown(
        self,
        *,
        mission_type: str,
        task_intent: TaskIntent,
        context: Dict[str, Any],
        report: Dict[str, Any],
    ) -> Optional[str]:
        if mission_type not in {"market_briefing", "theme_deep_dive", "opportunity_scan", "report_generation"}:
            return None
        provider = self._get_llm_provider()
        if not provider:
            return None
        prompt_context = {
            "mission_type": mission_type,
            "query": task_intent.query,
            "time_window": task_intent.time_window,
            "focus_assets": task_intent.focus_assets,
            "focus_themes": task_intent.focus_themes,
            "report": report,
            "news_items": ((context.get("news.search") or {}).get("items") or [])[:4],
            "market_snapshot": (context.get("market.snapshot") or {}).get("snapshot"),
            "similar_keywords": (context.get("news.similar_keywords") or {}).get("similar_keywords"),
            "opportunities": (context.get("market.opportunity_scan") or {}).get("opportunities"),
        }
        messages = [
            LLMMessage(
                role="system",
                content=(
                    "你是一个加密研究助理。请基于提供的结构化事实生成简洁的中文 markdown 回答。"
                    "不要虚构数据；不要描述内部工具编排；直接给结论、证据和下一步。"
                ),
            ),
            LLMMessage(
                role="user",
                content=(
                    "请把下面的结构化上下文整理成正常聊天回答，使用 markdown。\n"
                    f"{json.dumps(prompt_context, ensure_ascii=False)}"
                ),
            ),
        ]
        try:
            response = provider.chat(messages, temperature=0.2, max_tokens=700)
            content = (response.content or "").strip()
            return content or None
        except Exception as exc:
            logger.warning("LLM synthesis failed, falling back to template: %s", exc)
            return None

    def _build_execution_trace_summary(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "total_tools": len(tool_calls),
            "completed_tools": sum(1 for call in tool_calls if call.get("status") == "completed"),
            "failed_tools": sum(1 for call in tool_calls if call.get("status") == "failed"),
            "tool_titles": [call.get("title") for call in tool_calls],
        }

    def _build_data_freshness(self, context: Dict[str, Any]) -> Dict[str, Any]:
        recommendation_status = (context.get("news.recommend") or {}).get("recommendation_status", {})
        snapshot = ((context.get("market.snapshot") or {}).get("snapshot") or {})
        return {
            "recommendations": recommendation_status,
            "market_snapshot_last_updated": snapshot.get("last_updated"),
        }

    def _plan_capability_labels(self, tool_sequence: List[str]) -> List[str]:
        mapping = {
            "profile.read": "读取画像",
            "news.recommend": "个性化推荐",
            "news.search": "新闻搜索",
            "news.similar_keywords": "相关关键词",
            "analysis.keyword_trend": "趋势分析",
            "analysis.news_correlation": "新闻与市场关联",
            "market.snapshot": "实时市场快照",
            "market.asset_detail": "资产详情",
            "market.opportunity_scan": "机会扫描",
            "report.compose": "报告生成",
        }
        return [mapping[tool_id] for tool_id in tool_sequence if tool_id in mapping]

    def _build_memory_update(self, task_intent: TaskIntent, short_term_memory: Dict[str, Any]) -> Dict[str, Any]:
        updated = dict(short_term_memory or {})
        updated["last_task_type"] = task_intent.task_type
        updated["time_window"] = task_intent.time_window
        if task_intent.focus_assets:
            updated["focus_assets"] = task_intent.focus_assets
        if task_intent.focus_themes:
            updated["focus_themes"] = task_intent.focus_themes
        if task_intent.topic:
            updated["last_topic"] = task_intent.topic
        updated["output_format"] = task_intent.output_format
        return updated

    def _extract_assets(self, text: str) -> List[str]:
        asset_patterns = {
            "BTC": ["btc", "bitcoin", "比特币"],
            "ETH": ["eth", "ethereum", "以太坊"],
            "SOL": ["sol", "solana"],
            "ETF": ["etf"],
            "AI": ["ai"],
        }
        lowered = text.lower()
        return [asset for asset, patterns in asset_patterns.items() if any(pattern in lowered for pattern in patterns)]

    def _extract_themes(self, text: str) -> List[str]:
        theme_patterns = {
            "AI": ["ai", "agent", "智能体"],
            "ETF": ["etf"],
            "DeFi": ["defi"],
            "infra": ["infra", "基础设施", "layer2", "模块化"],
            "macro": ["宏观", "美联储", "利率", "macro"],
        }
        lowered = text.lower()
        return [theme for theme, patterns in theme_patterns.items() if any(pattern in lowered for pattern in patterns)]

    def _pick_search_keyword(self, task_intent: TaskIntent, mission_type: str, message: str) -> str:
        if task_intent.topic:
            return task_intent.topic
        if task_intent.focus_assets:
            return " ".join(task_intent.focus_assets[:2])
        if task_intent.focus_themes:
            return " ".join(task_intent.focus_themes[:2])
        if mission_type == "market_briefing":
            return "bitcoin ethereum crypto market"
        if mission_type == "opportunity_scan":
            return "btc eth sol ai defi"
        return (message or "bitcoin").strip()

    def _parse_days(self, window: str) -> int:
        if not window:
            return 1
        match = re.match(r"(\d+)([hd天小时]+)", str(window))
        if not match:
            return 1
        count = int(match.group(1))
        unit = match.group(2)
        if "h" in unit or "小时" in unit:
            return max(1, count // 24 or 1)
        return max(1, count)

    def _preview_data(self, data: Any) -> str:
        if isinstance(data, dict):
            keys = list(data.keys())[:6]
            fragments = []
            for key in keys:
                value = data[key]
                if isinstance(value, list):
                    fragments.append(f"{key}={len(value)} items")
                elif isinstance(value, dict):
                    fragments.append(f"{key}={','.join(list(value.keys())[:3])}")
                else:
                    fragments.append(f"{key}={str(value)[:48]}")
            return "; ".join(fragments)
        if isinstance(data, list):
            return f"{len(data)} items"
        return str(data)[:180]

    def _duration_ms(self, started_at: str, ended_at: str) -> int:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(ended_at)
        return int((end - start).total_seconds() * 1000)

    def _default_reply(self, mission_type: str) -> str:
        mapping = {
            "news_recommendation": "我已经结合你的画像完成一轮新闻推荐。",
            "market_briefing": "我已经完成一轮市场 briefing。",
            "theme_deep_dive": "我已经完成一轮主题深挖。",
            "opportunity_scan": "我已经完成一轮机会扫描。",
            "report_generation": "我已经整理出一份研究摘要。",
        }
        return mapping.get(mission_type, "我已经处理完当前任务。")

    def get_conversations(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        try:
            conversations = self.conversation_repo.get_by_user(user_id=user_id, limit=limit, offset=offset)
            return [conv.to_dict() for conv in conversations]
        except Exception as e:
            logger.error("Get conversations error: %s", e)
            return []

    def get_conversation_messages(self, conversation_id: int) -> List[Dict[str, Any]]:
        try:
            messages = self.conversation_repo.get_messages(conversation_id)
            return [msg.to_dict() for msg in messages]
        except Exception as e:
            logger.error("Get messages error: %s", e)
            return []

    def delete_conversation(self, conversation_id: int) -> bool:
        try:
            return self.conversation_repo.delete_conversation(conversation_id)
        except Exception as e:
            logger.error("Delete conversation error: %s", e)
            return False

    def get_conversation_with_messages(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        try:
            conversation = self.conversation_repo.get_by_id(conversation_id)
            if not conversation:
                return None
            messages = self.conversation_repo.get_messages(conversation_id)
            return {
                "conversation": conversation.to_dict(),
                "messages": [msg.to_dict() for msg in messages],
            }
        except Exception as e:
            logger.error("Get conversation with messages error: %s", e)
            return None

    def execute_skill(
        self,
        user_id: str,
        skill_name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            logger.info("Executing skill: %s for user %s", skill_name, user_id)
            skill_executor = get_skill_executor()
            result = skill_executor.execute_skill(skill_name, params or {})
            return {
                "success": result.success,
                "skill_name": result.skill_name,
                "final_report": result.final_report,
                "structured_output": result.structured_output,
                "steps": [
                    {
                        "name": step.name,
                        "description": step.description,
                        "completed": step.completed,
                        "error": step.error,
                        "tool_name": step.tool_name,
                    }
                    for step in result.steps
                ],
                "started_at": result.started_at,
                "completed_at": result.completed_at,
                "metadata": result.metadata,
            }
        except Exception as e:
            logger.error("Execute skill error: %s", e, exc_info=True)
            return {
                "success": False,
                "skill_name": skill_name,
                "final_report": f"技能执行失败：{str(e)}",
                "steps": [],
                "error": str(e),
            }

    def list_skills(self) -> List[Dict[str, str]]:
        try:
            skill_executor = get_skill_executor()
            skills = skill_executor.list_skills()
            return [{"name": name, "description": description} for name, description in skills.items()]
        except Exception as e:
            logger.error("List skills error: %s", e)
            return []

    def get_skill_info(self, skill_name: str) -> Optional[Dict[str, Any]]:
        try:
            skill_executor = get_skill_executor()
            skill = skill_executor.get_skill(skill_name)
            if not skill:
                return None
            return {
                "name": skill.name,
                "description": skill.description,
                "steps": [],
            }
        except Exception as e:
            logger.error("Get skill info error: %s", e)
            return None

    def list_capabilities(self) -> List[Dict[str, Any]]:
        return [
            {
                "group": "看新闻",
                "items": [
                    {
                        "id": "news_recommendation",
                        "title": "推荐适合我的新闻",
                        "description": "根据画像与历史/实时数据返回最值得先看的资讯",
                        "sample_prompts": [
                            "过去 12 小时适合我的新闻",
                            "优先看 BTC 和 AI 的变化",
                        ],
                        "backed_by_tools": ["profile.read", "news.recommend", "report.compose"],
                        "result_type": "briefing",
                        "code_roles": ["候选召回", "画像打分", "历史兜底"],
                        "llm_roles": ["推荐理由生成", "结果表达"],
                    },
                    {
                        "id": "news_search",
                        "title": "按关键词查新闻",
                        "description": "围绕资产、主题和时间窗口搜索新闻",
                        "sample_prompts": [
                            "搜索过去 7 天的 DeFi 新闻",
                            "只看 ETH 的相关新闻",
                        ],
                        "backed_by_tools": ["news.search", "news.filter"],
                        "result_type": "news_list",
                        "code_roles": ["规则解析", "结构化检索", "过滤与排序"],
                        "llm_roles": ["复杂自然语言解析 fallback"],
                    },
                ],
            },
            {
                "group": "查关键词",
                "items": [
                    {
                        "id": "theme_deep_dive",
                        "title": "围绕主题深挖",
                        "description": "扩展相关关键词并查看趋势与关联",
                        "sample_prompts": [
                            "围绕 DeFi 深挖",
                            "AI Agent 主题最近怎么演化",
                        ],
                        "backed_by_tools": ["news.search", "news.similar_keywords", "analysis.keyword_trend", "analysis.news_correlation"],
                        "result_type": "report",
                        "code_roles": ["检索", "相关词扩展", "趋势与相关性计算"],
                        "llm_roles": ["主题定义", "结论提炼", "markdown 总结"],
                    }
                ],
            },
            {
                "group": "看市场",
                "items": [
                    {
                        "id": "market_briefing",
                        "title": "分析今天市场局势",
                        "description": "结合 Fear & Greed、市场看板与新闻证据给出结论",
                        "sample_prompts": [
                            "分析今天市场局势",
                            "给我 3 个最重要的市场结论",
                        ],
                        "backed_by_tools": ["market.snapshot", "news.search", "analysis.keyword_trend", "report.compose"],
                        "result_type": "market",
                        "code_roles": ["行情采集", "新闻聚合", "基础统计"],
                        "llm_roles": ["市场结论", "驱动因素归纳", "风险总结"],
                    },
                    {
                        "id": "asset_detail",
                        "title": "查看单资产行情详情",
                        "description": "获取单资产的实时行情与相关新闻联动",
                        "sample_prompts": [
                            "BTC 现在值得关注吗",
                            "ETH 最近的市场和新闻联动如何",
                        ],
                        "backed_by_tools": ["market.asset_detail", "analysis.news_correlation"],
                        "result_type": "market",
                        "code_roles": ["单资产行情与联动查询"],
                        "llm_roles": ["解释型回答"],
                    },
                ],
            },
            {
                "group": "找机会",
                "items": [
                    {
                        "id": "opportunity_scan",
                        "title": "找短线高波动机会",
                        "description": "接入 AlphaHunter 做机会扫描并返回证据",
                        "sample_prompts": [
                            "帮我找短线高波动机会",
                            "扫描今天的 Alpha 候选",
                        ],
                        "backed_by_tools": ["market.opportunity_scan", "news.search", "report.compose"],
                        "result_type": "opportunity",
                        "code_roles": ["候选生成", "波动筛选", "证据交叉"],
                        "llm_roles": ["机会解释", "风险说明", "观察条件总结"],
                    }
                ],
            },
            {
                "group": "做报告",
                "items": [
                    {
                        "id": "report_generation",
                        "title": "生成研究简报",
                        "description": "将新闻、市场和画像上下文整合成可展示的结论",
                        "sample_prompts": [
                            "生成一份个性化市场简报",
                            "把上面的结论整理成 briefing",
                        ],
                        "backed_by_tools": ["profile.read", "market.snapshot", "news.recommend", "report.compose"],
                        "result_type": "report",
                        "code_roles": ["上下文聚合", "事实整理"],
                        "llm_roles": ["简报写作", "结构化 markdown 输出"],
                    }
                ],
            },
        ]

    def list_tools(self) -> List[Dict[str, Any]]:
        return self.tool_registry.list_tools()

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        return self.execution_store.get(execution_id)
