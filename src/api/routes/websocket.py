"""
WebSocket路由
实时流式响应
"""
import json
import logging
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.services.ai_agent_service import AIAgentService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])

# 初始化服务
agent_service = AIAgentService()

# 连接管理器
class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """建立连接"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected via WebSocket")

    def disconnect(self, user_id: str):
        """断开连接"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected")

    async def send_message(self, user_id: str, message: dict):
        """发送消息"""
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_json(message)

    async def send_text(self, user_id: str, text: str):
        """发送文本"""
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_text(text)


manager = ConnectionManager()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket聊天端点

    消息格式:
    {
        "action": "chat" | "skill",
        "user_id": "user_id",
        "message": "message text",
        "conversation_id": 123,
        "skill_name": "DailyBriefing",
        "params": {}
    }

    响应格式:
    {
        "type": "chunk" | "complete" | "error",
        "content": "text chunk or full response",
        "conversation_id": 123,
        "agent_name": "NewsAgent"
    }
    """
    user_id = None

    try:
        # 接受连接
        await websocket.accept()
        logger.info("WebSocket connection established")

        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected successfully"
        })

        while True:
            # 接收消息
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)
                action = message_data.get("action", "chat")
                user_id = message_data.get("user_id", "ws_user")

                # 注册连接
                if user_id not in manager.active_connections:
                    manager.active_connections[user_id] = websocket

                if action == "chat":
                    # 处理聊天消息
                    await handle_chat_message(websocket, message_data)

                elif action == "skill":
                    # 执行技能
                    await handle_skill_execution(websocket, message_data)

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })

            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}", exc_info=True)
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {user_id}")
        if user_id:
            manager.disconnect(user_id)

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        if user_id:
            manager.disconnect(user_id)


async def handle_chat_message(websocket: WebSocket, data: dict):
    """处理聊天消息"""
    user_id = data.get("user_id", "ws_user")
    message = data.get("message", "")
    conversation_id = data.get("conversation_id")

    if not message:
        await websocket.send_json({
            "type": "error",
            "message": "Message is required"
        })
        return

    try:
        # 发送处理中状态
        await websocket.send_json({
            "type": "processing",
            "message": "正在思考..."
        })

        # 调用AI服务
        result = agent_service.chat(
            user_id=user_id,
            message=message,
            conversation_id=conversation_id
        )

        # 模拟流式响应（将完整响应分块发送）
        response_text = result.get('reply', result.get('response', ''))

        # 每20个字符发送一个chunk
        chunk_size = 20
        for i in range(0, len(response_text), chunk_size):
            chunk = response_text[i:i + chunk_size]
            await websocket.send_json({
                "type": "chunk",
                "content": chunk,
                "conversation_id": result.get('conversation_id')
            })

        # 发送完成消息
        await websocket.send_json({
            "type": "complete",
            "content": response_text,
            "conversation_id": result.get('conversation_id'),
            "agent_name": result.get('agent', result.get('agent_name'))
        })

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })


async def handle_skill_execution(websocket: WebSocket, data: dict):
    """处理技能执行"""
    user_id = data.get("user_id", "ws_user")
    skill_name = data.get("skill_name")
    params = data.get("params", {})

    if not skill_name:
        await websocket.send_json({
            "type": "error",
            "message": "skill_name is required"
        })
        return

    try:
        # 发送开始执行状态
        await websocket.send_json({
            "type": "skill_start",
            "skill_name": skill_name,
            "message": f"正在执行 {skill_name}..."
        })

        # 执行技能
        result = agent_service.execute_skill(
            user_id=user_id,
            skill_name=skill_name,
            params=params
        )

        # 发送步骤进度
        if result.get('steps'):
            for i, step in enumerate(result['steps'], 1):
                await websocket.send_json({
                    "type": "skill_progress",
                    "skill_name": skill_name,
                    "step": i,
                    "total_steps": len(result['steps']),
                    "step_name": step.get('name', ''),
                    "step_description": step.get('description', ''),
                    "completed": step.get('completed', False)
                })

        # 发送完整报告
        await websocket.send_json({
            "type": "skill_complete",
            "skill_name": skill_name,
            "final_report": result.get('final_report', ''),
            "success": result.get('success', False),
            "started_at": result.get('started_at'),
            "completed_at": result.get('completed_at')
        })

    except Exception as e:
        logger.error(f"Skill execution error: {e}", exc_info=True)
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
