"""
市场服务
提供市场数据获取和分析功能（价格、成交量等）
"""
import logging
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from src.core.models import NewsSource
from src.core.exceptions import ServiceException

logger = logging.getLogger(__name__)

# API Endpoints
FNG_API_ENDPOINT = "https://api.alternative.me/fng/?limit=1"
COINGECKO_MARKET_ENDPOINT = "https://api.coingecko.com/api/v3/coins/markets"


class MarketService:
    """
    市场服务

    功能：
    1. 获取实时价格
    2. 获取历史价格
    3. 计算价格变化
    4. 分析新闻与价格的关联
    5. 市场情绪分析

    注意：这是一个抽象层，实际的市场数据需要集成外部API
    （如 CoinGecko, Binance API 等）
    """

    def __init__(self, source: NewsSource = NewsSource.CRYPTO):
        """
        初始化市场服务

        Args:
            source: 新闻来源
        """
        self.source = source

        # 缓存市场数据（实际项目中应使用Redis等）
        self._price_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300  # 5分钟缓存

    def get_current_price(self, symbol: str, currency: str = 'USD') -> Optional[Dict[str, Any]]:
        """
        获取当前价格

        Args:
            symbol: 交易对符号（如 BTC, ETH）
            currency: 计价货币

        Returns:
            价格信息字典
        """
        try:
            # 检查缓存
            cache_key = f"{symbol}_{currency}"
            if cache_key in self._price_cache:
                cached = self._price_cache[cache_key]
                if self._is_cache_valid(cached['timestamp']):
                    return cached['data']

            # TODO: 实际项目中应该调用外部API
            # 示例：使用 CoinGecko API
            # import requests
            # response = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies={currency}")
            # data = response.json()

            # 这里返回模拟数据
            logger.warning(f"使用模拟数据: {symbol}/{currency}")
            data = {
                'symbol': symbol,
                'currency': currency,
                'price': 0.0,
                'change_24h': 0.0,
                'volume_24h': 0.0,
                'timestamp': datetime.now().isoformat()
            }

            # 更新缓存
            self._price_cache[cache_key] = {
                'data': data,
                'timestamp': datetime.now()
            }

            return data

        except Exception as e:
            logger.error(f"获取价格失败: {e}")
            return None

    def get_historical_price(self,
                           symbol: str,
                           start_date: str,
                           end_date: str,
                           currency: str = 'USD') -> List[Dict[str, Any]]:
        """
        获取历史价格

        Args:
            symbol: 交易对符号
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            currency: 计价货币

        Returns:
            历史价格列表
        """
        try:
            # TODO: 实际项目中应该调用外部API
            # 示例：使用 CoinGecko API
            # import requests
            # response = requests.get(f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart/range?vs_currency={currency}&from={start_ts}&to={end_ts}")
            # data = response.json()

            logger.warning(f"使用模拟数据: {symbol} 历史价格")
            return []

        except Exception as e:
            logger.error(f"获取历史价格失败: {e}")
            return []

    def calculate_price_change(self,
                             symbol: str,
                             days: int = 7) -> Optional[Dict[str, Any]]:
        """
        计算价格变化

        Args:
            symbol: 交易对符号
            days: 统计天数

        Returns:
            价格变化信息
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            historical = self.get_historical_price(
                symbol,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )

            if not historical:
                return None

            # 计算变化率
            first_price = historical[0]['price']
            last_price = historical[-1]['price']
            change_rate = (last_price - first_price) / first_price if first_price > 0 else 0

            # 计算最高/最低
            max_price = max(h['price'] for h in historical)
            min_price = min(h['price'] for h in historical)

            return {
                'symbol': symbol,
                'period_days': days,
                'start_price': first_price,
                'end_price': last_price,
                'change_rate': change_rate,
                'max_price': max_price,
                'min_price': min_price,
                'volatility': (max_price - min_price) / min_price if min_price > 0 else 0
            }

        except Exception as e:
            logger.error(f"计算价格变化失败: {e}")
            return None

    def analyze_news_price_correlation(self,
                                      symbol: str,
                                      days: int = 30) -> Dict[str, Any]:
        """
        分析新闻热度与价格变化的关联

        Args:
            symbol: 交易对符号
            days: 统计天数

        Returns:
            关联分析结果
        """
        try:
            # 获取新闻趋势
            from src.analyzers import get_trend_analyzer
            trend_analyzer = get_trend_analyzer()

            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            news_trend = trend_analyzer.analyze_keyword_trend(
                keyword=symbol,
                source=self.source,
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d')
            )

            # 获取价格数据
            price_change = self.calculate_price_change(symbol, days)

            if not price_change:
                return {
                    'symbol': symbol,
                    'correlation': 'insufficient_data'
                }

            # 简单关联分析
            # 实际项目中应该使用更复杂的统计方法（如Pearson相关系数）
            news_growth = news_trend.total_count / news_trend.active_days if news_trend.active_days > 0 else 0
            price_growth = price_change['change_rate']

            # 判断关联类型
            if news_growth > 10 and price_growth > 0.1:
                correlation_type = 'positive_strong'
                description = "新闻热度与价格上涨呈强正相关"
            elif news_growth > 5 and price_growth < -0.1:
                correlation_type = 'negative_strong'
                description = "新闻热度增加但价格下跌（可能是负面新闻）"
            elif news_growth < 2 and abs(price_growth) < 0.05:
                correlation_type = 'weak'
                description = "新闻热度低且价格稳定"
            else:
                correlation_type = 'unclear'
                description = "新闻与价格关联不明显"

            return {
                'symbol': symbol,
                'period_days': days,
                'news_stats': {
                    'total_count': news_trend.total_count,
                    'active_days': news_trend.active_days,
                    'avg_daily': news_trend.avg_daily_count
                },
                'price_stats': price_change,
                'correlation_type': correlation_type,
                'description': description
            }

        except Exception as e:
            logger.error(f"新闻价格关联分析失败: {e}")
            return {
                'symbol': symbol,
                'correlation': 'error',
                'error': str(e)
            }

    def get_market_sentiment(self,
                           symbol: Optional[str] = None,
                           days: int = 7) -> Dict[str, Any]:
        """
        获取市场情绪（基于新闻数量和价格变化）

        Args:
            symbol: 交易对符号（None则分析整体市场）
            days: 统计天数

        Returns:
            市场情绪分析
        """
        try:
            if symbol:
                # 分析单个币种
                correlation = self.analyze_news_price_correlation(symbol, days)

                # 基于关联类型判断情绪
                correlation_type = correlation.get('correlation_type', 'unclear')

                if correlation_type == 'positive_strong':
                    sentiment = 'bullish'
                    score = 0.8
                elif correlation_type == 'negative_strong':
                    sentiment = 'bearish'
                    score = 0.2
                else:
                    sentiment = 'neutral'
                    score = 0.5

                return {
                    'symbol': symbol,
                    'sentiment': sentiment,
                    'score': score,
                    'period_days': days,
                    'analysis': correlation
                }

            else:
                # 分析整体市场（需要获取多个主流币种）
                major_symbols = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP']
                sentiments = []

                for sym in major_symbols:
                    result = self.get_market_sentiment(sym, days)
                    if result.get('sentiment'):
                        sentiments.append(result['score'])

                # 计算平均情绪
                if sentiments:
                    avg_score = sum(sentiments) / len(sentiments)
                    if avg_score > 0.6:
                        overall_sentiment = 'bullish'
                    elif avg_score < 0.4:
                        overall_sentiment = 'bearish'
                    else:
                        overall_sentiment = 'neutral'
                else:
                    overall_sentiment = 'unknown'
                    avg_score = 0.5

                return {
                    'market': 'crypto',
                    'sentiment': overall_sentiment,
                    'score': avg_score,
                    'period_days': days,
                    'analyzed_symbols': major_symbols
                }

        except Exception as e:
            logger.error(f"市场情绪分析失败: {e}")
            return {
                'sentiment': 'error',
                'error': str(e)
            }

    def get_volume_analysis(self, symbol: str, days: int = 7) -> Dict[str, Any]:
        """
        获取成交量分析

        Args:
            symbol: 交易对符号
            days: 统计天数

        Returns:
            成交量分析结果
        """
        try:
            # TODO: 实际项目中应该调用外部API获取成交量数据
            logger.warning(f"使用模拟数据: {symbol} 成交量分析")

            return {
                'symbol': symbol,
                'period_days': days,
                'avg_volume': 0.0,
                'volume_trend': 'stable'
            }

        except Exception as e:
            logger.error(f"成交量分析失败: {e}")
            return {}

    def fetch_fear_greed_index(self) -> Dict[str, Any]:
        """
        获取Fear & Greed Index（恐惧与贪婪指数）

        Returns:
            指数信息字典
        """
        fallback = {
            "value": None,
            "classification": "数据不可用",
            "value_class": "neutral",
            "timestamp": None,
        }
        try:
            response = requests.get(FNG_API_ENDPOINT, timeout=5)
            response.raise_for_status()
            payload = response.json() or {}
            entry = (payload.get("data") or [fallback])[0]
            value = entry.get("value") or fallback["value"]
            classification_raw = (
                entry.get("value_classification")
                or entry.get("classification")
                or fallback["classification"]
            )
            classification_str = str(classification_raw).strip() or "未知"

            # 中文标签映射
            cn_map = {
                "extreme greed": "极度贪婪",
                "greed": "贪婪",
                "neutral": "中性",
                "fear": "恐惧",
                "extreme fear": "极度恐惧",
            }
            classification_cn = cn_map.get(classification_str.lower(), classification_str)
            class_slug = classification_str.lower().replace(' ', '-')
            allowed_classes = {"extreme-greed", "greed", "neutral", "fear", "extreme-fear"}

            if class_slug not in allowed_classes:
                class_slug = "neutral"

            timestamp = entry.get("timestamp")
            if timestamp:
                try:
                    dt = datetime.fromtimestamp(int(timestamp))
                    timestamp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    timestamp_str = None
            else:
                timestamp_str = None

            return {
                "value": value,
                "classification": classification_cn,
                "value_class": class_slug,
                "timestamp": timestamp_str,
            }
        except Exception as e:
            logger.warning(f"获取Fear & Greed Index失败: {e}")
            return fallback

    def fetch_crypto_market_board(self, limit: int = 20) -> Dict[str, Any]:
        """
        获取加密货币市场概览（24h涨跌榜）

        Args:
            limit: 返回币种数量

        Returns:
            市场数据字典
        """
        fallback = {
            "coins": [],
            "currency": "USD",
            "last_updated": None,
        }
        try:
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": limit,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h",
            }
            response = requests.get(COINGECKO_MARKET_ENDPOINT, params=params, timeout=8)
            response.raise_for_status()
            data = response.json() or []

            coins = []
            for entry in data:
                try:
                    price = entry.get("current_price")
                    pct = entry.get("price_change_percentage_24h")
                    change = entry.get("price_change_24h")
                    last_updated = entry.get("last_updated")

                    coins.append({
                        "id": entry.get("id"),
                        "symbol": (entry.get("symbol") or "").upper(),
                        "name": entry.get("name"),
                        "price": price,
                        "price_change_percentage_24h": pct,
                        "price_change_pct": pct,
                        "price_change_24h": change,
                        "market_cap": entry.get("market_cap"),
                        "volume_24h": entry.get("total_volume"),
                        "image": entry.get("image"),
                        "last_updated": last_updated,
                        "trend": "up" if (pct or 0) >= 0 else "down",
                        "news_count": 0,  # 待实现
                        "news_ratio": 0.0,  # 待实现
                    })
                except Exception as ex:
                    logger.warning(f"解析币种数据失败: {ex}")
                    continue

            raw_last_updated = coins[0].get("last_updated") if coins else None

            payload = {
                "coins": coins,
                "currency": "USD",
                "last_updated": raw_last_updated,
            }

            return payload

        except Exception as e:
            logger.warning(f"获取加密货币市场数据失败: {e}")
            return fallback

    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """
        检查缓存是否有效

        Args:
            timestamp: 缓存时间

        Returns:
            是否有效
        """
        return (datetime.now() - timestamp).total_seconds() < self._cache_ttl


# 便捷函数
def get_market_service(source: NewsSource = NewsSource.CRYPTO) -> MarketService:
    """
    获取市场服务实例

    Args:
        source: 新闻来源

    Returns:
        MarketService实例
    """
    return MarketService(source=source)
