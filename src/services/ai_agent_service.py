"""
AI Agent Service
高层编排服务，协调Agent系统和数据持久化
"""
import logging
from typing import Optional, Dict, Any, List

from src.ai.agents.graph import create_agent_graph
from src.ai.agents.state import create_initial_state
from src.ai.skills.executor import get_skill_executor
from src.data.repositories.conversation import ConversationRepository
from src.data.repositories.user_profile import UserProfileRepository
from src.core.models import Conversation, Message

logger = logging.getLogger(__name__)


class AIAgentService:
    """AI Agent编排服务"""

    def __init__(self):
        self.conversation_repo = ConversationRepository()
        self.user_profile_repo = UserProfileRepository()
        self.agent_graph = None

    def _get_agent_graph(self):
        """延迟加载Agent图"""
        if self.agent_graph is None:
            self.agent_graph = create_agent_graph()
        return self.agent_graph

    def chat(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        处理用户消息

        Args:
            user_id: 用户ID
            message: 用户消息
            conversation_id: 对话ID（可选，如果为None则创建新对话）

        Returns:
            响应字典，包含reply和conversation_id
        """
        try:
            logger.info(f"Processing chat for user {user_id}")

            # 获取或创建用户画像
            user_profile = self.user_profile_repo.get_or_create(user_id)
            self.user_profile_repo.update_last_active(user_id)

            # 获取或创建对话
            if conversation_id:
                conversation = self.conversation_repo.get_by_id(conversation_id)
                if not conversation:
                    raise ValueError(f"Conversation {conversation_id} not found")
            else:
                # 创建新对话
                conversation = self.conversation_repo.create_conversation(
                    user_id=user_id,
                    title=message[:50]  # 使用前50个字符作为标题
                )
                conversation_id = conversation.id
                self.user_profile_repo.increment_conversation_count(user_id)

            # 保存用户消息
            self.conversation_repo.add_message(
                conversation_id=conversation_id,
                role="user",
                content=message
            )

            # 获取对话历史（最近10条）
            history_messages = self.conversation_repo.get_messages(
                conversation_id=conversation_id,
                limit=10
            )

            # 创建初始状态
            initial_state = create_initial_state(
                user_id=user_id,
                user_message=message,
                conversation_id=conversation_id,
                user_profile=user_profile.preferences
            )

            # 执行Agent图
            logger.info("Executing agent graph...")
            graph = self._get_agent_graph()
            final_state = graph.invoke(initial_state)

            # 获取响应
            reply = final_state.get("final_response", "抱歉，我遇到了一些问题。")

            # 保存助手消息
            self.conversation_repo.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=reply,
                agent_name=final_state.get("current_agent")
            )

            logger.info("Chat processed successfully")

            return {
                'success': True,
                'reply': reply,
                'conversation_id': conversation_id,
                'agent': final_state.get("current_agent"),
                'tool_results': final_state.get("tool_results", [])
            }

        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            return {
                'success': False,
                'reply': f"抱歉，处理您的请求时出错了：{str(e)}",
                'conversation_id': conversation_id,
                'error': str(e)
            }

    def get_conversations(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取用户对话列表

        Args:
            user_id: 用户ID
            limit: 限制数量
            offset: 偏移量

        Returns:
            对话列表
        """
        try:
            conversations = self.conversation_repo.get_by_user(
                user_id=user_id,
                limit=limit,
                offset=offset
            )

            return [conv.to_dict() for conv in conversations]

        except Exception as e:
            logger.error(f"Get conversations error: {e}")
            return []

    def get_conversation_messages(
        self,
        conversation_id: int
    ) -> List[Dict[str, Any]]:
        """
        获取对话的消息列表

        Args:
            conversation_id: 对话ID

        Returns:
            消息列表
        """
        try:
            messages = self.conversation_repo.get_messages(conversation_id)
            return [msg.to_dict() for msg in messages]

        except Exception as e:
            logger.error(f"Get messages error: {e}")
            return []

    def delete_conversation(self, conversation_id: int) -> bool:
        """删除对话"""
        try:
            return self.conversation_repo.delete_conversation(conversation_id)
        except Exception as e:
            logger.error(f"Delete conversation error: {e}")
            return False

    def get_conversation_with_messages(
        self,
        conversation_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        获取对话详情和消息列表

        Args:
            conversation_id: 对话ID

        Returns:
            包含对话和消息的字典
        """
        try:
            conversation = self.conversation_repo.get_by_id(conversation_id)
            if not conversation:
                return None

            messages = self.conversation_repo.get_messages(conversation_id)

            return {
                'conversation': conversation.to_dict(),
                'messages': [msg.to_dict() for msg in messages]
            }

        except Exception as e:
            logger.error(f"Get conversation with messages error: {e}")
            return None

    def execute_skill(
        self,
        user_id: str,
        skill_name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行技能

        Args:
            user_id: 用户ID
            skill_name: 技能名称
            params: 技能参数

        Returns:
            技能执行结果
        """
        try:
            logger.info(f"Executing skill: {skill_name} for user {user_id}")

            # 获取技能执行器
            skill_executor = get_skill_executor()

            # 执行技能
            result = skill_executor.execute_skill(skill_name, params or {})

            logger.info(f"Skill {skill_name} executed successfully")

            return {
                'success': result.success,
                'skill_name': result.skill_name,
                'final_report': result.final_report,
                'steps': [
                    {
                        'name': step.name,
                        'description': step.description,
                        'completed': step.completed,
                        'error': step.error
                    }
                    for step in result.steps
                ],
                'started_at': result.started_at,
                'completed_at': result.completed_at,
                'metadata': result.metadata
            }

        except Exception as e:
            logger.error(f"Execute skill error: {e}", exc_info=True)
            return {
                'success': False,
                'skill_name': skill_name,
                'final_report': f"技能执行失败：{str(e)}",
                'steps': [],
                'error': str(e)
            }

    def list_skills(self) -> List[Dict[str, str]]:
        """
        获取所有可用技能列表

        Returns:
            技能列表
        """
        try:
            skill_executor = get_skill_executor()
            skills = skill_executor.list_skills()

            return [
                {
                    'name': name,
                    'description': description
                }
                for name, description in skills.items()
            ]

        except Exception as e:
            logger.error(f"List skills error: {e}")
            return []

    def get_skill_info(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """
        获取技能详细信息

        Args:
            skill_name: 技能名称

        Returns:
            技能信息
        """
        try:
            skill_executor = get_skill_executor()
            skill = skill_executor.get_skill(skill_name)

            if not skill:
                return None

            return {
                'name': skill.name,
                'description': skill.description,
                'steps': []  # 可以扩展返回步骤定义
            }

        except Exception as e:
            logger.error(f"Get skill info error: {e}")
            return None
