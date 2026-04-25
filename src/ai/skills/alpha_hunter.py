"""
Alpha Hunter Skill
Alpha机会挖掘技能
"""
import logging
from typing import List, Dict, Any

from .base import BaseSkill, SkillStep
from src.ai.tools.analysis_tools import TrendAnalysisTool, KeywordExtractionTool
from src.ai.tools.market_tools import MarketDataTool
from src.ai.tools.news_tools import NewsSearchTool

logger = logging.getLogger(__name__)


class AlphaHunterSkill(BaseSkill):
    """Alpha机会挖掘技能"""

    def __init__(self):
        super().__init__(
            name="AlphaHunter",
            description="挖掘潜在Alpha机会：新兴关键词 + 低估资产"
        )
        self.trend_tool = TrendAnalysisTool()
        self.keyword_tool = KeywordExtractionTool()
        self.market_tool = MarketDataTool()
        self.news_tool = NewsSearchTool()

    def define_steps(self, params: Dict[str, Any]) -> List[SkillStep]:
        """定义执行步骤"""
        return [
            SkillStep(
                name="scan_emerging_keywords",
                description="扫描新兴关键词（低频但有上升趋势）",
                tool_name="emerging_keywords"
            ),
            SkillStep(
                name="analyze_market_data",
                description="分析市场数据，寻找高新闻比但低市值的资产",
                tool_name="market_screening"
            ),
            SkillStep(
                name="correlate_news_market",
                description="关联新闻热度与市场表现",
                tool_name="correlation_analysis"
            ),
            SkillStep(
                name="identify_opportunities",
                description="识别潜在Alpha机会",
                tool_name="opportunity_finder"
            ),
        ]

    def _execute_step(self, step: SkillStep):
        """执行单个步骤"""
        try:
            if step.tool_name == "emerging_keywords":
                # 搜索多个热门话题的新闻，提取关键词
                keywords = ["defi", "nft", "layer2", "ai", "gamefi"]
                all_keywords = []

                for keyword in keywords:
                    trend_result = self.trend_tool.execute(keyword=keyword, days=14)
                    if trend_result.success and trend_result.data:
                        trend = trend_result.data
                        # 选择中等热度的关键词（可能是新兴的）
                        if 5 <= trend.get('total_count', 0) <= 50:
                            all_keywords.append({
                                'keyword': keyword,
                                'count': trend.get('total_count', 0),
                                'avg_daily': trend.get('avg_daily_count', 0),
                                'peak_count': trend.get('peak_count', 0)
                            })

                step.result = sorted(all_keywords, key=lambda x: x['avg_daily'], reverse=True)[:5]

            elif step.tool_name == "market_screening":
                # 获取市场数据
                market_result = self.market_tool.execute(limit=20)
                coins = market_result.data.get('coins', []) if market_result.success and isinstance(market_result.data, dict) else []
                if coins:
                    # 筛选：24h涨跌在±5%以内的（波动不大的）
                    screened = []
                    for coin in coins:
                        change = coin.get('price_change_24h', 0)
                        if -5 <= change <= 5:
                            screened.append(coin)

                    step.result = screened[:10]
                else:
                    step.result = []

            elif step.tool_name == "correlation_analysis":
                # 关联分析：对每个币种，检查新闻数量
                market_coins = self.steps[1].result if self.steps[1].result else []
                correlations = []

                for coin in market_coins[:5]:  # 只分析前5个
                    symbol = coin.get('symbol', '')
                    if symbol:
                        news_result = self.news_tool.execute(keyword=symbol, days=7, limit=10)
                        news_count = len(news_result.data) if news_result.success else 0

                        correlations.append({
                            'symbol': symbol,
                            'price': coin.get('current_price', 0),
                            'change_24h': coin.get('price_change_24h', 0),
                            'market_cap': coin.get('market_cap', 0),
                            'news_count': news_count,
                            'news_to_cap_ratio': news_count / (coin.get('market_cap', 1) / 1e9) if coin.get('market_cap', 0) > 0 else 0
                        })

                step.result = sorted(correlations, key=lambda x: x['news_to_cap_ratio'], reverse=True)

            elif step.tool_name == "opportunity_finder":
                # 识别机会：新闻热度高但市值相对较低的
                correlations = self.steps[2].result if self.steps[2].result else []
                opportunities = []

                for item in correlations[:5]:
                    # 高新闻比率 + 市值不太大 = 潜在机会
                    if item.get('news_to_cap_ratio', 0) > 0.5:
                        opportunities.append({
                            'symbol': item.get('symbol'),
                            'reason': '新闻热度高，市值相对较低',
                            'score': item.get('news_to_cap_ratio', 0),
                            'price': item.get('price', 0),
                            'change_24h': item.get('change_24h', 0),
                            'news_count': item.get('news_count', 0)
                        })

                step.result = opportunities

        except Exception as e:
            logger.error(f"Step execution error: {e}")
            step.result = None
            raise

    def generate_report(self, steps: List[SkillStep]) -> str:
        """生成Alpha机会报告"""
        from datetime import datetime

        report = "# 🎯 Alpha机会挖掘报告\n\n"
        report += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        report += "---\n\n"

        # 1. 新兴关键词
        keywords_step = steps[0]
        if keywords_step.result and keywords_step.result:
            report += "## 🌱 新兴关键词（14天数据）\n\n"
            report += "这些关键词具有中等热度，可能代表新兴趋势：\n\n"
            report += "| 关键词 | 总次数 | 平均每日 | 峰值 |\n"
            report += "|--------|--------|----------|------|\n"
            for kw in keywords_step.result:
                keyword = kw.get('keyword', 'N/A')
                count = kw.get('count', 0)
                avg = kw.get('avg_daily', 0)
                peak = kw.get('peak_count', 0)
                report += f"| {keyword} | {count} | {avg:.1f} | {peak} |\n"
            report += "\n"
        else:
            report += "## 🌱 新兴关键词\n\n暂无数据\n\n"

        # 2. 市场筛选
        market_step = steps[1]
        if market_step.result and market_step.result:
            report += "## 📊 市场筛选（波动较小的币种）\n\n"
            report += "这些币种24h涨跌在±5%以内，波动较小：\n\n"
            report += "| 币种 | 价格 | 24h涨跌 | 市值 |\n"
            report += "|------|------|---------|------|\n"
            for coin in market_step.result[:5]:
                symbol = coin.get('symbol', 'N/A')
                price = coin.get('current_price', 0)
                change = coin.get('price_change_24h', 0)
                mcap = coin.get('market_cap', 0)
                emoji = "🔺" if change > 0 else "🔻" if change < 0 else "➖"
                report += f"| {symbol} | ${price:,.2f} | {emoji} {change:+.2f}% | ${mcap/1e9:.2f}B |\n"
            report += "\n"
        else:
            report += "## 📊 市场筛选\n\n暂无数据\n\n"

        # 3. 关联分析
        corr_step = steps[2]
        if corr_step.result and corr_step.result:
            report += "## 🔗 新闻-市值关联分析\n\n"
            report += "| 币种 | 新闻数 | 市值 | 新闻/市值比 |\n"
            report += "|------|--------|------|-------------|\n"
            for item in corr_step.result[:5]:
                symbol = item.get('symbol', 'N/A')
                news_count = item.get('news_count', 0)
                mcap = item.get('market_cap', 0) / 1e9
                ratio = item.get('news_to_cap_ratio', 0)
                report += f"| {symbol} | {news_count} | ${mcap:.2f}B | {ratio:.3f} |\n"
            report += "\n"
        else:
            report += "## 🔗 关联分析\n\n暂无数据\n\n"

        # 4. Alpha机会
        opp_step = steps[3]
        if opp_step.result and opp_step.result:
            report += "## 🎯 潜在Alpha机会\n\n"
            if opp_step.result:
                for i, opp in enumerate(opp_step.result, 1):
                    symbol = opp.get('symbol', 'N/A')
                    reason = opp.get('reason', 'N/A')
                    score = opp.get('score', 0)
                    price = opp.get('price', 0)
                    news_count = opp.get('news_count', 0)

                    report += f"### {i}. {symbol}\n"
                    report += f"**理由**: {reason}\n"
                    report += f"**评分**: {score:.3f}\n"
                    report += f"**价格**: ${price:,.2f}\n"
                    report += f"**新闻数**: {news_count} 条\n"
                    report += f"**建议**: 关注该币种的后续动态，可能存在机会\n\n"
            else:
                report += "未发现明显的Alpha机会。\n\n"
        else:
            report += "## 🎯 潜在Alpha机会\n\n暂无数据\n\n"

        report += "---\n\n"
        report += "## ⚠️ 风险提示\n\n"
        report += "1. 本报告基于数据分析，不构成投资建议\n"
        report += "2. 加密货币市场波动大，投资需谨慎\n"
        report += "3. 建议结合基本面分析和自身风险承受能力\n"
        report += "4. 过去表现不代表未来收益\n\n"

        report += "---\n\n"
        report += "*本报告由AI自动生成，仅供参考*\n"

        return report

    def build_structured_output(self, steps: List[SkillStep], report: str) -> Dict[str, Any]:
        opportunities = steps[3].result if len(steps) > 3 and steps[3].result else []
        keywords = steps[0].result if steps and steps[0].result else []
        return {
            "title": "Opportunity Radar",
            "summary": f"系统已完成 Alpha 机会扫描，当前识别到 {len(opportunities)} 个候选机会。",
            "key_points": [
                f"扫描到 {len(keywords)} 个新兴关键词",
                f"输出 {len(opportunities)} 个潜在机会候选",
            ],
            "evidence_news_ids": [],
            "risk_notes": [
                "该结果更偏机会发现，不等于可直接执行的交易信号。",
                "建议结合主题深挖与更多市场因子验证。"
            ],
            "next_actions": [
                "深挖其中一个机会对应的主题",
                "将机会候选加入观察列表"
            ],
            "tool_trace_refs": [step.tool_name for step in steps if step.tool_name],
            "sections": {
                "emerging_keywords": keywords,
                "market_screening": steps[1].result if len(steps) > 1 else [],
                "correlations": steps[2].result if len(steps) > 2 else [],
                "opportunities": opportunities,
            }
        }
