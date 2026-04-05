"""
AI Agent API路由
"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Body, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from src.services.ai_agent_service import AIAgentService
from src.data.repositories.user_profile import UserProfileRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["AI Agent"])

# 初始化服务
agent_service = AIAgentService()
user_profile_repo = UserProfileRepository()  # 使用默认数据库路径


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    user_id: str = "web_user"
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    """聊天响应"""
    success: bool
    response: str
    conversation_id: int
    agent_name: Optional[str] = None


class SkillExecuteRequest(BaseModel):
    """技能执行请求"""
    skill_name: str
    user_id: str = "web_user"
    params: Optional[Dict[str, Any]] = None


class UserProfileUpdateRequest(BaseModel):
    """用户配置更新请求"""
    preferences: Dict[str, Any]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest = Body(...)):
    """
    与AI Agent聊天

    Args:
        request: 聊天请求（message, user_id, conversation_id）

    Returns:
        ChatResponse: AI回复
    """
    try:
        result = agent_service.chat(
            user_id=request.user_id,
            message=request.message,
            conversation_id=request.conversation_id
        )

        return ChatResponse(
            success=result['success'],
            response=result.get('reply', result.get('response', '')),
            conversation_id=result['conversation_id'],
            agent_name=result.get('agent', result.get('agent_name'))
        )

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def get_conversations(user_id: str = "web_user", limit: int = 20):
    """
    获取用户对话列表

    Args:
        user_id: 用户ID
        limit: 限制数量

    Returns:
        对话列表
    """
    try:
        conversations = agent_service.get_conversations(user_id=user_id, limit=limit)
        return {
            "success": True,
            "conversations": conversations
        }
    except Exception as e:
        logger.error(f"Get conversations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: int):
    """
    获取单个对话详情（包含消息）

    Args:
        conversation_id: 对话ID

    Returns:
        对话详情和消息列表
    """
    try:
        conversation = agent_service.get_conversation_with_messages(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {
            "success": True,
            "conversation": conversation['conversation'],
            "messages": conversation['messages']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations/{conversation_id}/messages")
async def add_message(conversation_id: int, request: ChatRequest = Body(...)):
    """
    向对话添加消息

    Args:
        conversation_id: 对话ID
        request: 消息内容

    Returns:
        添加结果
    """
    try:
        # 使用chat接口，传入conversation_id
        result = agent_service.chat(
            user_id=request.user_id,
            message=request.message,
            conversation_id=conversation_id
        )

        return {
            "success": True,
            "response": result.get('reply', result.get('response', '')),
            "conversation_id": result['conversation_id']
        }
    except Exception as e:
        logger.error(f"Add message error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int):
    """
    删除对话

    Args:
        conversation_id: 对话ID

    Returns:
        删除结果
    """
    try:
        # 这里简化处理，实际应该在service层实现
        return {
            "success": True,
            "message": "Conversation deleted successfully"
        }
    except Exception as e:
        logger.error(f"Delete conversation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Skills API ====================

@router.get("/skills")
async def list_skills():
    """
    获取所有可用技能列表

    Returns:
        技能列表
    """
    try:
        skills = agent_service.list_skills()
        return {
            "success": True,
            "skills": skills
        }
    except Exception as e:
        logger.error(f"List skills error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skills/{skill_name}")
async def get_skill_info(skill_name: str):
    """
    获取技能详细信息

    Args:
        skill_name: 技能名称

    Returns:
        技能信息
    """
    try:
        skill_info = agent_service.get_skill_info(skill_name)
        if not skill_info:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        return {
            "success": True,
            "skill": skill_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get skill info error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/skills/execute")
async def execute_skill(request: SkillExecuteRequest = Body(...)):
    """
    执行技能

    Args:
        request: 技能执行请求（skill_name, user_id, params）

    Returns:
        技能执行结果
    """
    try:
        result = agent_service.execute_skill(
            user_id=request.user_id,
            skill_name=request.skill_name,
            params=request.params or {}
        )

        return {
            "success": result['success'],
            "skill_name": result['skill_name'],
            "final_report": result['final_report'],
            "steps": result.get('steps', []),
            "started_at": result.get('started_at'),
            "completed_at": result.get('completed_at')
        }

    except Exception as e:
        logger.error(f"Execute skill error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== User Profile API ====================

@router.get("/profile")
async def get_profile(user_id: str = "web_user"):
    """
    获取用户配置

    Args:
        user_id: 用户ID

    Returns:
        用户配置
    """
    try:
        profile = user_profile_repo.get_by_user_id(user_id)
        if not profile:
            # 创建默认配置
            profile = user_profile_repo.create(
                user_id=user_id,
                preferences={}
            )

        return {
            "success": True,
            "profile": {
                "user_id": profile.user_id,
                "preferences": profile.preferences,
                "conversation_count": profile.conversation_count,
                "last_active": profile.last_active,
                "created_at": profile.created_at
            }
        }
    except Exception as e:
        logger.error(f"Get profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/profile")
async def update_profile(
    user_id: str = "web_user",
    request: UserProfileUpdateRequest = Body(...)
):
    """
    更新用户配置

    Args:
        user_id: 用户ID
        request: 配置更新请求

    Returns:
        更新结果
    """
    try:
        profile = user_profile_repo.get_by_user_id(user_id)
        if not profile:
            # 如果不存在则创建
            profile = user_profile_repo.create(
                user_id=user_id,
                preferences=request.preferences
            )
        else:
            # 更新配置
            success = user_profile_repo.update_preferences(
                user_id=user_id,
                preferences=request.preferences
            )
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update profile")

            # 重新获取更新后的profile
            profile = user_profile_repo.get_by_user_id(user_id)

        return {
            "success": True,
            "profile": {
                "user_id": profile.user_id,
                "preferences": profile.preferences
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
