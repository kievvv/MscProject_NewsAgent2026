"""
Agent Graph
使用LangGraph构建多Agent状态机
"""
import logging
from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, END
from .state import AgentState
from .coordinator import CoordinatorAgent
from .news_agent import NewsAgent
from .analysis_agent import AnalysisAgent
from .trade_agent import TradeAgent
from .profile_agent import UserProfileAgent
from src.ai.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)


def route_agent(state: AgentState) -> Literal["news_agent", "analysis_agent", "trade_agent", "profile_agent", "chat_agent", "end"]:
    """
    路由函数：根据next_action决定下一个节点

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    next_action = state.get("next_action", "end")

    logger.info(f"Routing to: {next_action}")

    if next_action == "news":
        return "news_agent"
    elif next_action == "analysis":
        return "analysis_agent"
    elif next_action == "market":
        return "trade_agent"
    elif next_action == "profile":
        return "profile_agent"
    elif next_action == "chat":
        return "chat_agent"
    else:
        return "end"


def coordinator_node(state: AgentState) -> AgentState:
    """协调器节点"""
    llm = get_llm_provider()
    coordinator = CoordinatorAgent(llm)
    return coordinator.process(state)


def news_agent_node(state: AgentState) -> AgentState:
    """新闻Agent节点"""
    llm = get_llm_provider()
    news_agent = NewsAgent(llm)
    return news_agent.process(state)


def analysis_agent_node(state: AgentState) -> AgentState:
    """分析Agent节点"""
    llm = get_llm_provider()
    analysis_agent = AnalysisAgent(llm)
    return analysis_agent.process(state)


def trade_agent_node(state: AgentState) -> AgentState:
    """交易Agent节点"""
    llm = get_llm_provider()
    trade_agent = TradeAgent(llm)
    return trade_agent.process(state)


def profile_agent_node(state: AgentState) -> AgentState:
    """用户画像Agent节点"""
    llm = get_llm_provider()
    profile_agent = UserProfileAgent(llm)
    return profile_agent.process(state)


def chat_agent_node(state: AgentState) -> AgentState:
    """聊天Agent节点（简化版）"""
    logger.info("ChatAgent processing...")

    # 简单响应
    user_message = ""
    for msg in reversed(state["messages"]):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break

    # 生成简单回复
    llm = get_llm_provider()
    from src.ai.llm.base import LLMMessage

    messages = [
        LLMMessage(role="system", content="你是一个友好的助手。请简短回复用户。"),
        LLMMessage(role="user", content=user_message)
    ]

    response = llm.chat(messages)
    reply = response.content

    state["messages"].append({"role": "assistant", "content": reply})
    state["current_agent"] = "chat_agent"
    state["final_response"] = reply
    state["next_action"] = "end"

    return state


def create_agent_graph() -> StateGraph:
    """
    创建Agent状态机图

    Returns:
        配置好的StateGraph
    """
    logger.info("Creating agent graph...")

    # 创建图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("coordinator", coordinator_node)
    workflow.add_node("news_agent", news_agent_node)
    workflow.add_node("analysis_agent", analysis_agent_node)
    workflow.add_node("trade_agent", trade_agent_node)
    workflow.add_node("profile_agent", profile_agent_node)
    workflow.add_node("chat_agent", chat_agent_node)

    # 设置入口点
    workflow.set_entry_point("coordinator")

    # 添加条件边：从coordinator路由到不同的agent
    workflow.add_conditional_edges(
        "coordinator",
        route_agent,
        {
            "news_agent": "news_agent",
            "analysis_agent": "analysis_agent",
            "trade_agent": "trade_agent",
            "profile_agent": "profile_agent",
            "chat_agent": "chat_agent",
            "end": END
        }
    )

    # 所有agent处理完后都结束
    workflow.add_edge("news_agent", END)
    workflow.add_edge("analysis_agent", END)
    workflow.add_edge("trade_agent", END)
    workflow.add_edge("profile_agent", END)
    workflow.add_edge("chat_agent", END)

    # 编译图
    app = workflow.compile()

    logger.info("Agent graph created successfully")

    return app
