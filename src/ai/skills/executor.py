"""
Skill Executor
技能执行器，管理和执行技能
"""
import logging
from typing import Dict, Any, Optional

from .base import BaseSkill, SkillResult
from .daily_briefing import DailyBriefingSkill
from .deep_dive import DeepDiveSkill
from .alpha_hunter import AlphaHunterSkill

logger = logging.getLogger(__name__)


class SkillExecutor:
    """技能执行器"""

    def __init__(self):
        self.skills: Dict[str, BaseSkill] = {}
        self._register_skills()

    def _register_skills(self):
        """注册所有可用技能"""
        self.skills['DailyBriefing'] = DailyBriefingSkill()
        self.skills['DeepDive'] = DeepDiveSkill()
        self.skills['AlphaHunter'] = AlphaHunterSkill()

        logger.info(f"Registered {len(self.skills)} skills")

    def list_skills(self) -> Dict[str, str]:
        """列出所有可用技能"""
        return {
            name: skill.description
            for name, skill in self.skills.items()
        }

    def execute_skill(
        self,
        skill_name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> SkillResult:
        """
        执行指定技能

        Args:
            skill_name: 技能名称
            params: 技能参数

        Returns:
            SkillResult

        Raises:
            ValueError: 如果技能不存在
        """
        if skill_name not in self.skills:
            available = ', '.join(self.skills.keys())
            raise ValueError(
                f"Skill '{skill_name}' not found. Available: {available}"
            )

        skill = self.skills[skill_name]
        logger.info(f"Executing skill: {skill_name}")

        return skill.execute(params or {})

    def get_skill(self, skill_name: str) -> Optional[BaseSkill]:
        """获取技能对象"""
        return self.skills.get(skill_name)


# 全局技能执行器实例
_executor = None


def get_skill_executor() -> SkillExecutor:
    """获取全局技能执行器实例"""
    global _executor
    if _executor is None:
        _executor = SkillExecutor()
    return _executor
