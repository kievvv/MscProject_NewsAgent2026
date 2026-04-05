"""
AI Skills Unit Tests
测试技能系统
"""
import pytest
from unittest.mock import Mock, patch

from src.ai.skills.base import BaseSkill, SkillStep, SkillResult
from src.ai.skills.executor import SkillExecutor, get_skill_executor
from src.ai.skills.daily_briefing import DailyBriefingSkill
from src.ai.skills.deep_dive import DeepDiveSkill
from src.ai.skills.alpha_hunter import AlphaHunterSkill


class TestSkillBase:
    """测试技能基类"""

    def test_skill_step_creation(self):
        """测试步骤创建"""
        step = SkillStep(
            name="test_step",
            description="Test step",
            tool_name="test_tool",
            params={"key": "value"}
        )

        assert step.name == "test_step"
        assert step.description == "Test step"
        assert step.tool_name == "test_tool"
        assert step.params == {"key": "value"}
        assert step.result is None
        assert step.error is None
        assert step.completed is False

    def test_skill_result_to_dict(self):
        """测试结果转字典"""
        steps = [
            SkillStep(name="step1", description="Step 1", completed=True),
            SkillStep(name="step2", description="Step 2", completed=False)
        ]

        result = SkillResult(
            success=True,
            skill_name="TestSkill",
            steps=steps,
            final_report="Test report",
            metadata={"key": "value"}
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["skill_name"] == "TestSkill"
        assert len(result_dict["steps"]) == 2
        assert result_dict["final_report"] == "Test report"
        assert result_dict["metadata"] == {"key": "value"}


class TestSkillExecutor:
    """测试技能执行器"""

    def test_executor_initialization(self):
        """测试执行器初始化"""
        executor = SkillExecutor()
        assert len(executor.skills) == 3
        assert "DailyBriefing" in executor.skills
        assert "DeepDive" in executor.skills
        assert "AlphaHunter" in executor.skills

    def test_list_skills(self):
        """测试列出技能"""
        executor = SkillExecutor()
        skills = executor.list_skills()

        assert isinstance(skills, dict)
        assert len(skills) == 3
        assert "DailyBriefing" in skills
        assert isinstance(skills["DailyBriefing"], str)

    def test_get_skill(self):
        """测试获取技能"""
        executor = SkillExecutor()
        skill = executor.get_skill("DailyBriefing")

        assert skill is not None
        assert isinstance(skill, DailyBriefingSkill)
        assert skill.name == "DailyBriefing"

    def test_get_nonexistent_skill(self):
        """测试获取不存在的技能"""
        executor = SkillExecutor()
        skill = executor.get_skill("NonExistent")
        assert skill is None

    def test_execute_skill_not_found(self):
        """测试执行不存在的技能"""
        executor = SkillExecutor()

        with pytest.raises(ValueError) as exc_info:
            executor.execute_skill("NonExistent")

        assert "not found" in str(exc_info.value).lower()

    def test_get_skill_executor_singleton(self):
        """测试全局执行器单例"""
        executor1 = get_skill_executor()
        executor2 = get_skill_executor()
        assert executor1 is executor2


class TestDailyBriefingSkill:
    """测试每日简报技能"""

    def test_skill_initialization(self):
        """测试技能初始化"""
        skill = DailyBriefingSkill()
        assert skill.name == "DailyBriefing"
        assert skill.description is not None
        assert "简报" in skill.description

    def test_define_steps(self):
        """测试定义步骤"""
        skill = DailyBriefingSkill()
        steps = skill.define_steps({})

        assert len(steps) == 4
        assert steps[0].name == "fetch_market_sentiment"
        assert steps[1].name == "fetch_market_data"
        assert steps[2].name == "fetch_latest_news"
        assert steps[3].name == "analyze_trends"

    @patch.object(DailyBriefingSkill, '_execute_step')
    def test_execute_skill(self, mock_execute):
        """测试执行技能"""
        # Mock step execution
        def mock_step_execution(step):
            step.completed = True
            step.result = {"mock": "data"}

        mock_execute.side_effect = mock_step_execution

        # Execute
        skill = DailyBriefingSkill()
        result = skill.execute({})

        # Verify
        assert result.success is True
        assert result.skill_name == "DailyBriefing"
        assert len(result.steps) == 4
        assert all(step.completed for step in result.steps)
        assert result.final_report is not None
        assert "简报" in result.final_report


class TestDeepDiveSkill:
    """测试深度分析技能"""

    def test_skill_initialization(self):
        """测试技能初始化"""
        skill = DeepDiveSkill()
        assert skill.name == "DeepDive"
        assert "深度" in skill.description

    def test_define_steps_with_topic(self):
        """测试定义步骤（带话题）"""
        skill = DeepDiveSkill()
        steps = skill.define_steps({"topic": "ethereum"})

        assert len(steps) == 4
        assert steps[0].params["keyword"] == "ethereum"

    def test_define_steps_default_topic(self):
        """测试定义步骤（默认话题）"""
        skill = DeepDiveSkill()
        steps = skill.define_steps({})

        assert len(steps) == 4
        assert steps[0].params["keyword"] == "bitcoin"


class TestAlphaHunterSkill:
    """测试Alpha挖掘技能"""

    def test_skill_initialization(self):
        """测试技能初始化"""
        skill = AlphaHunterSkill()
        assert skill.name == "AlphaHunter"
        assert "Alpha" in skill.description

    def test_define_steps(self):
        """测试定义步骤"""
        skill = AlphaHunterSkill()
        steps = skill.define_steps({})

        assert len(steps) == 4
        assert steps[0].name == "scan_emerging_keywords"
        assert steps[1].name == "analyze_market_data"
        assert steps[2].name == "correlate_news_market"
        assert steps[3].name == "identify_opportunities"

    @patch.object(AlphaHunterSkill, '_execute_step')
    def test_execute_generates_report(self, mock_execute):
        """测试生成报告"""
        # Mock step execution
        def mock_step_execution(step):
            step.completed = True
            if step.name == "scan_emerging_keywords":
                step.result = [{"keyword": "defi", "count": 10}]
            elif step.name == "analyze_market_data":
                step.result = [{"symbol": "UNI", "price": 10}]
            elif step.name == "correlate_news_market":
                step.result = [{"symbol": "UNI", "news_count": 5}]
            elif step.name == "identify_opportunities":
                step.result = [{"symbol": "UNI", "reason": "High news ratio"}]

        mock_execute.side_effect = mock_step_execution

        # Execute
        skill = AlphaHunterSkill()
        result = skill.execute({})

        # Verify
        assert result.success is True
        assert result.final_report is not None
        assert "Alpha" in result.final_report


# Test fixtures
@pytest.fixture
def sample_skill_params():
    """示例技能参数"""
    return {
        "topic": "bitcoin",
        "days": 7,
        "limit": 10
    }


@pytest.fixture
def sample_skill_steps():
    """示例技能步骤"""
    return [
        SkillStep(
            name="step1",
            description="First step",
            tool_name="tool1",
            completed=True,
            result={"data": "result1"}
        ),
        SkillStep(
            name="step2",
            description="Second step",
            tool_name="tool2",
            completed=True,
            result={"data": "result2"}
        )
    ]
