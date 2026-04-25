"""
Agent State Definition
定义Agent系统的状态结构
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from operator import add


class AgentState(TypedDict):
    """
    Agent状态定义

    用于在LangGraph节点间传递状态
    """
    # 消息历史
    messages: Annotated[List[Dict[str, str]], add]

    # 用户信息
    user_id: str
    conversation_id: Optional[int]

    # 当前处理的Agent
    current_agent: Optional[str]

    # 上下文信息
    context: Dict[str, Any]

    # 任务意图
    task_intent: Dict[str, Any]

    # 工具执行结果
    tool_results: List[Dict[str, Any]]

    # 下一步动作
    next_action: Optional[str]

    # 用户画像
    user_profile: Optional[Dict[str, Any]]

    # 短期记忆
    short_term_memory: Optional[Dict[str, Any]]

    # 最终响应
    final_response: Optional[str]


def create_initial_state(
    user_id: str,
    user_message: str,
    conversation_id: Optional[int] = None,
    user_profile: Optional[Dict[str, Any]] = None,
    short_term_memory: Optional[Dict[str, Any]] = None,
    task_intent: Optional[Dict[str, Any]] = None,
) -> AgentState:
    """
    创建初始状态

    Args:
        user_id: 用户ID
        user_message: 用户消息
        conversation_id: 对话ID
        user_profile: 用户画像

    Returns:
        初始AgentState
    """
    return AgentState(
        messages=[{"role": "user", "content": user_message}],
        user_id=user_id,
        conversation_id=conversation_id,
        current_agent=None,
        context={},
        task_intent=task_intent or {},
        tool_results=[],
        next_action="route",
        user_profile=user_profile or {},
        short_term_memory=short_term_memory or {},
        final_response=None
    )
