"""
Daily Briefing Skill
每日市场简报技能
"""
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

from .base import BaseSkill, SkillStep
from src.ai.tools.news_tools import NewsSearchTool
from src.ai.tools.analysis_tools import TrendAnalysisTool
from src.ai.tools.market_tools import MarketDataTool, FearGreedTool

logger = logging.getLogger(__name__)


class DailyBriefingSkill(BaseSkill):
    """每日市场简报技能"""

    def __init__(self):
        super().__init__(
            name="DailyBriefing",
            description="生成每日市场简报，包括最新新闻、趋势分析和市场数据"
        )
        self.news_tool = NewsSearchTool()
        self.trend_tool = TrendAnalysisTool()
        self.market_tool = MarketDataTool()
        self.fng_tool = FearGreedTool()

    def define_steps(self, params: Dict[str, Any]) -> List[SkillStep]:
        """定义执行步骤"""
        return [
            SkillStep(
                name="fetch_market_sentiment",
                description="获取市场情绪指标（恐慌贪婪指数）",
                tool_name="fear_greed_index"
            ),
            SkillStep(
                name="fetch_market_data",
                description="获取Top 10币种市场数据",
                tool_name="market_data"
            ),
            SkillStep(
                name="fetch_latest_news",
                description="获取最近24小时热门新闻",
                tool_name="news_search",
                params={"keyword": "bitcoin ethereum crypto", "days": 1, "limit": 5}
            ),
            SkillStep(
                name="analyze_trends",
                description="分析热门关键词趋势",
                tool_name="trend_analysis",
                params={"keyword": "bitcoin", "days": 7}
            ),
        ]

    def _execute_step(self, step: SkillStep):
        """执行单个步骤"""
        try:
            if step.tool_name == "fear_greed_index":
                result = self.fng_tool.execute()
                step.result = result.data if result.success else None

            elif step.tool_name == "market_data":
                result = self.market_tool.execute(limit=10)
                step.result = result.data if result.success else None

            elif step.tool_name == "news_search":
                keyword = step.params.get("keyword", "")
                days = step.params.get("days", 1)
                limit = step.params.get("limit", 5)
                result = self.news_tool.execute(keyword=keyword, days=days, limit=limit)
                step.result = result.data if result.success else None

            elif step.tool_name == "trend_analysis":
                keyword = step.params.get("keyword", "bitcoin")
                days = step.params.get("days", 7)
                result = self.trend_tool.execute(keyword=keyword, days=days)
                step.result = result.data if result.success else None

        except Exception as e:
            logger.error(f"Step execution error: {e}")
            step.result = None
            raise

    def generate_report(self, steps: List[SkillStep]) -> str:
        """生成每日简报"""
        report = "# 📊 每日市场简报\n\n"
        report += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report += "---\n\n"

        # 1. 市场情绪
        fng_step = steps[0]
        if fng_step.result:
            fng_data = fng_step.result
            report += "## 🎭 市场情绪\n\n"
            report += f"**恐慌贪婪指数**: {fng_data.get('value', 'N/A')}/100\n"
            report += f"**状态**: {fng_data.get('value_classification', 'N/A')}\n"
            report += f"**解读**: {fng_data.get('interpretation', 'N/A')}\n\n"
        else:
            report += "## 🎭 市场情绪\n\n暂无数据\n\n"

        # 2. 市场数据
        market_step = steps[1]
        if market_step.result and market_step.result:
            report += "## 💰 Top 10 加密货币\n\n"
            report += "| 排名 | 币种 | 价格 | 24h涨跌 |\n"
            report += "|------|------|------|--------|\n"
            for i, coin in enumerate(market_step.result[:10], 1):
                symbol = coin.get('symbol', 'N/A')
                price = coin.get('current_price', 0)
                change = coin.get('price_change_24h', 0)
                emoji = "🔺" if change > 0 else "🔻" if change < 0 else "➖"
                report += f"| {i} | {symbol} | ${price:,.2f} | {emoji} {change:+.2f}% |\n"
            report += "\n"
        else:
            report += "## 💰 市场数据\n\n暂无数据\n\n"

        # 3. 最新新闻
        news_step = steps[2]
        if news_step.result and news_step.result:
            report += "## 📰 最新新闻（24小时）\n\n"
            for i, news in enumerate(news_step.result[:5], 1):
                title = news.get('title', 'N/A')
                date = news.get('date', 'N/A')
                report += f"{i}. **{title}**\n"
                report += f"   *{date}*\n\n"
        else:
            report += "## 📰 最新新闻\n\n暂无数据\n\n"

        # 4. 趋势分析
        trend_step = steps[3]
        if trend_step.result:
            trend = trend_step.result
            report += "## 📈 趋势分析\n\n"
            report += f"**关键词**: {trend.get('keyword', 'N/A')}\n"
            report += f"**总出现次数**: {trend.get('total_count', 0)}\n"
            report += f"**活跃天数**: {trend.get('active_days', 0)}\n"
            report += f"**平均每日**: {trend.get('avg_daily_count', 0):.1f} 次\n"
            if trend.get('peak_date'):
                report += f"**峰值**: {trend.get('peak_count', 0)} 次 ({trend.get('peak_date')})\n"
            report += "\n"
        else:
            report += "## 📈 趋势分析\n\n暂无数据\n\n"

        report += "---\n\n"
        report += "*本简报由AI自动生成，仅供参考*\n"

        return report
