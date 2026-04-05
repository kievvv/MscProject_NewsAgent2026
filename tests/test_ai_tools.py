"""
AI Tools Unit Tests
测试AI工具包装器
"""
import pytest
from unittest.mock import Mock, patch

from src.ai.tools.news_tools import NewsSearchTool
from src.ai.tools.analysis_tools import KeywordExtractionTool, TrendAnalysisTool
from src.ai.tools.market_tools import MarketDataTool, FearGreedTool


class TestNewsSearchTool:
    """测试新闻搜索工具"""

    def test_tool_initialization(self):
        """测试工具初始化"""
        tool = NewsSearchTool()
        assert tool.name == "news_search"
        assert tool.description is not None

    @patch('src.ai.tools.news_tools.get_search_service')
    def test_execute_success(self, mock_get_service):
        """测试成功执行"""
        # Mock service
        mock_service = Mock()
        mock_news = Mock()
        mock_news.title = "Test News"
        mock_news.text = "Test content"
        mock_news.date = "2026-03-20"
        mock_service.search_by_keyword.return_value = [mock_news]
        mock_get_service.return_value = mock_service

        # Execute
        tool = NewsSearchTool()
        result = tool.execute(keyword="bitcoin", days=7, limit=10)

        # Verify
        assert result.success is True
        assert isinstance(result.data, list)
        assert len(result.data) > 0
        mock_service.search_by_keyword.assert_called_once()

    def test_execute_missing_keyword(self):
        """测试缺少关键词"""
        tool = NewsSearchTool()
        result = tool.execute(keyword="", days=7, limit=10)
        assert result.success is False
        assert "keyword" in result.error.lower()


class TestKeywordExtractionTool:
    """测试关键词提取工具"""

    def test_tool_initialization(self):
        """测试工具初始化"""
        tool = KeywordExtractionTool()
        assert tool.name == "keyword_extraction"
        assert tool.description is not None

    @patch('src.ai.tools.analysis_tools.get_keyword_extractor')
    def test_execute_success(self, mock_get_extractor):
        """测试成功执行"""
        # Mock extractor
        mock_extractor = Mock()
        mock_extractor.extract_keywords.return_value = [
            {"keyword": "bitcoin", "score": 0.9},
            {"keyword": "crypto", "score": 0.8}
        ]
        mock_get_extractor.return_value = mock_extractor

        # Execute
        tool = KeywordExtractionTool()
        result = tool.execute(text="Bitcoin is a cryptocurrency", top_n=10)

        # Verify
        assert result.success is True
        assert isinstance(result.data, list)
        assert len(result.data) == 2
        mock_extractor.extract_keywords.assert_called_once()

    def test_execute_empty_text(self):
        """测试空文本"""
        tool = KeywordExtractionTool()
        result = tool.execute(text="", top_n=10)
        assert result.success is False


class TestTrendAnalysisTool:
    """测试趋势分析工具"""

    @patch('src.ai.tools.analysis_tools.get_trend_service')
    def test_execute_success(self, mock_get_service):
        """测试成功执行"""
        # Mock service
        mock_service = Mock()
        mock_service.analyze_keyword_trend.return_value = {
            'keyword': 'bitcoin',
            'total_count': 100,
            'active_days': 15,
            'avg_daily_count': 6.67,
            'peak_date': '2026-03-15',
            'peak_count': 20
        }
        mock_get_service.return_value = mock_service

        # Execute
        tool = TrendAnalysisTool()
        result = tool.execute(keyword="bitcoin", days=30)

        # Verify
        assert result.success is True
        assert result.data['keyword'] == 'bitcoin'
        assert result.data['total_count'] == 100
        mock_service.analyze_keyword_trend.assert_called_once()


class TestMarketDataTool:
    """测试市场数据工具"""

    @patch('src.ai.tools.market_tools.get_market_service')
    def test_execute_success(self, mock_get_service):
        """测试成功执行"""
        # Mock service
        mock_service = Mock()
        mock_service.fetch_crypto_market_board.return_value = {
            'coins': [
                {
                    'symbol': 'BTC',
                    'current_price': 50000,
                    'price_change_24h': 2.5,
                    'market_cap': 1000000000000
                }
            ],
            'last_updated': '2026-03-20T10:00:00'
        }
        mock_get_service.return_value = mock_service

        # Execute
        tool = MarketDataTool()
        result = tool.execute(limit=10)

        # Verify
        assert result.success is True
        assert 'coins' in result.data
        assert len(result.data['coins']) > 0
        mock_service.fetch_crypto_market_board.assert_called_once()


class TestFearGreedTool:
    """测试恐慌贪婪指数工具"""

    @patch('src.ai.tools.market_tools.get_market_service')
    def test_execute_success(self, mock_get_service):
        """测试成功执行"""
        # Mock service
        mock_service = Mock()
        mock_service.fetch_fear_greed_index.return_value = {
            'value': 45,
            'classification': '恐惧',
            'value_class': 'fear',
            'interpretation': '市场恐慌，可能是买入机会'
        }
        mock_get_service.return_value = mock_service

        # Execute
        tool = FearGreedTool()
        result = tool.execute()

        # Verify
        assert result.success is True
        assert result.data['value'] == 45
        assert 'classification' in result.data
        mock_service.fetch_fear_greed_index.assert_called_once()


# Pytest fixtures
@pytest.fixture
def sample_news_data():
    """示例新闻数据"""
    return [
        {
            'title': 'Bitcoin hits new high',
            'text': 'Bitcoin price reaches $50,000',
            'date': '2026-03-20',
            'keywords': 'bitcoin, price'
        }
    ]


@pytest.fixture
def sample_market_data():
    """示例市场数据"""
    return {
        'coins': [
            {
                'symbol': 'BTC',
                'current_price': 50000,
                'price_change_24h': 2.5,
                'market_cap': 1000000000000
            },
            {
                'symbol': 'ETH',
                'current_price': 3000,
                'price_change_24h': -1.2,
                'market_cap': 300000000000
            }
        ],
        'last_updated': '2026-03-20T10:00:00'
    }
