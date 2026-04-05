"""
AI Agents Unit Tests
测试AI Agent逻辑
"""
import pytest
from unittest.mock import Mock, patch

from src.ai.agents.state import create_initial_state
from src.ai.agents.coordinator import CoordinatorAgent
from src.ai.agents.news_agent import NewsAgent
from src.ai.agents.analysis_agent import AnalysisAgent
from src.ai.agents.trade_agent import TradeAgent


class TestAgentState:
    """测试Agent状态"""

    def test_create_initial_state(self):
        """测试创建初始状态"""
        state = create_initial_state(
            user_id="test_user",
            user_message="Hello",
            conversation_id=123,
            user_profile={"theme": "dark"}
        )

        assert state["user_id"] == "test_user"
        assert len(state["messages"]) == 1
        assert state["messages"][0]["role"] == "user"
        assert state["messages"][0]["content"] == "Hello"
        assert state["conversation_id"] == 123
        assert state["user_profile"] == {"theme": "dark"}
        assert state["current_agent"] is None
        assert state["next_action"] is None


class TestCoordinatorAgent:
    """测试协调器Agent"""

    @patch('src.ai.agents.coordinator.get_llm_provider')
    def test_route_to_news_agent(self, mock_get_llm):
        """测试路由到新闻Agent"""
        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "news"
        mock_get_llm.return_value = mock_llm

        # Create state
        state = create_initial_state(
            user_id="test_user",
            user_message="最新比特币新闻",
            conversation_id=None,
            user_profile={}
        )

        # Execute
        agent = CoordinatorAgent()
        result = agent.process(state)

        # Verify
        assert result["next_action"] in ["news", "news_agent"]
        assert result["current_agent"] == "coordinator"

    @patch('src.ai.agents.coordinator.get_llm_provider')
    def test_route_to_analysis_agent(self, mock_get_llm):
        """测试路由到分析Agent"""
        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "analysis"
        mock_get_llm.return_value = mock_llm

        # Create state
        state = create_initial_state(
            user_id="test_user",
            user_message="分析比特币趋势",
            conversation_id=None,
            user_profile={}
        )

        # Execute
        agent = CoordinatorAgent()
        result = agent.process(state)

        # Verify
        assert result["next_action"] in ["analysis", "analysis_agent"]


class TestNewsAgent:
    """测试新闻Agent"""

    @patch('src.ai.agents.news_agent.NewsSearchTool')
    @patch('src.ai.agents.news_agent.get_llm_provider')
    def test_search_news(self, mock_get_llm, mock_news_tool):
        """测试搜索新闻"""
        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "bitcoin"
        mock_get_llm.return_value = mock_llm

        # Mock tool
        mock_tool_instance = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = [
            {'title': 'Bitcoin news', 'text': 'Content', 'date': '2026-03-20'}
        ]
        mock_tool_instance.execute.return_value = mock_result
        mock_news_tool.return_value = mock_tool_instance

        # Create state
        state = create_initial_state(
            user_id="test_user",
            user_message="比特币新闻",
            conversation_id=None,
            user_profile={}
        )

        # Execute
        agent = NewsAgent()
        result = agent.process(state)

        # Verify
        assert "final_response" in result
        assert len(result.get("tool_results", [])) > 0


class TestAnalysisAgent:
    """测试分析Agent"""

    @patch('src.ai.agents.analysis_agent.TrendAnalysisTool')
    @patch('src.ai.agents.analysis_agent.get_llm_provider')
    def test_trend_analysis(self, mock_get_llm, mock_trend_tool):
        """测试趋势分析"""
        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "正在分析趋势..."
        mock_get_llm.return_value = mock_llm

        # Mock tool
        mock_tool_instance = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = {
            'keyword': 'bitcoin',
            'total_count': 100,
            'active_days': 15,
            'avg_daily_count': 6.67
        }
        mock_tool_instance.execute.return_value = mock_result
        mock_trend_tool.return_value = mock_tool_instance

        # Create state
        state = create_initial_state(
            user_id="test_user",
            user_message="分析比特币趋势",
            conversation_id=None,
            user_profile={}
        )

        # Execute
        agent = AnalysisAgent()
        result = agent.process(state)

        # Verify
        assert "final_response" in result


class TestTradeAgent:
    """测试交易Agent"""

    @patch('src.ai.agents.trade_agent.MarketDataTool')
    @patch('src.ai.agents.trade_agent.get_llm_provider')
    def test_market_data(self, mock_get_llm, mock_market_tool):
        """测试市场数据"""
        # Mock LLM
        mock_llm = Mock()
        mock_llm.generate.return_value = "正在获取市场数据..."
        mock_get_llm.return_value = mock_llm

        # Mock tool
        mock_tool_instance = Mock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.data = {
            'coins': [
                {
                    'symbol': 'BTC',
                    'current_price': 50000,
                    'price_change_24h': 2.5
                }
            ]
        }
        mock_tool_instance.execute.return_value = mock_result
        mock_market_tool.return_value = mock_tool_instance

        # Create state
        state = create_initial_state(
            user_id="test_user",
            user_message="市场数据",
            conversation_id=None,
            user_profile={}
        )

        # Execute
        agent = TradeAgent()
        result = agent.process(state)

        # Verify
        assert "final_response" in result


# Test fixtures
@pytest.fixture
def sample_state():
    """示例状态"""
    return create_initial_state(
        user_id="test_user",
        user_message="Hello",
        conversation_id=123,
        user_profile={"theme": "dark"}
    )


@pytest.fixture
def mock_llm_provider():
    """Mock LLM Provider"""
    with patch('src.ai.llm.factory.get_llm_provider') as mock:
        mock_provider = Mock()
        mock_provider.generate.return_value = "Test response"
        mock.return_value = mock_provider
        yield mock
