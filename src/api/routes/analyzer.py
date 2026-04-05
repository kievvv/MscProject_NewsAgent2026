"""
分析器路由
提供关键词分析和统计功能
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta

from src.services import get_search_service
from src.core.models import NewsSource
from src.data.repositories.news import NewsRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analyzer"])

# 频道映射
CHANNEL_MAP = {
    "1": ("-1001387109317", "@theblockbeats"),
    "2": ("-1001735732363", "@TechFlowDaily"),
    "3": ("-1002395608815", "@news6551"),
    "4": ("-1002117032512", "@MMSnews"),
}

DEFAULT_SOURCE = "crypto"
SOURCE_LABEL_MAP = {"crypto": "Web3 新闻", "hkstocks": "港股新闻"}


def normalize_source(source: Optional[str]) -> str:
    """标准化数据源"""
    if not source:
        return DEFAULT_SOURCE
    key = str(source).lower()
    return key if key in SOURCE_LABEL_MAP else DEFAULT_SOURCE


@router.get("/channels")
async def get_channels(source: str = DEFAULT_SOURCE):
    """获取可用频道列表"""
    source_key = normalize_source(source)

    if source_key == "crypto":
        channels = [
            {"id": k, "channel_id": v[0], "name": v[1]}
            for k, v in CHANNEL_MAP.items()
        ]
        return JSONResponse(content={
            'channels': channels,
            'supports_channels': True
        })
    else:
        return JSONResponse(content={
            'channels': [],
            'supports_channels': False
        })


@router.post("/analyze")
async def analyze_data(request: Request):
    """分析数据的主要接口"""
    try:
        data = await request.json()
        source_key = normalize_source(data.get('data_source'))
        channel_ids = data.get('channel_ids', []) or None
        time_range_str = data.get('time_range')

        logger.info(f"📊 开始分析 {SOURCE_LABEL_MAP.get(source_key, source_key)} 数据...")
        logger.info(f"   频道 ID: {channel_ids}")
        logger.info(f"   时间范围: {time_range_str}")

        # 确定时间范围
        end_time = datetime.now()
        if time_range_str:
            minutes = int(time_range_str.split(':')[0])
            start_time = end_time - timedelta(minutes=minutes)
        else:
            start_time = None

        # 获取数据
        source_enum = NewsSource.CRYPTO if source_key == "crypto" else NewsSource.HKSTOCKS
        news_repo = NewsRepository(source=source_enum)

        # 获取所有新闻
        all_news = news_repo.get_all()

        # 时间筛选
        if start_time:
            filtered_news = []
            for news in all_news:
                if news.date:
                    try:
                        news_date = datetime.fromisoformat(news.date.replace('Z', '+00:00').replace('T', ' ').split('+')[0])
                        if news_date >= start_time:
                            filtered_news.append(news)
                    except:
                        filtered_news.append(news)
            all_news = filtered_news

        # 频道筛选（仅Crypto）
        if source_key == "crypto" and channel_ids:
            all_news = [n for n in all_news if n.channel_id in channel_ids]

        total_rows = len(all_news)
        logger.info(f"✓ 总行数: {total_rows}")

        # 统计关键词
        from collections import Counter
        keyword_counter = Counter()
        keyword_occurrence = Counter()

        for news in all_news:
            if news.keywords:
                keywords = [k.strip() for k in news.keywords.split(',') if k.strip()]
                for kw in keywords:
                    keyword_counter[kw] += 1
                keyword_occurrence[kw] += 1

        logger.info(f"✓ 关键词种类: {len(keyword_counter)}")

        # 统计币种/行业
        currency_counter = Counter()
        currency_occurrence = Counter()

        for news in all_news:
            if source_key == "crypto":
                if news.currency:
                    currencies = [c.strip() for c in news.currency.split(',') if c.strip()]
                    for cur in currencies:
                        currency_counter[cur] += 1
                    for cur in currencies:
                        currency_occurrence[cur] += 1
            else:
                if news.industry:
                    industries = [i.strip() for i in news.industry.split(',') if i.strip()]
                    for ind in industries:
                        currency_counter[ind] += 1
                    for ind in industries:
                        currency_occurrence[ind] += 1

        logger.info(f"✓ 币种/行业种类: {len(currency_counter)}")

        # 构建统计结果
        keyword_stats = []
        for word, count in keyword_counter.most_common():
            occur_count = keyword_occurrence[word]
            ratio = (occur_count / total_rows * 100) if total_rows > 0 else 0
            keyword_stats.append({
                'word': word,
                'count': count,
                'occur_count': occur_count,
                'ratio': round(ratio, 2)
            })

        currency_stats = []
        for word, count in currency_counter.most_common():
            occur_count = currency_occurrence[word]
            ratio = (occur_count / total_rows * 100) if total_rows > 0 else 0
            currency_stats.append({
                'word': word,
                'count': count,
                'occur_count': occur_count,
                'ratio': round(ratio, 2)
            })

        # 相似度分析（简化版）
        similarity_results = []

        logger.info("✅ 分析完成")
        return JSONResponse(content={
            'success': True,
            'total_rows': total_rows,
            'keyword_stats': keyword_stats,
            'currency_stats': currency_stats,
            'similarity_results': similarity_results,
            'keyword_total': len(keyword_counter),
            'currency_total': len(currency_counter)
        })

    except Exception as e:
        logger.error(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={
            'success': False,
            'error': str(e)
        })


@router.post("/query-keyword")
async def query_keyword_similarity(request: Request):
    """查询关键词相似度"""
    try:
        data = await request.json()
        source_key = normalize_source(data.get('data_source'))
        keyword = data.get('keyword', '').strip()

        logger.info(f"🔍 查询请求: '{keyword}'")
        if not keyword:
            return JSONResponse(status_code=400, content={
                'success': False,
                'error': '请输入关键词'
            })

        # 简化实现：直接返回查询结果
        source_enum = NewsSource.CRYPTO if source_key == "crypto" else NewsSource.HKSTOCKS
        search_service = get_search_service(source=source_enum)

        # 搜索相关新闻
        news_list = search_service.search_by_keyword(keyword, exact=False, limit=10)

        return JSONResponse(content={
            'success': True,
            'exists': len(news_list) > 0,
            'direct_count': len(news_list),
            'similar_results': [],
            'news': [
                {
                    'id': news.id,
                    'text': news.text[:200],
                    'date': news.date,
                    'keywords': news.keywords
                }
                for news in news_list
            ]
        })

    except Exception as e:
        logger.error(f"❌ 查询失败: {e}")
        return JSONResponse(status_code=500, content={
            'success': False,
            'error': str(e)
        })
