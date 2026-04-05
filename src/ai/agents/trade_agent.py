"""
Trade Agent
市场交易专家Agent - 处理市场数据、价格查询、情绪分析等
"""
import logging
from typing import Dict, Any

from .base import BaseAgent
from .state import AgentState
from src.ai.llm.base import LLMMessage
from src.ai.tools.market_tools import MarketDataTool, FearGreedTool

logger = logging.getLogger(__name__)


class TradeAgent(BaseAgent):
    """交易Agent"""

    def __init__(self, llm):
        super().__init__("TradeAgent", llm)
        self.market_tool = MarketDataTool()
        self.fng_tool = FearGreedTool()

    def process(self, state: AgentState) -> AgentState:
        """
        处理市场/交易相关请求

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("TradeAgent processing request...")

        # 获取用户消息
        user_message = ""
        for msg in reversed(state["messages"]):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break

        # 判断查询类型
        query_type = self._detect_query_type(user_message)

        logger.info(f"Market query type: {query_type}")

        if query_type == "fear_greed":
            response = self._handle_fear_greed(state)
        elif query_type == "market_overview":
            response = self._handle_market_overview(state)
        else:
            # 默认：市场概览 + 恐慌贪婪指数
            response = self._handle_comprehensive_market(state)

        state = self._add_message(state, "assistant", response)
        state["current_agent"] = "trade_agent"
        state["final_response"] = response
        state["next_action"] = "end"

        return state

    def _detect_query_type(self, text: str) -> str:
        """检测查询类型"""
        text_lower = text.lower()

        if any(keyword in text_lower for keyword in ["恐慌", "贪婪", "情绪", "fear", "greed"]):
            return "fear_greed"
        elif any(keyword in text_lower for keyword in ["市场", "行情", "价格", "market", "price"]):
            return "market_overview"
        else:
            return "comprehensive"

    def _handle_fear_greed(self, state: AgentState) -> str:
        """处理恐慌贪婪指数查询"""
        tool_result = self.fng_tool.execute()

        state["tool_results"].append({
            "tool": "fear_greed_index",
            "result": tool_result.to_dict()
        })

        if tool_result.success and tool_result.data:
            fng_data = tool_result.data
            response = self._format_fng_response(fng_data)
        else:
            response = "抱歉，无法获取恐慌贪婪指数。请稍后再试。"

        return response

    def _handle_market_overview(self, state: AgentState) -> str:
        """处理市场概览查询"""
        tool_result = self.market_tool.execute(limit=10)

        state["tool_results"].append({
            "tool": "market_data",
            "result": tool_result.to_dict()
        })

        if tool_result.success and tool_result.data:
            market_data = tool_result.data
            response = self._format_market_response(market_data)
        else:
            response = "抱歉，无法获取市场数据。请稍后再试。"

        return response

    def _handle_comprehensive_market(self, state: AgentState) -> str:
        """综合市场报告：市场数据 + 恐慌贪婪指数"""
        # 获取市场数据
        market_result = self.market_tool.execute(limit=10)
        fng_result = self.fng_tool.execute()

        state["tool_results"].extend([
            {"tool": "market_data", "result": market_result.to_dict()},
            {"tool": "fear_greed_index", "result": fng_result.to_dict()}
        ])

        response = "📊 **市场综合报告**\n\n"

        # 恐慌贪婪指数
        if fng_result.success and fng_result.data:
            fng_data = fng_result.data
            value = fng_data.get('value', 0)
            classification = fng_data.get('value_classification', 'Unknown')
            interpretation = fng_data.get('interpretation', '')

            response += f"🎭 **市场情绪**\n"
            response += f"  恐慌贪婪指数：{value}/100 ({classification})\n"
            response += f"  解读：{interpretation}\n\n"

        # 市场数据
        if market_result.success and market_result.data:
            market_data = market_result.data
            response += f"💰 **Top 10 加密货币**\n\n"

            for i, coin in enumerate(market_data[:10], 1):
                symbol = coin.get('symbol', 'N/A')
                name = coin.get('name', 'N/A')
                price = coin.get('current_price', 0)
                change = coin.get('price_change_24h', 0)

                # 涨跌emoji
                emoji = "🔺" if change > 0 else "🔻" if change < 0 else "➖"

                response += f"{i}. {symbol} ({name})\n"
                response += f"   价格: ${price:,.2f} | 24h: {emoji} {change:+.2f}%\n\n"
        else:
            response += "  ⚠️ 暂时无法获取市场数据\n"

        return response

    def _format_fng_response(self, fng_data: dict) -> str:
        """格式化恐慌贪婪指数响应"""
        value = fng_data.get('value', 0)
        classification = fng_data.get('value_classification', 'Unknown')
        interpretation = fng_data.get('interpretation', '')

        response = f"🎭 **加密货币恐慌贪婪指数**\n\n"
        response += f"📊 当前指数：**{value}/100**\n"
        response += f"📈 市场状态：**{classification}**\n\n"

        # 可视化指标
        bar_length = int(value / 5)  # 0-20个方块
        bar = "█" * bar_length + "░" * (20 - bar_length)
        response += f"[{bar}] {value}\n\n"

        response += f"💡 **解读**：\n{interpretation}\n\n"

        response += "---\n"
        response += "📌 指数说明：\n"
        response += "• 0-24: 极度恐慌\n"
        response += "• 25-44: 恐慌\n"
        response += "• 45-55: 中性\n"
        response += "• 56-75: 贪婪\n"
        response += "• 76-100: 极度贪婪\n"

        return response

    def _format_market_response(self, market_data: list) -> str:
        """格式化市场数据响应"""
        response = f"💰 **加密货币市场概览** (Top {len(market_data)})\n\n"

        for i, coin in enumerate(market_data, 1):
            symbol = coin.get('symbol', 'N/A')
            name = coin.get('name', 'N/A')
            price = coin.get('current_price', 0)
            change = coin.get('price_change_24h', 0)
            volume = coin.get('total_volume', 0)

            # 涨跌emoji和颜色
            if change > 5:
                emoji = "🚀"
            elif change > 0:
                emoji = "🔺"
            elif change < -5:
                emoji = "💥"
            elif change < 0:
                emoji = "🔻"
            else:
                emoji = "➖"

            response += f"{i}. **{symbol}** ({name})\n"
            response += f"   💵 价格: ${price:,.2f}\n"
            response += f"   {emoji} 24h变化: {change:+.2f}%\n"
            response += f"   📊 成交量: ${volume:,.0f}\n\n"

        return response

    def _get_system_prompt(self) -> str:
        return "你是市场分析专家，擅长加密货币市场数据分析和情绪判断。"
