"""
News Agent
新闻搜索专家Agent
"""
import logging
import re
from typing import Dict, Any

from .base import BaseAgent
from .state import AgentState
from src.ai.llm.base import LLMMessage
from src.ai.tools.news_tools import NewsSearchTool

logger = logging.getLogger(__name__)


class NewsAgent(BaseAgent):
    """新闻Agent"""

    def __init__(self, llm):
        super().__init__("NewsAgent", llm)
        self.news_tool = NewsSearchTool()

    def process(self, state: AgentState) -> AgentState:
        """
        处理新闻搜索请求

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("NewsAgent processing request...")

        # 获取用户消息
        user_message = ""
        for msg in reversed(state["messages"]):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        # 提取关键词
        keyword = self._extract_keyword(user_message)

        logger.info(f"Extracted keyword: {keyword}")

        # 使用工具搜索新闻
        tool_result = self.news_tool.execute(keyword=keyword, days=7, limit=5)

        state["tool_results"].append({
            "tool": "news_search",
            "result": tool_result.to_dict()
        })

        # 生成响应
        if tool_result.success and tool_result.data:
            response = self._format_news_response(tool_result.data, keyword)
        else:
            response = f"抱歉，没有找到关于'{keyword}'的新闻。"

        state = self._add_message(state, "assistant", response)
        state["current_agent"] = "news_agent"
        state["final_response"] = response
        state["next_action"] = "end"

        return state

    def _extract_keyword(self, text: str) -> str:
        """从用户消息中提取搜索关键词。"""
        stop_phrases = [
            "最新新闻", "最新消息", "有什么", "请问", "帮我", "看看", "关于", "有关",
            "新闻", "消息", "资讯", "分析", "趋势", "市场", "最新", "一下"
        ]
        cleaned = text.strip()
        for phrase in stop_phrases:
            cleaned = cleaned.replace(phrase, " ")
        cleaned = re.sub(r"[^\w\u4e00-\u9fff#@+-]+", " ", cleaned)
        tokens = [token.strip() for token in cleaned.split() if len(token.strip()) > 1]
        if tokens:
            return tokens[0]

        cjk_chunks = re.findall(r"[\u4e00-\u9fffA-Za-z0-9+#@-]{2,}", text)
        if cjk_chunks:
            return cjk_chunks[0]
        return text[:10]

    def _format_news_response(self, news_list: list, keyword: str) -> str:
        """格式化新闻响应"""
        response = f"找到了 {len(news_list)} 条关于'{keyword}'的新闻：\n\n"

        for i, news in enumerate(news_list, 1):
            response += f"{i}. {news.get('title', 'N/A')}\n"
            response += f"   日期: {news.get('date', 'N/A')}\n"
            response += f"   摘要: {news.get('text', 'N/A')}\n\n"

        return response.strip()

    def _get_system_prompt(self) -> str:
        return "你是新闻搜索专家，帮助用户查找和理解新闻。"
