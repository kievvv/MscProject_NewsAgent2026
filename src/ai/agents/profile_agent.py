"""
User Profile Agent
用户画像Agent - 管理用户偏好、推荐个性化内容
"""
import logging
from typing import Dict, Any, List

from .base import BaseAgent
from .state import AgentState
from src.ai.llm.base import LLMMessage
from src.data.repositories.user_profile import UserProfileRepository

logger = logging.getLogger(__name__)


class UserProfileAgent(BaseAgent):
    """用户画像Agent"""

    def __init__(self, llm):
        super().__init__("UserProfileAgent", llm)
        self.profile_repo = UserProfileRepository()

    def process(self, state: AgentState) -> AgentState:
        """
        处理用户画像相关请求

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("UserProfileAgent processing request...")

        user_id = state.get("user_id", "")
        user_message = ""

        for msg in reversed(state["messages"]):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        # 判断操作类型
        operation = self._detect_operation(user_message)

        logger.info(f"Profile operation: {operation}")

        if operation == "set_preference":
            response = self._handle_set_preference(user_id, user_message, state)
        elif operation == "get_profile":
            response = self._handle_get_profile(user_id, state)
        elif operation == "recommend":
            response = self._handle_recommendation(user_id, state)
        else:
            response = self._handle_general_profile(user_id, state)

        state = self._add_message(state, "assistant", response)
        state["current_agent"] = "profile_agent"
        state["final_response"] = response
        state["next_action"] = "end"

        return state

    def _detect_operation(self, text: str) -> str:
        """检测操作类型"""
        text_lower = text.lower()

        if any(keyword in text_lower for keyword in ["设置", "偏好", "喜欢", "关注", "preference"]):
            return "set_preference"
        elif any(keyword in text_lower for keyword in ["推荐", "建议", "recommend"]):
            return "recommend"
        elif any(keyword in text_lower for keyword in ["我的", "个人", "profile"]):
            return "get_profile"
        else:
            return "general"

    def _handle_set_preference(self, user_id: str, message: str, state: AgentState) -> str:
        """处理设置偏好"""
        try:
            # 获取或创建用户画像
            profile = self.profile_repo.get_or_create(user_id)

            # 提取偏好（简化：使用LLM提取关键词）
            preferences = self._extract_preferences(message)

            # 更新偏好
            current_prefs = profile.preferences or {}
            current_prefs.update(preferences)

            self.profile_repo.update_preferences(user_id, current_prefs)

            response = "✅ 已记录您的偏好！\n\n"
            response += "您关注的内容：\n"
            for key, value in preferences.items():
                response += f"  • {key}: {value}\n"

            response += "\n我会根据这些偏好为您推荐相关内容。"

            state["context"]["preferences_updated"] = True

            return response

        except Exception as e:
            logger.error(f"Set preference error: {e}")
            return "抱歉，保存偏好时出错了。"

    def _handle_get_profile(self, user_id: str, state: AgentState) -> str:
        """处理获取画像"""
        try:
            profile = self.profile_repo.get_or_create(user_id)

            response = f"👤 **您的个人画像**\n\n"
            response += f"📊 统计数据：\n"
            response += f"  • 对话次数: {profile.conversation_count}\n"
            response += f"  • 最后活跃: {profile.last_active}\n"
            response += f"  • 注册时间: {profile.created_at}\n\n"

            if profile.preferences:
                response += f"⚙️ 偏好设置：\n"
                for key, value in profile.preferences.items():
                    response += f"  • {key}: {value}\n"
            else:
                response += "⚙️ 您还没有设置偏好。\n"
                response += "可以告诉我您关注的币种、关键词等，我会为您推荐相关内容。\n"

            return response

        except Exception as e:
            logger.error(f"Get profile error: {e}")
            return "抱歉，获取画像时出错了。"

    def _handle_recommendation(self, user_id: str, state: AgentState) -> str:
        """处理推荐请求"""
        try:
            profile = self.profile_repo.get_or_create(user_id)

            if not profile.preferences:
                return "您还没有设置偏好，无法为您推荐内容。请先告诉我您关注什么。"

            # 基于偏好生成推荐
            response = "💡 **个性化推荐**\n\n"
            response += "根据您的偏好，我建议您关注：\n\n"

            # 从偏好中提取关键词
            interests = []
            for key, value in profile.preferences.items():
                if isinstance(value, str):
                    interests.append(value)
                elif isinstance(value, list):
                    interests.extend(value)

            if interests:
                for i, interest in enumerate(interests[:5], 1):
                    response += f"{i}. 关于 '{interest}' 的最新动态\n"

                response += "\n提示：您可以直接问我 \"比特币最新新闻\" 或 \"以太坊趋势分析\"。"
            else:
                response += "暂时无法生成推荐，请完善您的偏好设置。"

            return response

        except Exception as e:
            logger.error(f"Recommendation error: {e}")
            return "抱歉，生成推荐时出错了。"

    def _handle_general_profile(self, user_id: str, state: AgentState) -> str:
        """处理一般画像查询"""
        profile = self.profile_repo.get_or_create(user_id)

        response = f"您好！我可以帮您：\n\n"
        response += f"1. 设置偏好 - 告诉我您关注什么\n"
        response += f"2. 查看画像 - \"我的个人资料\"\n"
        response += f"3. 个性化推荐 - \"推荐一些内容\"\n\n"
        response += f"您目前有 {profile.conversation_count} 次对话记录。"

        return response

    def _extract_preferences(self, message: str) -> Dict[str, Any]:
        """从消息中提取偏好（简化版）"""
        preferences = {}

        # 简单的关键词提取
        keywords = ["比特币", "以太坊", "DeFi", "NFT", "Web3", "AI", "区块链"]

        mentioned = []
        message_lower = message.lower()

        for keyword in keywords:
            if keyword.lower() in message_lower:
                mentioned.append(keyword)

        if mentioned:
            preferences["interests"] = mentioned

        # 提取时间偏好
        if "每天" in message or "daily" in message_lower:
            preferences["update_frequency"] = "daily"
        elif "每周" in message or "weekly" in message_lower:
            preferences["update_frequency"] = "weekly"

        return preferences

    def _get_system_prompt(self) -> str:
        return "你是用户画像管理专家，帮助用户管理偏好和获取个性化推荐。"
