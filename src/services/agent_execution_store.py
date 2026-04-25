"""
Agent execution store
用于保存可回放的执行轨迹与事件。
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4


class AgentExecutionStore:
    def __init__(self, max_items: int = 200):
        self.max_items = max_items
        self._items: Dict[str, Dict[str, Any]] = {}
        self._order: List[str] = []
        self._lock = Lock()

    def create(
        self,
        *,
        user_id: str,
        mission_type: str,
        message: str,
        conversation_id: Optional[int] = None,
        execution_plan: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        execution_id = str(uuid4())
        now = datetime.now().isoformat()
        item = {
            "execution_id": execution_id,
            "user_id": user_id,
            "mission_type": mission_type,
            "message": message,
            "conversation_id": conversation_id,
            "status": "running",
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "execution_plan": execution_plan or {},
            "tool_calls": [],
            "events": [],
            "result": None,
            "error": None,
        }
        with self._lock:
            self._items[execution_id] = item
            self._order.append(execution_id)
            self._trim_locked()
        return deepcopy(item)

    def add_event(
        self,
        execution_id: str,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        with self._lock:
            item = self._items.get(execution_id)
            if not item:
                return
            event = {
                "type": event_type,
                "timestamp": datetime.now().isoformat(),
                "payload": payload,
            }
            item["events"].append(event)
            item["updated_at"] = event["timestamp"]

    def set_tool_calls(self, execution_id: str, tool_calls: List[Dict[str, Any]]) -> None:
        with self._lock:
            item = self._items.get(execution_id)
            if not item:
                return
            item["tool_calls"] = deepcopy(tool_calls)
            item["updated_at"] = datetime.now().isoformat()

    def complete(
        self,
        execution_id: str,
        result: Dict[str, Any],
        *,
        status: str = "completed",
        error: Optional[str] = None,
    ) -> None:
        with self._lock:
            item = self._items.get(execution_id)
            if not item:
                return
            now = datetime.now().isoformat()
            item["status"] = status
            item["result"] = deepcopy(result)
            item["error"] = error
            item["updated_at"] = now
            item["completed_at"] = now

    def get(self, execution_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            item = self._items.get(execution_id)
            return deepcopy(item) if item else None

    def list_recent(self, user_id: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            ids = list(reversed(self._order))
            result = []
            for execution_id in ids:
                item = self._items.get(execution_id)
                if not item:
                    continue
                if user_id and item["user_id"] != user_id:
                    continue
                result.append(deepcopy(item))
                if len(result) >= limit:
                    break
            return result

    def _trim_locked(self) -> None:
        while len(self._order) > self.max_items:
            execution_id = self._order.pop(0)
            self._items.pop(execution_id, None)


_execution_store: Optional[AgentExecutionStore] = None


def get_agent_execution_store() -> AgentExecutionStore:
    global _execution_store
    if _execution_store is None:
        _execution_store = AgentExecutionStore()
    return _execution_store
