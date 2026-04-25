"""
Skill Base Classes
技能基类和执行步骤定义
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SkillStep:
    """技能执行步骤"""
    name: str
    description: str
    tool_name: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    completed: bool = False


@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool
    skill_name: str
    steps: List[SkillStep]
    final_report: str
    structured_output: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'skill_name': self.skill_name,
            'steps': [
                {
                    'name': step.name,
                    'description': step.description,
                    'tool_name': step.tool_name,
                    'params': step.params,
                    'completed': step.completed,
                    'error': step.error
                }
                for step in self.steps
            ],
            'final_report': self.final_report,
            'structured_output': self.structured_output,
            'metadata': self.metadata,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
        }


class BaseSkill(ABC):
    """技能基类"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.steps: List[SkillStep] = []

    @abstractmethod
    def define_steps(self, params: Dict[str, Any]) -> List[SkillStep]:
        """
        定义技能执行步骤

        Args:
            params: 技能参数

        Returns:
            步骤列表
        """
        pass

    @abstractmethod
    def generate_report(self, steps: List[SkillStep]) -> str:
        """
        生成最终报告

        Args:
            steps: 已执行的步骤列表

        Returns:
            报告文本
        """
        pass

    def build_structured_output(self, steps: List[SkillStep], report: str) -> Dict[str, Any]:
        """生成结构化输出，子类可覆盖。"""
        return {
            "title": self.name,
            "summary": report[:200],
            "key_points": [],
            "evidence_news_ids": [],
            "risk_notes": [],
            "next_actions": [],
        }

    def execute(self, params: Dict[str, Any] = None) -> SkillResult:
        """
        执行技能

        Args:
            params: 技能参数

        Returns:
            SkillResult
        """
        params = params or {}
        started_at = datetime.now().isoformat()

        logger.info(f"Executing skill: {self.name}")

        try:
            # 定义步骤
            self.steps = self.define_steps(params)

            # 执行每个步骤
            for step in self.steps:
                try:
                    logger.info(f"Executing step: {step.name}")
                    self._execute_step(step)
                    step.completed = True
                except Exception as e:
                    logger.error(f"Step {step.name} failed: {e}")
                    step.error = str(e)
                    step.completed = False

            # 生成报告
            report = self.generate_report(self.steps)

            completed_at = datetime.now().isoformat()

            return SkillResult(
                success=True,
                skill_name=self.name,
                steps=self.steps,
                final_report=report,
                structured_output=self.build_structured_output(self.steps, report),
                metadata=params,
                started_at=started_at,
                completed_at=completed_at
            )

        except Exception as e:
            logger.error(f"Skill execution failed: {e}")
            return SkillResult(
                success=False,
                skill_name=self.name,
                steps=self.steps,
                final_report=f"技能执行失败: {str(e)}",
                structured_output={},
                metadata=params,
                started_at=started_at,
                completed_at=datetime.now().isoformat()
            )

    def _execute_step(self, step: SkillStep):
        """
        执行单个步骤（子类可覆盖）

        Args:
            step: 步骤对象
        """
        # 默认实现：如果有tool_name，则调用对应的工具
        # 子类应该覆盖这个方法来实现具体逻辑
        pass
