"""
相似度分析器
基于 spaCy 计算关键词和币种的相似度
"""
import logging
import re
import itertools
from collections import Counter
from typing import List, Tuple, Optional, Dict, Any

from src.utils.model_loader import get_spacy_model
from src.data.repositories.news import NewsRepository
from src.core.models import NewsSource
from src.core.exceptions import AnalyzerException
from config.settings import settings

logger = logging.getLogger(__name__)

# 分隔符正则
SPLIT_RE = re.compile(r"[,，]+")


class SimilarityAnalyzer:
    """
    相似度分析器

    功能：
    1. 统计关键词/币种出现频率
    2. 计算关键词相似度对
    3. 查询相似词推荐
    """

    def __init__(self,
                 news_repo: Optional[NewsRepository] = None,
                 min_count: int = 5,
                 top_n: int = 100,
                 spacy_model_name: Optional[str] = None):
        """
        初始化相似度分析器

        Args:
            news_repo: 新闻仓储
            min_count: 最小词频阈值
            top_n: 输出前 N 对结果
            spacy_model_name: spaCy 模型名称
        """
        self.news_repo = news_repo
        self.min_count = min_count
        self.top_n = top_n
        self.spacy_model_name = spacy_model_name or settings.SPACY_SIMILARITY_MODEL

        # 延迟加载 spaCy 模型
        self._nlp = None

    @property
    def nlp(self):
        """延迟加载 spaCy 模型"""
        if self._nlp is None:
            try:
                self._nlp = get_spacy_model(self.spacy_model_name)
                logger.info(f"spaCy 模型已加载: {self.spacy_model_name}")
            except Exception as e:
                logger.error(f"spaCy 模型加载失败: {e}")
                raise AnalyzerException(f"Failed to load spaCy model: {e}")
        return self._nlp

    def split_items(self, item_string: str, case_insensitive: bool = True) -> List[str]:
        """
        分隔字符串中的项目

        Args:
            item_string: 逗号分隔的字符串
            case_insensitive: 是否转换为小写

        Returns:
            项目列表
        """
        if not item_string:
            return []

        parts = [p.strip() for p in SPLIT_RE.split(item_string) if p and p.strip()]

        if case_insensitive:
            parts = [p.lower() for p in parts]

        return parts

    def count_items(self,
                   items_list: List[str],
                   case_insensitive: bool = True) -> Tuple[Counter, Counter]:
        """
        统计项目出现次数

        Args:
            items_list: 项目字符串列表（逗号分隔）
            case_insensitive: 是否不区分大小写

        Returns:
            (item_counter, occurrence_counter) 元组
            - item_counter: 总出现次数
            - occurrence_counter: 出现的文档数
        """
        item_counter = Counter()
        occurrence_counter = Counter()

        for item_str in items_list:
            if not item_str:
                continue

            parts = self.split_items(item_str, case_insensitive)
            item_counter.update(parts)
            occurrence_counter.update(set(parts))

        return item_counter, occurrence_counter

    def get_keyword_statistics(self,
                              source: NewsSource = NewsSource.CRYPTO,
                              channel_ids: Optional[List[str]] = None,
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取关键词统计

        Args:
            source: 新闻来源
            channel_ids: 频道ID列表（仅Crypto）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            统计信息字典
        """
        if not self.news_repo:
            repo = NewsRepository(source=source)
        else:
            repo = self.news_repo

        # 获取新闻列表
        if start_date and end_date:
            news_list = repo.get_by_date_range(start_date, end_date)
        elif channel_ids and source == NewsSource.CRYPTO:
            news_list = []
            for channel_id in channel_ids:
                news_list.extend(repo.get_by_channel(channel_id))
        else:
            news_list = repo.get_all(limit=10000)  # 限制数量

        # 提取关键词字符串列表
        keywords_list = [news.keywords or '' for news in news_list]
        currency_list = []

        if source == NewsSource.CRYPTO:
            currency_list = [news.currency or '' for news in news_list]
        else:  # HKSTOCKS
            currency_list = [news.industry or '' for news in news_list]

        # 统计
        keyword_counter, keyword_occurrence = self.count_items(keywords_list)
        currency_counter, currency_occurrence = self.count_items(currency_list)

        return {
            'total_news': len(news_list),
            'keyword_counter': keyword_counter,
            'keyword_occurrence': keyword_occurrence,
            'currency_counter': currency_counter,
            'currency_occurrence': currency_occurrence,
        }

    def calculate_similarity(self, word_counter: Counter) -> List[Tuple[str, int, str, int, float]]:
        """
        计算词语之间的相似度

        Args:
            word_counter: 词语计数器

        Returns:
            相似度结果列表 [(word1, count1, word2, count2, similarity), ...]
        """
        # 过滤低频词
        terms = [t for t, c in word_counter.items() if c >= self.min_count]

        if len(terms) < 2:
            logger.warning(f"词语数量不足（{len(terms)} < 2），无法计算相似度")
            return []

        # 构建词向量
        term_docs = {}
        skipped = []

        for term in terms:
            try:
                doc = self.nlp(term)
                if hasattr(doc, "vector_norm") and doc.vector_norm > 0:
                    term_docs[term] = doc
                else:
                    skipped.append(term)
            except Exception as e:
                logger.debug(f"跳过词 '{term}': {e}")
                skipped.append(term)

        if skipped:
            logger.debug(f"跳过了 {len(skipped)} 个词（无有效词向量）")

        if len(term_docs) < 2:
            logger.warning("有效词语数量不足（< 2），无法计算相似度")
            return []

        # 计算所有词对的相似度
        pairs = []
        keys = list(term_docs.keys())

        for word1, word2 in itertools.combinations(keys, 2):
            try:
                sim = term_docs[word1].similarity(term_docs[word2])
                pairs.append((
                    word1,
                    word_counter[word1],
                    word2,
                    word_counter[word2],
                    float(sim)
                ))
            except Exception as e:
                logger.debug(f"计算 '{word1}' 和 '{word2}' 的相似度失败: {e}")
                continue

        # 按相似度降序排序
        pairs.sort(key=lambda x: x[4], reverse=True)

        return pairs[:self.top_n]

    def find_similar_words(self,
                          input_word: str,
                          word_counter: Counter,
                          top_n: int = 10) -> Tuple[bool, List[Tuple[str, int, float]]]:
        """
        查找与输入词相似的词

        Args:
            input_word: 输入的词
            word_counter: 词语计数器
            top_n: 返回前 N 个相似词

        Returns:
            (exists, similar_words) 元组
            - exists: 词是否存在于数据集中
            - similar_words: [(word, count, similarity), ...] 列表
        """
        input_norm = input_word.lower().strip()

        # 判断是否存在
        exists = input_norm in (k.lower() for k in word_counter.keys())

        # 过滤高频词
        high_freq_terms = [t for t, c in word_counter.items() if c >= self.min_count]

        if not high_freq_terms:
            logger.warning("没有高频词，无法计算相似度")
            return exists, []

        # 构建词向量
        term_docs = {}
        for term in high_freq_terms:
            try:
                doc = self.nlp(term)
                if hasattr(doc, "vector_norm") and doc.vector_norm > 0:
                    term_docs[term] = doc
            except Exception as e:
                logger.debug(f"跳过词 '{term}': {e}")
                continue

        # 计算输入词向量
        try:
            input_doc = self.nlp(input_norm)
            if not (hasattr(input_doc, "vector_norm") and input_doc.vector_norm > 0):
                logger.warning(f"输入词 '{input_word}' 没有有效的词向量")
                return exists, []
        except Exception as e:
            logger.error(f"处理输入词失败: {e}")
            return exists, []

        # 计算与所有词的相似度
        similarities = []
        for term, doc in term_docs.items():
            try:
                sim = input_doc.similarity(doc)
                similarities.append((term, word_counter[term], float(sim)))
            except Exception as e:
                logger.debug(f"计算相似度失败: {e}")
                continue

        # 排序并返回 top N
        similarities.sort(key=lambda x: x[2], reverse=True)
        top_similar = similarities[:top_n]

        return exists, top_similar

    def analyze_keywords(self,
                        source: NewsSource = NewsSource.CRYPTO,
                        channel_ids: Optional[List[str]] = None,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        综合分析关键词

        Args:
            source: 新闻来源
            channel_ids: 频道ID列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            分析结果字典
        """
        # 获取统计数据
        stats = self.get_keyword_statistics(source, channel_ids, start_date, end_date)

        # 计算关键词相似度
        keyword_similarity = self.calculate_similarity(stats['keyword_counter'])

        # 计算币种/行业相似度
        currency_similarity = self.calculate_similarity(stats['currency_counter'])

        # 构建结果
        result = {
            'total_news': stats['total_news'],
            'keyword_stats': {
                'total_unique': len(stats['keyword_counter']),
                'total_occurrences': sum(stats['keyword_counter'].values()),
                'top_keywords': stats['keyword_counter'].most_common(20),
                'similarity_pairs': keyword_similarity[:50],
            },
            'currency_stats': {
                'total_unique': len(stats['currency_counter']),
                'total_occurrences': sum(stats['currency_counter'].values()),
                'top_currencies': stats['currency_counter'].most_common(20),
                'similarity_pairs': currency_similarity[:50],
            }
        }

        return result


# 全局单例
_similarity_analyzer: Optional[SimilarityAnalyzer] = None


def get_similarity_analyzer() -> SimilarityAnalyzer:
    """
    获取相似度分析器单例

    Returns:
        SimilarityAnalyzer实例
    """
    global _similarity_analyzer
    if _similarity_analyzer is None:
        _similarity_analyzer = SimilarityAnalyzer()
    return _similarity_analyzer
