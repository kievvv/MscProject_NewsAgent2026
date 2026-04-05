"""
Base Tool Class
Abstract base for all agent tools
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class ToolResult:
    """标准工具执行结果"""
    success: bool
    data: Any
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'metadata': self.metadata or {},
        }


class BaseTool(ABC):
    """基础工具类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        执行工具

        Args:
            **kwargs: 工具特定参数

        Returns:
            ToolResult对象
        """
        pass

    def __call__(self, **kwargs) -> ToolResult:
        """允许直接调用工具实例"""
        return self.execute(**kwargs)

    def to_langchain_tool(self):
        """转换为LangChain工具格式（可选）"""
        from langchain_core.tools import StructuredTool
        return StructuredTool.from_function(
            func=self.execute,
            name=self.name,
            description=self.description,
        )
