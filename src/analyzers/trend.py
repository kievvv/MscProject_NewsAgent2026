"""
趋势分析器
提供关键词热度趋势分析、异常检测、增长速度分析、关联分析等功能
"""
import logging
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, Counter

import numpy as np

from src.data.repositories.news import NewsRepository
from src.data.repositories.keyword import TrendRepository
from src.core.models import NewsSource, TrendAnalysis
from src.core.exceptions import AnalyzerException
from config.settings import settings

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """
    趋势分析器

    功能：
    1. 基础趋势分析（热度统计、时间序列）
    2. 异常检测（突增、突降）
    3. 增长速度分析（速度、加速度）
    4. 关联分析（关键词相关性）
    5. 可视化支持
    """

    def __init__(self,
                 news_repo: Optional[NewsRepository] = None,
                 trend_repo: Optional[TrendRepository] = None):
        """
        初始化趋势分析器

        Args:
            news_repo: 新闻仓储
            trend_repo: 趋势仓储
        """
        self.news_repo = news_repo
        self.trend_repo = trend_repo

    def analyze_keyword_trend(self,
                             keyword: str,
                             source: NewsSource = NewsSource.CRYPTO,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None,
                             granularity: str = 'day') -> TrendAnalysis:
        """
        分析关键词热度趋势

        Args:
            keyword: 关键词
            source: 新闻来源
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            granularity: 时间粒度 ('day', 'week', 'month')

        Returns:
            TrendAnalysis对象
        """
        # 获取新闻仓储
        if not self.news_repo:
            repo = NewsRepository(source=source)
        else:
            repo = self.news_repo

        # 查询新闻
        if start_date and end_date:
            news_list = repo.get_by_date_range(start_date, end_date)
        else:
            news_list = repo.get_all(limit=10000)

        # 统计每日出现次数
        daily_counts: Dict[str, int] = defaultdict(int)

        for news in news_list:
            if not news.keywords:
                continue

            # 检查关键词是否包含
            keyword_list = news.keyword_list
            if keyword.lower() in [k.lower() for k in keyword_list]:
                # 提取日期
                if news.date:
                    date_str = news.date.split('T')[0] if 'T' in news.date else news.date.split(' ')[0]
                    daily_counts[date_str] += 1

        # 按时间粒度聚合
        if granularity == 'week':
            daily_counts = self._aggregate_by_week(daily_counts)
        elif granularity == 'month':
            daily_counts = self._aggregate_by_month(daily_counts)

        # 构建时间序列
        sorted_dates = sorted(daily_counts.keys())
        daily_trend = [
            {'date': date, 'count': daily_counts[date]}
            for date in sorted_dates
        ]

        # 计算统计信息
        total_count = sum(daily_counts.values())
        active_days = len(daily_counts)

        # 找出峰值日期
        peak_date = None
        peak_count = 0
        if daily_trend:
            peak_item = max(daily_trend, key=lambda x: x['count'])
            peak_date = peak_item['date']
            peak_count = peak_item['count']

        # 日期范围
        date_range = (sorted_dates[0], sorted_dates[-1]) if sorted_dates else ('', '')

        # 平均每日次数
        avg_daily_count = total_count / active_days if active_days > 0 else 0

        return TrendAnalysis(
            keyword=keyword,
            total_count=total_count,
            active_days=active_days,
            date_range=date_range,
            daily_trend=daily_trend,
            avg_daily_count=avg_daily_count,
            peak_date=peak_date,
            peak_count=peak_count,
        )

    def compare_keywords(self,
                        keywords: List[str],
                        source: NewsSource = NewsSource.CRYPTO,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        对比多个关键词的热度

        Args:
            keywords: 关键词列表
            source: 新闻来源
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            对比结果字典
        """
        comparison_results = []
        all_dates = set()
        keyword_data = {}

        # 分析每个关键词
        for keyword in keywords:
            trend = self.analyze_keyword_trend(keyword, source, start_date, end_date)

            # 收集统计信息
            comparison_results.append({
                'keyword': keyword,
                'total_count': trend.total_count,
                'active_days': trend.active_days,
                'avg_daily': trend.avg_daily_count
            })

            # 收集时间序列数据
            keyword_data[keyword] = {item['date']: item['count'] for item in trend.daily_trend}
            all_dates.update(keyword_data[keyword].keys())

        # 构建完整的时间序列（填充缺失日期）
        sorted_dates = sorted(all_dates)
        time_series_data = {}

        for keyword in keywords:
            time_series_data[keyword] = [
                keyword_data[keyword].get(date, 0) for date in sorted_dates
            ]

        # 按总次数排序
        comparison_results.sort(key=lambda x: x['total_count'], reverse=True)

        return {
            'keywords': keywords,
            'comparison': comparison_results,
            'time_series': {
                'dates': sorted_dates,
                'data': time_series_data
            }
        }

    def detect_anomalies(self,
                        keyword: str,
                        source: NewsSource = NewsSource.CRYPTO,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        sensitivity: float = 2.0) -> Dict[str, Any]:
        """
        检测关键词热度异常波动

        Args:
            keyword: 关键词
            source: 新闻来源
            start_date: 开始日期
            end_date: 结束日期
            sensitivity: 敏感度（标准差倍数，越大越不敏感）

        Returns:
            异常检测结果
        """
        # 获取趋势数据
        trend = self.analyze_keyword_trend(keyword, source, start_date, end_date)

        if not trend.daily_trend or len(trend.daily_trend) < 3:
            return {
                'keyword': keyword,
                'anomalies': [],
                'summary': '数据不足，无法检测异常'
            }

        # 提取时间序列
        dates = [item['date'] for item in trend.daily_trend]
        values = np.array([item['count'] for item in trend.daily_trend])

        # 计算统计指标
        mean = np.mean(values)
        std = np.std(values)

        if std == 0:
            return {
                'keyword': keyword,
                'anomalies': [],
                'summary': '热度无变化'
            }

        # 计算Z分数
        z_scores = (values - mean) / std

        # 检测异常
        anomalies = []

        for i in range(len(values)):
            z_score = z_scores[i]

            # 异常判断：Z分数超过阈值
            if abs(z_score) > sensitivity:
                # 计算变化率
                if i > 0:
                    change_rate = (values[i] - values[i-1]) / (values[i-1] + 1)
                else:
                    change_rate = 0.0

                # 判断类型
                if z_score > 0:
                    anomaly_type = 'surge'
                    description = f"突然爆发：热度达到 {values[i]:.0f} (平均值的 {z_score:.1f} 倍标准差)"
                else:
                    anomaly_type = 'drop'
                    description = f"断崖式下跌：热度降至 {values[i]:.0f} (低于平均值 {abs(z_score):.1f} 倍标准差)"

                anomalies.append({
                    'date': dates[i],
                    'value': int(values[i]),
                    'type': anomaly_type,
                    'z_score': float(z_score),
                    'change_rate': float(change_rate),
                    'description': description
                })

        # 排序（按日期）
        anomalies.sort(key=lambda x: x['date'])

        # 统计摘要
        surge_count = sum(1 for a in anomalies if a['type'] == 'surge')
        drop_count = sum(1 for a in anomalies if a['type'] == 'drop')

        summary = f"检测到 {len(anomalies)} 个异常: {surge_count} 次爆发, {drop_count} 次下跌"

        return {
            'keyword': keyword,
            'anomalies': anomalies,
            'statistics': {
                'mean': float(mean),
                'std': float(std),
                'max': float(np.max(values)),
                'min': float(np.min(values))
            },
            'summary': summary
        }

    def calculate_growth_velocity(self,
                                  keyword: str,
                                  source: NewsSource = NewsSource.CRYPTO,
                                  start_date: Optional[str] = None,
                                  end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        计算热度增长速度（变化率）

        Args:
            keyword: 关键词
            source: 新闻来源
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            增长速度分析结果
        """
        # 获取趋势数据
        trend = self.analyze_keyword_trend(keyword, source, start_date, end_date)

        if not trend.daily_trend or len(trend.daily_trend) < 2:
            return {
                'keyword': keyword,
                'velocity_data': [],
                'summary': {'avg_velocity': 0, 'max_velocity': 0, 'trend': 'stable'}
            }

        # 提取数据
        dates = [item['date'] for item in trend.daily_trend]
        values = np.array([item['count'] for item in trend.daily_trend], dtype=float)

        velocity_data = []
        velocities = []

        for i in range(len(values)):
            # 计算速度（相对于前一天的变化率）
            if i > 0:
                velocity = (values[i] - values[i-1]) / (values[i-1] + 1)
            else:
                velocity = 0.0

            # 计算加速度（速度的变化率）
            if i > 1:
                prev_velocity = (values[i-1] - values[i-2]) / (values[i-2] + 1)
                acceleration = velocity - prev_velocity
            else:
                acceleration = 0.0

            velocity_data.append({
                'date': dates[i],
                'value': int(values[i]),
                'velocity': float(velocity),
                'acceleration': float(acceleration)
            })

            velocities.append(velocity)

        # 统计摘要
        avg_velocity = np.mean(velocities)
        max_velocity = np.max(np.abs(velocities))

        # 判断趋势
        if avg_velocity > 0.1:
            trend_direction = 'accelerating'
        elif avg_velocity < -0.1:
            trend_direction = 'decelerating'
        else:
            trend_direction = 'stable'

        return {
            'keyword': keyword,
            'velocity_data': velocity_data,
            'summary': {
                'avg_velocity': float(avg_velocity),
                'max_velocity': float(max_velocity),
                'trend': trend_direction
            }
        }

    def analyze_keyword_correlation(self,
                                   keyword1: str,
                                   keyword2: str,
                                   source: NewsSource = NewsSource.CRYPTO,
                                   start_date: Optional[str] = None,
                                   end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        分析两个关键词的关联性

        Args:
            keyword1: 关键词1
            keyword2: 关键词2
            source: 新闻来源
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            关联分析结果
        """
        try:
            from scipy import stats
        except ImportError:
            logger.warning("scipy 未安装，无法计算相关系数")
            return {
                'keyword1': keyword1,
                'keyword2': keyword2,
                'correlation': 0.0,
                'p_value': 1.0,
                'co_occurrence': 0,
                'relationship': 'none',
                'description': 'scipy 未安装'
            }

        # 获取两个关键词的趋势
        trend1 = self.analyze_keyword_trend(keyword1, source, start_date, end_date)
        trend2 = self.analyze_keyword_trend(keyword2, source, start_date, end_date)

        if not trend1.daily_trend or not trend2.daily_trend:
            return {
                'keyword1': keyword1,
                'keyword2': keyword2,
                'correlation': 0.0,
                'p_value': 1.0,
                'co_occurrence': 0,
                'relationship': 'none',
                'description': '数据不足'
            }

        # 构建时间序列（对齐日期）
        dates1 = {item['date']: item['count'] for item in trend1.daily_trend}
        dates2 = {item['date']: item['count'] for item in trend2.daily_trend}

        common_dates = sorted(set(dates1.keys()) & set(dates2.keys()))

        if len(common_dates) < 3:
            return {
                'keyword1': keyword1,
                'keyword2': keyword2,
                'correlation': 0.0,
                'p_value': 1.0,
                'co_occurrence': 0,
                'relationship': 'none',
                'description': '共同日期不足'
            }

        # 提取对齐的值
        values1 = np.array([dates1[date] for date in common_dates])
        values2 = np.array([dates2[date] for date in common_dates])

        # 计算相关系数
        correlation, p_value = stats.pearsonr(values1, values2)

        # 计算共现次数（同一天都有提及）
        co_occurrence = len([d for d in common_dates if dates1[d] > 0 and dates2[d] > 0])

        # 判断关系类型
        if p_value < 0.05:  # 显著
            if correlation > 0.5:
                relationship = 'strong_positive'
                description = f"强正相关：两个关键词热度高度一致（相关系数: {correlation:.2f}）"
            elif correlation > 0.2:
                relationship = 'positive'
                description = f"正相关：两个关键词热度同步变化（相关系数: {correlation:.2f}）"
            elif correlation < -0.5:
                relationship = 'strong_negative'
                description = f"强负相关：两个关键词热度反向变化（相关系数: {correlation:.2f}）"
            elif correlation < -0.2:
                relationship = 'negative'
                description = f"负相关：一个上升时另一个下降（相关系数: {correlation:.2f}）"
            else:
                relationship = 'weak'
                description = f"弱相关（相关系数: {correlation:.2f}）"
        else:
            relationship = 'none'
            description = f"无显著相关性（相关系数: {correlation:.2f}, p={p_value:.3f}）"

        return {
            'keyword1': keyword1,
            'keyword2': keyword2,
            'correlation': float(correlation),
            'p_value': float(p_value),
            'co_occurrence': int(co_occurrence),
            'relationship': relationship,
            'description': description
        }

    def get_hot_dates(self,
                     keyword: str,
                     source: NewsSource = NewsSource.CRYPTO,
                     top_n: int = 10) -> List[Dict[str, Any]]:
        """
        获取关键词最热门的日期

        Args:
            keyword: 关键词
            source: 新闻来源
            top_n: 返回前N天

        Returns:
            热门日期列表
        """
        trend = self.analyze_keyword_trend(keyword, source)
        sorted_data = sorted(trend.daily_trend, key=lambda x: x['count'], reverse=True)
        return sorted_data[:top_n]

    def _aggregate_by_week(self, daily_counts: Dict[str, int]) -> Dict[str, int]:
        """按周聚合数据"""
        weekly_counts: Dict[str, int] = defaultdict(int)

        for date_str, count in daily_counts.items():
            try:
                date = datetime.fromisoformat(date_str)
                week_start = date - timedelta(days=date.weekday())
                week_key = week_start.strftime('%Y-%m-%d')
                weekly_counts[week_key] += count
            except Exception as e:
                logger.warning(f"日期解析失败: {date_str}, {e}")
                continue

        return dict(weekly_counts)

    def _aggregate_by_month(self, daily_counts: Dict[str, int]) -> Dict[str, int]:
        """按月聚合数据"""
        monthly_counts: Dict[str, int] = defaultdict(int)

        for date_str, count in daily_counts.items():
            try:
                date = datetime.fromisoformat(date_str)
                month_key = date.strftime('%Y-%m') + '-01'
                monthly_counts[month_key] += count
            except Exception as e:
                logger.warning(f"日期解析失败: {date_str}, {e}")
                continue

        return dict(monthly_counts)


# 全局单例
_trend_analyzer: Optional[TrendAnalyzer] = None


def get_trend_analyzer() -> TrendAnalyzer:
    """
    获取趋势分析器单例

    Returns:
        TrendAnalyzer实例
    """
    global _trend_analyzer
    if _trend_analyzer is None:
        _trend_analyzer = TrendAnalyzer()
    return _trend_analyzer
