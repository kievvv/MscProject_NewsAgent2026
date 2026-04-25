"""
Deep Dive Skill
深度话题分析技能
"""
import logging
from typing import List, Dict, Any

from .base import BaseSkill, SkillStep
from src.ai.tools.news_tools import NewsSearchTool
from src.ai.tools.analysis_tools import KeywordExtractionTool, TrendAnalysisTool, SimilarityTool

logger = logging.getLogger(__name__)


class DeepDiveSkill(BaseSkill):
    """深度话题分析技能"""

    def __init__(self):
        super().__init__(
            name="DeepDive",
            description="对特定话题进行深度分析，包括新闻、关键词、趋势和相关内容"
        )
        self.news_tool = NewsSearchTool()
        self.keyword_tool = KeywordExtractionTool()
        self.trend_tool = TrendAnalysisTool()
        self.similarity_tool = SimilarityTool()

    def define_steps(self, params: Dict[str, Any]) -> List[SkillStep]:
        """定义执行步骤"""
        topic = params.get('topic', 'bitcoin')

        return [
            SkillStep(
                name="search_news",
                description=f"搜索关于'{topic}'的新闻",
                tool_name="news_search",
                params={"keyword": topic, "days": 7, "limit": 10}
            ),
            SkillStep(
                name="extract_keywords",
                description="从新闻中提取关键词",
                tool_name="keyword_extraction",
                params={"text": topic, "top_n": 10}
            ),
            SkillStep(
                name="analyze_trend",
                description=f"分析'{topic}'的趋势",
                tool_name="trend_analysis",
                params={"keyword": topic, "days": 30}
            ),
            SkillStep(
                name="find_similar",
                description="查找相似内容",
                tool_name="similarity_search",
                params={"text": topic, "limit": 5}
            ),
        ]

    def _execute_step(self, step: SkillStep):
        """执行单个步骤"""
        try:
            if step.tool_name == "news_search":
                keyword = step.params.get("keyword", "")
                days = step.params.get("days", 7)
                limit = step.params.get("limit", 10)
                result = self.news_tool.execute(keyword=keyword, days=days, limit=limit)
                step.result = result.data if result.success else None

            elif step.tool_name == "keyword_extraction":
                text = step.params.get("text", "")
                top_n = step.params.get("top_n", 10)
                # 如果前一步有新闻结果，从新闻中提取关键词
                if self.steps and self.steps[0].result:
                    news_texts = [news.get('text', '') for news in self.steps[0].result]
                    text = ' '.join(news_texts[:5])  # 使用前5条新闻
                result = self.keyword_tool.execute(text=text, top_n=top_n)
                step.result = result.data if result.success else None

            elif step.tool_name == "trend_analysis":
                keyword = step.params.get("keyword", "")
                days = step.params.get("days", 30)
                result = self.trend_tool.execute(keyword=keyword, days=days)
                step.result = result.data if result.success else None

            elif step.tool_name == "similarity_search":
                text = step.params.get("text", "")
                limit = step.params.get("limit", 5)
                result = self.similarity_tool.execute(text=text, limit=limit, threshold=0.6)
                step.result = result.data if result.success else None

        except Exception as e:
            logger.error(f"Step execution error: {e}")
            step.result = None
            raise

    def generate_report(self, steps: List[SkillStep]) -> str:
        """生成深度分析报告"""
        # 获取话题
        topic = steps[0].params.get('keyword', '未知话题')

        report = f"# 🔍 深度分析报告：{topic}\n\n"
        report += f"**生成时间**: {self._get_current_time()}\n\n"
        report += "---\n\n"

        # 1. 新闻汇总
        news_step = steps[0]
        if news_step.result and news_step.result:
            report += f"## 📰 相关新闻（共 {len(news_step.result)} 条）\n\n"
            for i, news in enumerate(news_step.result[:5], 1):
                title = news.get('title', 'N/A')
                text = news.get('text', '')[:100]
                date = news.get('date', 'N/A')
                report += f"### {i}. {title}\n"
                report += f"**日期**: {date}\n"
                report += f"**摘要**: {text}...\n\n"
        else:
            report += "## 📰 相关新闻\n\n暂无数据\n\n"

        # 2. 关键词分析
        keyword_step = steps[1]
        if keyword_step.result and keyword_step.result:
            report += "## 🔑 核心关键词\n\n"
            report += "| 排名 | 关键词 | 相关度 |\n"
            report += "|------|--------|--------|\n"
            for i, kw in enumerate(keyword_step.result[:10], 1):
                keyword = kw.get('keyword', 'N/A')
                score = kw.get('score', 0)
                report += f"| {i} | {keyword} | {score:.3f} |\n"
            report += "\n"
        else:
            report += "## 🔑 核心关键词\n\n暂无数据\n\n"

        # 3. 趋势分析
        trend_step = steps[2]
        if trend_step.result:
            trend = trend_step.result
            report += "## 📈 趋势分析（30天）\n\n"
            report += f"**总出现次数**: {trend.get('total_count', 0)}\n"
            report += f"**活跃天数**: {trend.get('active_days', 0)}\n"
            report += f"**平均每日**: {trend.get('avg_daily_count', 0):.1f} 次\n"
            report += f"**峰值日期**: {trend.get('peak_date', 'N/A')}\n"
            report += f"**峰值次数**: {trend.get('peak_count', 0)}\n\n"

            # 最近走势
            daily_trend = trend.get('daily_trend', [])
            if daily_trend:
                report += "**最近走势**:\n\n"
                for day in daily_trend[:7]:
                    date = day.get('date', 'N/A')
                    count = day.get('count', 0)
                    bar = "█" * min(count, 20)
                    report += f"- {date}: {bar} ({count})\n"
                report += "\n"
        else:
            report += "## 📈 趋势分析\n\n暂无数据\n\n"

        # 4. 相似内容
        similar_step = steps[3]
        if similar_step.result and similar_step.result:
            report += "## 🔗 相关内容\n\n"
            for i, similar in enumerate(similar_step.result, 1):
                title = similar.get('title', 'N/A')
                score = similar.get('similarity_score', 0)
                date = similar.get('date', 'N/A')
                report += f"{i}. **{title}** (相似度: {score:.2f})\n"
                report += f"   *{date}*\n\n"
        else:
            report += "## 🔗 相关内容\n\n暂无数据\n\n"

        report += "---\n\n"
        report += "## 💡 分析总结\n\n"

        # 智能总结
        total_news = len(news_step.result) if news_step.result else 0
        total_count = trend_step.result.get('total_count', 0) if trend_step.result else 0

        if total_news > 0 and total_count > 0:
            report += f"关于'{topic}'的话题在过去30天内共出现 {total_count} 次，"
            report += f"最近7天有 {total_news} 条相关新闻报道。"
            if trend_step.result and trend_step.result.get('avg_daily_count', 0) > 5:
                report += "该话题保持较高热度，值得持续关注。"
            else:
                report += "该话题热度一般，可能存在潜在机会。"
        else:
            report += f"关于'{topic}'的数据较少，建议扩大搜索范围或调整关键词。"

        report += "\n\n---\n\n"
        report += "*本报告由AI自动生成，仅供参考*\n"

        return report

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def build_structured_output(self, steps: List[SkillStep], report: str) -> Dict[str, Any]:
        topic = steps[0].params.get('keyword', '未知话题') if steps else '未知话题'
        news_items = steps[0].result if steps and steps[0].result else []
        evidence_news_ids = [item.get('id') for item in news_items if item.get('id')]
        trend = steps[2].result if len(steps) > 2 and steps[2].result else {}
        keywords = steps[1].result if len(steps) > 1 and steps[1].result else []
        return {
            "title": f"Theme Deep Dive · {topic}",
            "summary": f"围绕 {topic} 生成了一份深度分析，包含新闻、关键词、趋势与相关线索。",
            "key_points": [
                f"共汇总 {len(news_items)} 条相关新闻",
                f"提取到 {len(keywords)} 个核心关键词",
                f"过去周期总出现次数 {trend.get('total_count', 0)}",
            ],
            "evidence_news_ids": evidence_news_ids,
            "risk_notes": [
                "深度分析适合继续追问事件影响与时间演化。",
                "若需要交易决策，建议结合更细粒度市场数据。"
            ],
            "next_actions": [
                "继续问这个主题是否值得短线关注",
                "只看这个主题过去 24 小时的实时新闻"
            ],
            "tool_trace_refs": [step.tool_name for step in steps if step.tool_name],
            "sections": {
                "news": news_items,
                "keywords": keywords,
                "trend": trend,
                "similar": steps[3].result if len(steps) > 3 else [],
            }
        }
