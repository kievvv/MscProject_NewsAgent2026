"""
Base Agent Class
所有Agent的基类
"""
import logging
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from src.ai.llm.base import BaseLLMProvider, LLMMessage
from .state import AgentState

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Agent基类"""

    def __init__(self, name: str, llm: BaseLLMProvider):
        self.name = name
        self.llm = llm
        logger.info(f"Initialized agent: {name}")

    @abstractmethod
    def process(self, state: AgentState) -> AgentState:
        """
        处理状态并返回更新后的状态

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        pass

    def _format_messages_for_llm(self, state: AgentState) -> List[LLMMessage]:
        """将状态中的消息格式化为LLM消息"""
        return [
            LLMMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", "")
            )
            for msg in state["messages"]
        ]

    def _add_message(self, state: AgentState, role: str, content: str) -> AgentState:
        """添加消息到状态"""
        state["messages"].append({"role": role, "content": content})
        return state

    def _get_system_prompt(self) -> str:
        """获取系统提示词（子类可覆盖）"""
        return f"你是一个智能助手，名字是{self.name}。"
