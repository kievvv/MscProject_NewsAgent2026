"""
Analysis Agent
分析专家Agent - 处理关键词提取、趋势分析等
"""
import logging
from typing import Dict, Any

from .base import BaseAgent
from .state import AgentState
from src.ai.llm.base import LLMMessage
from src.ai.tools.analysis_tools import KeywordExtractionTool, TrendAnalysisTool

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseAgent):
    """分析Agent"""

    def __init__(self, llm):
        super().__init__("AnalysisAgent", llm)
        self.keyword_tool = KeywordExtractionTool()
        self.trend_tool = TrendAnalysisTool()

    def process(self, state: AgentState) -> AgentState:
        """
        处理分析请求

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("AnalysisAgent processing request...")

        # 获取用户消息
        user_message = ""
        for msg in reversed(state["messages"]):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        # 判断分析类型
        analysis_type = self._detect_analysis_type(user_message)

        logger.info(f"Analysis type: {analysis_type}")

        if analysis_type == "keyword_extraction":
            response = self._handle_keyword_extraction(user_message, state)
        elif analysis_type == "trend_analysis":
            response = self._handle_trend_analysis(user_message, state)
        else:
            # 默认：提取关键词并分析趋势
            response = self._handle_comprehensive_analysis(user_message, state)

        state = self._add_message(state, "assistant", response)
        state["current_agent"] = "analysis_agent"
        state["final_response"] = response
        state["next_action"] = "end"

        return state

    def _detect_analysis_type(self, text: str) -> str:
        """检测分析类型"""
        text_lower = text.lower()

        if any(keyword in text_lower for keyword in ["关键词", "提取", "keyword"]):
            return "keyword_extraction"
        elif any(keyword in text_lower for keyword in ["趋势", "热度", "trend", "分析"]):
            return "trend_analysis"
        else:
            return "comprehensive"

    def _handle_keyword_extraction(self, text: str, state: AgentState) -> str:
        """处理关键词提取"""
        # 从用户消息中提取文本（简化：使用消息本身）
        tool_result = self.keyword_tool.execute(text=text, top_n=10)

        state["tool_results"].append({
            "tool": "keyword_extraction",
            "result": tool_result.to_dict()
        })

        if tool_result.success and tool_result.data:
            keywords = tool_result.data
            response = "我提取出了以下关键词：\n\n"
            for i, kw_dict in enumerate(keywords, 1):
                keyword = kw_dict.get('keyword', 'N/A')
                score = kw_dict.get('score', 0)
                response += f"{i}. {keyword} (相关度: {score:.2f})\n"
        else:
            response = "抱歉，关键词提取失败。"

        return response

    def _handle_trend_analysis(self, text: str, state: AgentState) -> str:
        """处理趋势分析"""
        # 从用户消息中提取关键词
        keyword = self._extract_keyword_from_message(text)

        logger.info(f"Analyzing trend for keyword: {keyword}")

        # 执行趋势分析
        tool_result = self.trend_tool.execute(keyword=keyword, days=30)

        state["tool_results"].append({
            "tool": "trend_analysis",
            "result": tool_result.to_dict()
        })

        if tool_result.success and tool_result.data:
            trend = tool_result.data
            response = self._format_trend_response(trend, keyword)
        else:
            response = f"抱歉，无法分析'{keyword}'的趋势。可能是数据不足。"

        return response

    def _handle_comprehensive_analysis(self, text: str, state: AgentState) -> str:
        """综合分析：提取关键词 + 趋势分析"""
        # 先提取关键词
        kw_result = self.keyword_tool.execute(text=text, top_n=5)

        if not kw_result.success or not kw_result.data:
            return "抱歉，无法进行分析。"

        # 取第一个关键词进行趋势分析
        top_keyword = kw_result.data[0].get('keyword', '')

        trend_result = self.trend_tool.execute(keyword=top_keyword, days=30)

        state["tool_results"].extend([
            {"tool": "keyword_extraction", "result": kw_result.to_dict()},
            {"tool": "trend_analysis", "result": trend_result.to_dict()}
        ])

        # 组合响应
        response = f"📊 综合分析报告\n\n"
        response += f"🔑 核心关键词：{top_keyword}\n\n"

        if trend_result.success and trend_result.data:
            trend = trend_result.data
            response += f"📈 趋势分析（最近30天）：\n"
            response += f"  • 总出现次数：{trend.get('total_count', 0)}\n"
            response += f"  • 活跃天数：{trend.get('active_days', 0)}\n"
            response += f"  • 平均每日：{trend.get('avg_daily_count', 0):.1f} 次\n"
            response += f"  • 峰值日期：{trend.get('peak_date', 'N/A')}\n"
            response += f"  • 峰值次数：{trend.get('peak_count', 0)}\n"
        else:
            response += f"  • 暂无趋势数据\n"

        return response

    def _extract_keyword_from_message(self, text: str) -> str:
        """从用户消息中提取关键词（简化版）"""
        # 去除常见停用词
        stop_words = {
            "的", "了", "吗", "呢", "吧", "啊", "分析", "趋势", "关键词",
            "一下", "帮我", "查看", "看看", "怎么样", "如何"
        }

        words = text.split()
        keywords = [w for w in words if w not in stop_words and len(w) > 1]

        if keywords:
            return keywords[0]
        return text[:10]  # 兜底

    def _format_trend_response(self, trend: dict, keyword: str) -> str:
        """格式化趋势响应"""
        response = f"📈 '{keyword}' 的趋势分析\n\n"
        response += f"📊 统计数据（最近30天）：\n"
        response += f"  • 总出现次数：{trend.get('total_count', 0)}\n"
        response += f"  • 活跃天数：{trend.get('active_days', 0)}\n"
        response += f"  • 平均每日：{trend.get('avg_daily_count', 0):.1f} 次\n"
        response += f"  • 峰值日期：{trend.get('peak_date', 'N/A')}\n"
        response += f"  • 峰值次数：{trend.get('peak_count', 0)}\n\n"

        # 添加趋势走势（最近10天）
        daily_trend = trend.get('daily_trend', [])
        if daily_trend:
            response += "📉 最近走势：\n"
            for day_data in daily_trend[:10]:
                date = day_data.get('date', 'N/A')
                count = day_data.get('count', 0)
                bar = "█" * min(count, 20)  # 简单的条形图
                response += f"  {date}: {bar} ({count})\n"

        return response

    def _get_system_prompt(self) -> str:
        return "你是分析专家，擅长关键词提取和趋势分析。"
