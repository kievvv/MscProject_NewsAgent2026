"""
Market Tools
工具包装：市场数据、恐慌贪婪指数
"""
import logging
from typing import List, Optional, Dict, Any

from .base import BaseTool, ToolResult
from src.services import get_market_service
from src.core.models import NewsSource

logger = logging.getLogger(__name__)


class MarketDataTool(BaseTool):
    """市场数据工具"""

    def __init__(self, source: NewsSource = NewsSource.CRYPTO):
        super().__init__(
            name="market_data",
            description="获取市场数据（价格、成交量等）。参数: limit(返回前N个币种,默认10)"
        )
        self.market_service = get_market_service(source=source)

    def execute(self, limit: int = 10, **kwargs) -> ToolResult:
        """
        获取市场数据

        Args:
            limit: 返回前N个币种

        Returns:
            ToolResult包含市场数据
        """
        try:
            # 获取市场数据
            market_result = self.market_service.fetch_crypto_market_board(limit=limit)

            if not market_result or not market_result.get('coins'):
                return ToolResult(
                    success=False,
                    data=[],
                    error="Failed to fetch market data"
                )

            # 格式化结果
            formatted_data = []
            for coin in market_result.get('coins', []):
                formatted_data.append({
                    'symbol': coin.get('symbol', '').upper(),
                    'name': coin.get('name', ''),
                    'current_price': coin.get('current_price', 0),
                    'price_change_24h': round(coin.get('price_change_percentage_24h', 0), 2),
                    'market_cap': coin.get('market_cap', 0),
                    'total_volume': coin.get('total_volume', 0),
                })

            return ToolResult(
                success=True,
                data={
                    'coins': formatted_data,
                    'last_updated': market_result.get('last_updated'),
                },
                metadata={'total': len(formatted_data)}
            )

        except Exception as e:
            logger.error(f"MarketDataTool error: {e}")
            return ToolResult(
                success=False,
                data=[],
                error=str(e)
            )


class FearGreedTool(BaseTool):
    """恐慌贪婪指数工具"""

    def __init__(self):
        super().__init__(
            name="fear_greed_index",
            description="获取加密货币恐慌贪婪指数（0-100，越高表示越贪婪）"
        )
        self.market_service = get_market_service(source=NewsSource.CRYPTO)

    def execute(self, **kwargs) -> ToolResult:
        """
        获取恐慌贪婪指数

        Returns:
            ToolResult包含指数数据
        """
        try:
            # 获取恐慌贪婪指数
            fng_data = self.market_service.fetch_fear_greed_index()

            if not fng_data or fng_data.get('value') is None:
                return ToolResult(
                    success=False,
                    data={},
                    error="Failed to fetch Fear & Greed Index"
                )

            # 格式化结果
            value = int(fng_data.get('value', 50))  # 确保是整数
            result = {
                'value': value,
                'classification': fng_data.get('classification', 'Unknown'),
                'value_classification': fng_data.get('classification', 'Unknown'),
                'timestamp': fng_data.get('timestamp', ''),
                'interpretation': self._interpret_fng(value)
            }

            return ToolResult(
                success=True,
                data=result,
                metadata={'source': 'alternative.me'}
            )

        except Exception as e:
            logger.error(f"FearGreedTool error: {e}")
            return ToolResult(
                success=False,
                data={},
                error=str(e)
            )

    def _interpret_fng(self, value: int) -> str:
        """解释恐慌贪婪指数"""
        if value >= 75:
            return "市场极度贪婪，可能存在泡沫风险"
        elif value >= 55:
            return "市场贪婪，投资者情绪乐观"
        elif value >= 45:
            return "市场中性，情绪平衡"
        elif value >= 25:
            return "市场恐慌，投资者担忧"
        else:
            return "市场极度恐慌，可能是买入机会"
