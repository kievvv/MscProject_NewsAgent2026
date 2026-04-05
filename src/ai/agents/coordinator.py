"""
Coordinator Agent
协调器Agent，负责意图识别和路由
"""
import logging
from typing import Dict, Any

from .base import BaseAgent
from .state import AgentState
from src.ai.llm.base import LLMMessage

logger = logging.getLogger(__name__)


class CoordinatorAgent(BaseAgent):
    """协调器Agent"""

    def __init__(self, llm):
        super().__init__("Coordinator", llm)

    def process(self, state: AgentState) -> AgentState:
        """
        分析用户意图并路由到相应的专家Agent

        Args:
            state: 当前状态

        Returns:
            更新后的状态，包含next_action
        """
        logger.info("Coordinator analyzing user intent...")

        # 获取最后一条用户消息
        user_message = ""
        for msg in reversed(state["messages"]):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        # 构建意图识别提示
        system_prompt = """你是一个意图识别专家。请分析用户消息并判断用户意图，返回以下类别之一：

- news: 用户想搜索或查看新闻（例如："最新的比特币新闻"、"关于DeFi的消息"、"有什么新闻"）
- analysis: 用户想分析趋势或关键词（例如："分析一下以太坊的趋势"、"提取关键词"、"热度分析"）
- market: 用户想查看市场数据或情绪（例如："市场行情如何"、"恐慌贪婪指数"、"价格走势"、"币价"）
- profile: 用户想管理个人偏好或查看画像（例如："我的设置"、"我关注比特币"、"推荐内容"、"个人资料"）
- chat: 普通对话或问候（例如："你好"、"谢谢"、"介绍一下自己"）

只返回类别名称，不要有其他内容。"""

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=f"用户消息：{user_message}")
        ]

        try:
            response = self.llm.chat(messages)
            intent = response.content.strip().lower()

            logger.info(f"Detected intent: {intent}")

            # 设置下一步动作
            if intent in ["news", "analysis", "market", "profile"]:
                state["next_action"] = intent
            else:
                state["next_action"] = "chat"

            state["current_agent"] = "coordinator"
            state["context"]["detected_intent"] = intent

            return state

        except Exception as e:
            logger.error(f"Coordinator error: {e}")
            # 默认为聊天
            state["next_action"] = "chat"
            return state

    def _get_system_prompt(self) -> str:
        return "你是协调器，负责理解用户意图并分配任务。"
