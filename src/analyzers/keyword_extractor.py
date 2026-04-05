"""
关键词提取器
基于 KeyBERT 和 spaCy 提供关键词提取和实体识别功能
"""
import logging
import re
import json
from collections import Counter
from pathlib import Path
from typing import List, Tuple, Set, Optional, Dict, Any

import jieba
from sklearn.feature_extraction.text import CountVectorizer

from config.settings import settings
from src.utils.model_loader import get_spacy_model, get_keybert_model
from src.core.models import NewsSource
from src.core.exceptions import AnalyzerException

logger = logging.getLogger(__name__)

# 分隔关键词的正则（英文/中文逗号）
SPLIT_RE = re.compile(r"[,，]+")


class KeywordExtractor:
    """
    关键词提取器

    功能：
    1. 基于 KeyBERT 提取关键词
    2. 基于 spaCy NER 识别实体
    3. 识别币种（Crypto新闻）
    4. 识别行业（港股新闻）
    """

    def __init__(self,
                 model_name: Optional[str] = None,
                 stopwords_path: Optional[Path] = None,
                 coin_dict_path: Optional[Path] = None):
        """
        初始化关键词提取器

        Args:
            model_name: KeyBERT模型名称
            stopwords_path: 停用词文件路径
            coin_dict_path: 币种词典路径
        """
        self.model_name = model_name or settings.KEYBERT_MODEL

        # 加载停用词
        self.stopwords: Set[str] = set()
        self._stopwords_path = stopwords_path or self._find_stopwords_file()

        # 加载币种词典
        self._coin_dict_path = coin_dict_path or self._find_coin_dict_file()
        self.coin_dict: Dict[str, List[str]] = self._load_coin_dict()

        # 加载模型（延迟加载，按需初始化）
        self._keybert_model = None
        self._spacy_model = None
        self._matcher = None

    def _find_stopwords_file(self) -> Path:
        """查找停用词文件"""
        # 尝试多个可能的位置
        candidates = [
            settings.PROJECT_ROOT / "src" / "analyzers" / "stopwords.txt",
            settings.PROJECT_ROOT / "src" / "crypto_analysis" / "stopwords.txt",
            settings.PROJECT_ROOT / "src" / "crawler" / "crpyto_news" / "stopwords.txt",
        ]

        for candidate in candidates:
            if candidate.exists():
                logger.info(f"找到停用词文件: {candidate}")
                return candidate

        logger.warning("未找到停用词文件，将使用空停用词列表")
        return candidates[0]  # 返回默认路径

    def _find_coin_dict_file(self) -> Path:
        """查找币种词典文件"""
        candidates = [
            settings.PROJECT_ROOT / "src" / "analyzers" / "coin_dict.json",
            settings.PROJECT_ROOT / "src" / "crypto_analysis" / "coin_dict.json",
            settings.PROJECT_ROOT / "src" / "crawler" / "crpyto_news" / "coin_dict.json",
        ]

        for candidate in candidates:
            if candidate.exists():
                logger.info(f"找到币种词典: {candidate}")
                return candidate

        logger.warning("未找到币种词典文件")
        return candidates[0]

    def _load_stopwords(self) -> None:
        """加载停用词"""
        if self.stopwords:
            return

        try:
            if self._stopwords_path.exists():
                with open(self._stopwords_path, 'r', encoding='utf-8') as f:
                    self.stopwords = {line.strip() for line in f if line.strip()}
                logger.info(f"加载了 {len(self.stopwords)} 个停用词")
        except Exception as e:
            logger.warning(f"停用词加载失败: {e}")
            self.stopwords = set()

    def _load_coin_dict(self) -> Dict[str, List[str]]:
        """加载币种词典"""
        try:
            if self._coin_dict_path.exists():
                with open(self._coin_dict_path, 'r', encoding='utf-8') as f:
                    coin_dict = json.load(f)
                    logger.info(f"加载了 {len(coin_dict)} 个币种")
                    return coin_dict
        except Exception as e:
            logger.warning(f"币种词典加载失败: {e}")

        return {}

    @property
    def keybert_model(self):
        """延迟加载 KeyBERT 模型"""
        if self._keybert_model is None:
            self._keybert_model = get_keybert_model(self.model_name)
        return self._keybert_model

    @property
    def spacy_model(self):
        """延迟加载 spaCy 模型"""
        if self._spacy_model is None:
            try:
                self._spacy_model = get_spacy_model(settings.SPACY_MODEL)
            except RuntimeError as e:
                logger.error(f"spaCy 模型加载失败: {e}")
                self._spacy_model = None
        return self._spacy_model

    @property
    def matcher(self):
        """延迟构建币种匹配器"""
        if self._matcher is None and self.spacy_model and self.coin_dict:
            self._matcher = self._build_matcher()
        return self._matcher

    def _build_matcher(self):
        """构建币种匹配器（英文不区分大小写）"""
        from spacy.matcher import PhraseMatcher

        patterns = []
        for synonyms in self.coin_dict.values():
            for name in synonyms:
                patterns.append(self.spacy_model.make_doc(name.lower()))

        matcher = PhraseMatcher(self.spacy_model.vocab, attr="LOWER")
        matcher.add("COIN", patterns)
        logger.info(f"构建了包含 {len(patterns)} 个模式的币种匹配器")
        return matcher

    def is_valid_keyword(self, word: str) -> bool:
        """
        判断是否是有效的关键词

        Args:
            word: 候选关键词

        Returns:
            是否有效
        """
        if not word:
            return False

        word = word.strip()

        # 单个中文字符
        if re.fullmatch(r'[\u4e00-\u9fff]', word):
            return False

        # 单个英文字母
        if re.fullmatch(r'[A-Za-z]', word):
            return False

        # 纯数字（除了合理的年份）
        if re.fullmatch(r'\d+', word):
            try:
                num = int(word)
                if not (1950 <= num <= 2050):
                    return False
            except ValueError:
                return False

        # 只允许中英文数字
        allowed_pattern = re.compile(r'^[A-Za-z0-9\u4e00-\u9fff]+$')
        if not allowed_pattern.match(word):
            return False

        return True

    def tokenize_and_filter(self, text: str) -> List[str]:
        """
        分词并过滤

        Args:
            text: 输入文本

        Returns:
            分词结果
        """
        self._load_stopwords()

        # 使用 jieba 分词
        tokens = jieba.lcut(text)

        # 过滤停用词
        if self.stopwords:
            tokens = [tok for tok in tokens if tok not in self.stopwords]

        # 过滤无效关键词
        filtered_tokens = [tok.strip() for tok in tokens if self.is_valid_keyword(tok)]

        return filtered_tokens

    def extract_keywords(self,
                        text: str,
                        top_n: Optional[int] = None,
                        diversity: float = 0.3) -> List[Tuple[str, float]]:
        """
        提取关键词（基于 KeyBERT）

        Args:
            text: 输入文本
            top_n: 返回关键词数量
            diversity: 多样性参数（0-1）

        Returns:
            [(关键词, 权重), ...]

        Raises:
            AnalyzerException: 提取失败
        """
        if not text or not text.strip():
            return []

        top_n = top_n or settings.TOP_N_KEYWORDS

        if not self.keybert_model:
            logger.warning("KeyBERT 模型不可用，回退到本地词频关键词提取")
            return self._extract_keywords_fallback(text, top_n=top_n)

        try:
            # 自定义分词器
            vectorizer = CountVectorizer(
                tokenizer=self.tokenize_and_filter,
                token_pattern=None  # 避免警告
            )

            # 提取关键词
            keywords = self.keybert_model.extract_keywords(
                text,
                vectorizer=vectorizer,
                keyphrase_ngram_range=(1, 3),
                top_n=top_n,
                diversity=diversity
            )

            return keywords

        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return self._extract_keywords_fallback(text, top_n=top_n)

    def _extract_keywords_fallback(self, text: str, top_n: int) -> List[Tuple[str, float]]:
        """
        当 KeyBERT 不可用时，使用本地分词和词频作为稳定回退。
        """
        tokens = self.tokenize_and_filter(text)
        if not tokens:
            return []

        counter = Counter(tokens)
        total = sum(counter.values()) or 1
        return [
            (word, count / total)
            for word, count in counter.most_common(top_n)
        ]

    def extract_entities(self, text: str) -> List[str]:
        """
        提取命名实体（基于 spaCy NER）

        Args:
            text: 输入文本

        Returns:
            实体列表
        """
        if not self.spacy_model:
            logger.warning("spaCy 模型不可用，跳过实体提取")
            return []

        self._load_stopwords()

        try:
            doc = self.spacy_model(text)
            entities = set()

            for token in doc:
                # 仅保留特定词性
                if token.pos_ in {"PROPN", "NOUN", "VERB", "ORG", "GPE", "LOC"}:
                    token_text = token.text.strip()
                    if (token_text not in self.stopwords and
                        len(token_text) > 1 and
                        self.is_valid_keyword(token_text)):
                        entities.add(token_text)

            logger.debug(f"识别到 {len(entities)} 个实体")
            return list(entities)

        except Exception as e:
            logger.error(f"实体提取失败: {e}")
            return []

    def identify_currency(self, text: str) -> List[str]:
        """
        识别币种（仅适用于 Crypto 新闻）

        Args:
            text: 输入文本

        Returns:
            币种ID列表
        """
        if not self.matcher or not self.spacy_model:
            logger.debug("币种匹配器不可用")
            return []

        try:
            doc = self.spacy_model(text)
            matches = self.matcher(doc)

            mentioned_coins = set()
            for _, start, end in matches:
                span_text = doc[start:end].text

                # 查找对应的币种ID
                for coin_id, synonyms in self.coin_dict.items():
                    if span_text.lower() in [s.lower() for s in synonyms]:
                        mentioned_coins.add(coin_id)
                        break

            return list(mentioned_coins)

        except Exception as e:
            logger.error(f"币种识别失败: {e}")
            return []

    def extract_all(self,
                   text: str,
                   source: NewsSource = NewsSource.CRYPTO,
                   top_n: Optional[int] = None) -> Dict[str, Any]:
        """
        综合提取（关键词 + 实体 + 币种/行业）

        Args:
            text: 输入文本
            source: 新闻来源
            top_n: 关键词数量

        Returns:
            {
                'keywords': [(word, weight), ...],
                'entities': [entity, ...],
                'currency': [coin_id, ...],  # Crypto
                'keyword_string': 'kw1,kw2,kw3',
                'currency_string': 'BTC,ETH'
            }
        """
        result = {
            'keywords': [],
            'entities': [],
            'currency': [],
            'keyword_string': '',
            'currency_string': '',
        }

        # 提取关键词
        keywords = self.extract_keywords(text, top_n=top_n)
        result['keywords'] = keywords

        # 提取实体
        entities = self.extract_entities(text)
        result['entities'] = entities

        # 合并关键词和实体
        all_keywords = set([kw for kw, _ in keywords])
        all_keywords.update(entities)
        result['keyword_string'] = ','.join(all_keywords)

        # 识别币种（仅 Crypto）
        if source == NewsSource.CRYPTO:
            currency = self.identify_currency(text)
            result['currency'] = currency
            result['currency_string'] = ','.join(currency)

        return result

    def batch_extract(self,
                     texts: List[str],
                     source: NewsSource = NewsSource.CRYPTO) -> List[Dict[str, Any]]:
        """
        批量提取关键词

        Args:
            texts: 文本列表
            source: 新闻来源

        Returns:
            提取结果列表
        """
        results = []
        for text in texts:
            try:
                result = self.extract_all(text, source)
                results.append(result)
            except Exception as e:
                logger.error(f"批量提取失败: {e}")
                results.append({
                    'keywords': [],
                    'entities': [],
                    'currency': [],
                    'keyword_string': '',
                    'currency_string': '',
                })

        return results


# 全局单例
_keyword_extractor: Optional[KeywordExtractor] = None


def get_keyword_extractor() -> KeywordExtractor:
    """
    获取关键词提取器单例

    Returns:
        KeywordExtractor实例
    """
    global _keyword_extractor
    if _keyword_extractor is None:
        _keyword_extractor = KeywordExtractor()
    return _keyword_extractor
