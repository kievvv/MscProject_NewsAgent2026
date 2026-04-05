"""
趋势服务
提供关键词趋势分析和预测功能
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from src.analyzers import get_trend_analyzer
from src.core.models import NewsSource, TrendAnalysis
from src.core.exceptions import ServiceException

logger = logging.getLogger(__name__)


class TrendService:
    """
    趋势服务

    功能：
    1. 关键词趋势分析
    2. 多关键词对比
    3. 异常检测
    4. 增长速度分析
    5. 关联分析
    """

    def __init__(self, source: NewsSource = NewsSource.CRYPTO):
        """
        初始化趋势服务

        Args:
            source: 新闻来源
        """
        self.source = source
        self._trend_analyzer = None

    @property
    def trend_analyzer(self):
        """延迟加载趋势分析器"""
        if self._trend_analyzer is None:
            self._trend_analyzer = get_trend_analyzer()
        return self._trend_analyzer

    def analyze_keyword_trend(self,
                            keyword: str,
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None,
                            granularity: str = 'day') -> TrendAnalysis:
        """
        分析关键词趋势

        Args:
            keyword: 关键词
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            granularity: 时间粒度 ('day', 'week', 'month')

        Returns:
            TrendAnalysis对象
        """
        try:
            # 如果没有指定日期，默认查询最近30天
            if not start_date or not end_date:
                end = datetime.now()
                start = end - timedelta(days=30)
                start_date = start.strftime('%Y-%m-%d')
                end_date = end.strftime('%Y-%m-%d')

            return self.trend_analyzer.analyze_keyword_trend(
                keyword=keyword,
                source=self.source,
                start_date=start_date,
                end_date=end_date,
                granularity=granularity
            )

        except Exception as e:
            logger.error(f"趋势分析失败: {e}")
            raise ServiceException(f"Failed to analyze trend: {e}")

    def compare_keywords(self,
                        keywords: List[str],
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        对比多个关键词的趋势

        Args:
            keywords: 关键词列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            对比结果字典
        """
        try:
            # 默认最近30天
            if not start_date or not end_date:
                end = datetime.now()
                start = end - timedelta(days=30)
                start_date = start.strftime('%Y-%m-%d')
                end_date = end.strftime('%Y-%m-%d')

            return self.trend_analyzer.compare_keywords(
                keywords=keywords,
                source=self.source,
                start_date=start_date,
                end_date=end_date
            )

        except Exception as e:
            logger.error(f"关键词对比失败: {e}")
            raise ServiceException(f"Failed to compare keywords: {e}")

    def detect_anomalies(self,
                        keyword: str,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        sensitivity: float = 2.0) -> Dict[str, Any]:
        """
        检测关键词热度异常

        Args:
            keyword: 关键词
            start_date: 开始日期
            end_date: 结束日期
            sensitivity: 敏感度（标准差倍数，越大越不敏感）

        Returns:
            异常检测结果
        """
        try:
            # 默认最近60天（需要更多数据来检测异常）
            if not start_date or not end_date:
                end = datetime.now()
                start = end - timedelta(days=60)
                start_date = start.strftime('%Y-%m-%d')
                end_date = end.strftime('%Y-%m-%d')

            return self.trend_analyzer.detect_anomalies(
                keyword=keyword,
                source=self.source,
                start_date=start_date,
                end_date=end_date,
                sensitivity=sensitivity
            )

        except Exception as e:
            logger.error(f"异常检测失败: {e}")
            raise ServiceException(f"Failed to detect anomalies: {e}")

    def calculate_growth_velocity(self,
                                 keyword: str,
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        计算关键词增长速度

        Args:
            keyword: 关键词
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            增长速度分析结果
        """
        try:
            # 默认最近30天
            if not start_date or not end_date:
                end = datetime.now()
                start = end - timedelta(days=30)
                start_date = start.strftime('%Y-%m-%d')
                end_date = end.strftime('%Y-%m-%d')

            return self.trend_analyzer.calculate_growth_velocity(
                keyword=keyword,
                source=self.source,
                start_date=start_date,
                end_date=end_date
            )

        except Exception as e:
            logger.error(f"增长速度计算失败: {e}")
            raise ServiceException(f"Failed to calculate growth velocity: {e}")

    def analyze_correlation(self,
                          keyword1: str,
                          keyword2: str,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        分析两个关键词的关联性

        Args:
            keyword1: 关键词1
            keyword2: 关键词2
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            关联分析结果
        """
        try:
            # 默认最近60天
            if not start_date or not end_date:
                end = datetime.now()
                start = end - timedelta(days=60)
                start_date = start.strftime('%Y-%m-%d')
                end_date = end.strftime('%Y-%m-%d')

            return self.trend_analyzer.analyze_keyword_correlation(
                keyword1=keyword1,
                keyword2=keyword2,
                source=self.source,
                start_date=start_date,
                end_date=end_date
            )

        except Exception as e:
            logger.error(f"关联分析失败: {e}")
            raise ServiceException(f"Failed to analyze correlation: {e}")

    def get_hot_dates(self,
                     keyword: str,
                     top_n: int = 10) -> List[Dict[str, Any]]:
        """
        获取关键词最热门的日期

        Args:
            keyword: 关键词
            top_n: 返回前N天

        Returns:
            热门日期列表
        """
        try:
            return self.trend_analyzer.get_hot_dates(
                keyword=keyword,
                source=self.source,
                top_n=top_n
            )

        except Exception as e:
            logger.error(f"获取热门日期失败: {e}")
            return []

    def get_trending_keywords(self,
                            days: int = 7,
                            top_n: int = 10,
                            min_count: int = 5) -> List[Dict[str, Any]]:
        """
        获取当前热门关键词（基于最近的趋势）

        Args:
            days: 统计最近N天
            top_n: 返回前N个
            min_count: 最小出现次数

        Returns:
            热门关键词列表 [{'keyword': str, 'count': int, 'trend': str}]
        """
        try:
            # 获取最近的日期范围
            end = datetime.now()
            start = end - timedelta(days=days)
            start_date = start.strftime('%Y-%m-%d')
            end_date = end.strftime('%Y-%m-%d')

            # 获取关键词统计
            from src.analyzers import get_similarity_analyzer
            analyzer = get_similarity_analyzer()
            stats = analyzer.get_keyword_statistics(
                source=self.source,
                start_date=start_date,
                end_date=end_date
            )

            # 过滤并排序
            keyword_counter = stats['keyword_counter']
            candidates = [
                (kw, count)
                for kw, count in keyword_counter.items()
                if count >= min_count
            ]
            candidates.sort(key=lambda x: x[1], reverse=True)

            # 分析趋势
            results = []
            for keyword, count in candidates[:top_n * 2]:  # 取更多候选，因为有些可能分析失败
                try:
                    # 分析增长速度
                    velocity_result = self.trend_analyzer.calculate_growth_velocity(
                        keyword=keyword,
                        source=self.source,
                        start_date=start_date,
                        end_date=end_date
                    )

                    trend_direction = velocity_result['summary']['trend']

                    results.append({
                        'keyword': keyword,
                        'count': count,
                        'trend': trend_direction,
                        'avg_velocity': velocity_result['summary']['avg_velocity']
                    })

                    if len(results) >= top_n:
                        break

                except Exception as e:
                    logger.debug(f"分析关键词 '{keyword}' 失败: {e}")
                    continue

            # 按趋势排序（加速中的排前面）
            results.sort(key=lambda x: (
                1 if x['trend'] == 'accelerating' else
                2 if x['trend'] == 'stable' else
                3,
                -x['count']
            ))

            return results

        except Exception as e:
            logger.error(f"获取热门关键词失败: {e}")
            return []

    def analyze_keyword_lifecycle(self,
                                 keyword: str,
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        分析关键词生命周期（兴起、高峰、衰落）

        Args:
            keyword: 关键词
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            生命周期分析结果
        """
        try:
            # 默认查询更长时间（90天）以观察完整生命周期
            if not start_date or not end_date:
                end = datetime.now()
                start = end - timedelta(days=90)
                start_date = start.strftime('%Y-%m-%d')
                end_date = end.strftime('%Y-%m-%d')

            # 获取趋势
            trend = self.trend_analyzer.analyze_keyword_trend(
                keyword=keyword,
                source=self.source,
                start_date=start_date,
                end_date=end_date,
                granularity='day'
            )

            if not trend.daily_trend or len(trend.daily_trend) < 7:
                return {
                    'keyword': keyword,
                    'stage': 'insufficient_data',
                    'description': '数据不足，无法判断生命周期'
                }

            # 获取增长速度
            velocity_result = self.trend_analyzer.calculate_growth_velocity(
                keyword=keyword,
                source=self.source,
                start_date=start_date,
                end_date=end_date
            )

            # 检测异常
            anomaly_result = self.trend_analyzer.detect_anomalies(
                keyword=keyword,
                source=self.source,
                start_date=start_date,
                end_date=end_date,
                sensitivity=1.5
            )

            # 判断生命周期阶段
            avg_velocity = velocity_result['summary']['avg_velocity']
            trend_direction = velocity_result['summary']['trend']
            recent_data = trend.daily_trend[-7:]  # 最近7天
            recent_avg = sum(d['count'] for d in recent_data) / len(recent_data)
            overall_avg = trend.avg_daily_count

            # 阶段判断逻辑
            if trend_direction == 'accelerating' and recent_avg > overall_avg:
                stage = 'rising'
                description = f"关键词处于上升期，平均增速 {avg_velocity:.2%}"
            elif trend_direction == 'stable' and recent_avg >= overall_avg * 0.8:
                stage = 'peak'
                description = f"关键词处于高峰期，热度稳定在 {recent_avg:.1f}/天"
            elif trend_direction == 'decelerating' or recent_avg < overall_avg * 0.5:
                stage = 'declining'
                description = f"关键词处于衰落期，热度下降至 {recent_avg:.1f}/天"
            else:
                stage = 'stable'
                description = f"关键词热度平稳，平均 {recent_avg:.1f}/天"

            return {
                'keyword': keyword,
                'stage': stage,
                'description': description,
                'statistics': {
                    'total_count': trend.total_count,
                    'active_days': trend.active_days,
                    'peak_date': trend.peak_date,
                    'peak_count': trend.peak_count,
                    'avg_daily': trend.avg_daily_count,
                    'recent_avg': recent_avg,
                    'avg_velocity': avg_velocity,
                },
                'anomalies': anomaly_result.get('anomalies', []),
                'trend_data': trend.daily_trend
            }

        except Exception as e:
            logger.error(f"生命周期分析失败: {e}")
            raise ServiceException(f"Failed to analyze lifecycle: {e}")

    def predict_trend(self,
                     keyword: str,
                     days: int = 7) -> Dict[str, Any]:
        """
        简单趋势预测（基于历史数据）

        Args:
            keyword: 关键词
            days: 预测未来N天

        Returns:
            预测结果
        """
        try:
            # 获取历史数据（最近30天）
            end = datetime.now()
            start = end - timedelta(days=30)
            start_date = start.strftime('%Y-%m-%d')
            end_date = end.strftime('%Y-%m-%d')

            # 获取增长速度
            velocity_result = self.trend_analyzer.calculate_growth_velocity(
                keyword=keyword,
                source=self.source,
                start_date=start_date,
                end_date=end_date
            )

            # 获取趋势
            trend = self.trend_analyzer.analyze_keyword_trend(
                keyword=keyword,
                source=self.source,
                start_date=start_date,
                end_date=end_date
            )

            if not trend.daily_trend:
                return {
                    'keyword': keyword,
                    'prediction': 'insufficient_data',
                    'confidence': 'low'
                }

            # 简单预测：基于平均速度
            avg_velocity = velocity_result['summary']['avg_velocity']
            recent_count = trend.daily_trend[-1]['count'] if trend.daily_trend else 0

            # 预测未来值
            predictions = []
            current_value = recent_count
            for i in range(1, days + 1):
                # 简单线性预测
                predicted_value = max(0, current_value * (1 + avg_velocity))
                predictions.append({
                    'day': i,
                    'predicted_count': int(predicted_value)
                })
                current_value = predicted_value

            # 判断置信度
            trend_direction = velocity_result['summary']['trend']
            if trend_direction == 'stable':
                confidence = 'high'
            elif abs(avg_velocity) < 0.2:
                confidence = 'medium'
            else:
                confidence = 'low'

            return {
                'keyword': keyword,
                'prediction': trend_direction,
                'confidence': confidence,
                'current_count': recent_count,
                'avg_velocity': avg_velocity,
                'future_predictions': predictions
            }

        except Exception as e:
            logger.error(f"趋势预测失败: {e}")
            return {
                'keyword': keyword,
                'prediction': 'error',
                'confidence': 'low',
                'error': str(e)
            }


# 便捷函数
def get_trend_service(source: NewsSource = NewsSource.CRYPTO) -> TrendService:
    """
    获取趋势服务实例

    Args:
        source: 新闻来源

    Returns:
        TrendService实例
    """
    return TrendService(source=source)
