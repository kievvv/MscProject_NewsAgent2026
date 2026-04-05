"""
摘要生成器
支持多种模型：mT5 (推荐用于中文)、BART (用于英文)、简单提取
"""
import logging
import re
from pathlib import Path
from typing import Optional, List

from config.settings import settings
from src.core.exceptions import AnalyzerException
from src.utils.model_loader import find_local_hf_model, huggingface_endpoint

logger = logging.getLogger(__name__)


class Summarizer:
    """
    新闻摘要生成器

    支持三种方法：
    1. mT5: 多语言T5模型（适合中文）
    2. BART: Facebook BART模型（适合英文）
    3. simple: 简单文本提取
    """

    def __init__(self,
                 model_name: Optional[str] = None,
                 model_type: str = 'auto',
                 min_length: int = 16,
                 max_length: int = 84):
        """
        初始化摘要生成器

        Args:
            model_name: 模型名称
            model_type: 模型类型 ('mt5', 'bart', 'simple', 'auto')
            min_length: 最小长度
            max_length: 最大长度
        """
        self.model_name = model_name
        self.model_type = model_type
        self.min_length = min_length
        self.max_length = max_length

        # 延迟加载模型
        self._tokenizer = None
        self._model = None
        self._model_loaded = False
        self._actual_model_type = None

    def _load_model(self) -> None:
        """延迟加载模型"""
        if self._model_loaded:
            return

        # 自动选择模型类型
        if self.model_type == 'auto':
            # 优先尝试 mT5（适合中文）
            if self._try_load_mt5():
                self._actual_model_type = 'mt5'
            elif self._try_load_bart():
                self._actual_model_type = 'bart'
            else:
                self._actual_model_type = 'simple'
                logger.warning("所有模型加载失败，将使用简单提取方法")

        elif self.model_type == 'mt5':
            if not self._try_load_mt5():
                self._actual_model_type = 'simple'
                logger.warning("mT5 模型加载失败，fallback 到简单提取")

        elif self.model_type == 'bart':
            if not self._try_load_bart():
                self._actual_model_type = 'simple'
                logger.warning("BART 模型加载失败，fallback 到简单提取")

        else:  # simple
            self._actual_model_type = 'simple'

        self._model_loaded = True
        logger.info(f"摘要生成器使用模型: {self._actual_model_type}")

    def _try_load_mt5(self) -> bool:
        """尝试加载 mT5 模型"""
        try:
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

            model_name = self.model_name or "csebuetnlp/mT5_multilingual_XLSum"
            logger.info(f"正在加载 mT5 模型: {model_name}...")
            if self._load_seq2seq_model(model_name, use_fast=False):
                logger.info("mT5 模型加载成功")
                return True

        except ImportError:
            logger.warning("transformers 未安装，无法使用 mT5 模型")
            return False
        except Exception as e:
            logger.warning(f"mT5 模型加载失败: {e}")
            return False

    def _try_load_bart(self) -> bool:
        """尝试加载 BART 模型"""
        try:
            from transformers import BartTokenizer, BartForConditionalGeneration

            model_name = self.model_name or settings.SUMMARY_MODEL
            logger.info(f"正在加载 BART 模型: {model_name}...")
            if self._load_seq2seq_model(model_name):
                logger.info("BART 模型加载成功")
                return True

        except ImportError:
            logger.warning("transformers 未安装，无法使用 BART 模型")
            return False
        except Exception as e:
            logger.warning(f"BART 模型加载失败: {e}")
            return False

    def _load_seq2seq_model(self, model_name: str, use_fast: bool = True) -> bool:
        """
        优先从本地缓存加载摘要模型，失败时再尝试官方端点。
        """
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

        local_model = find_local_hf_model(model_name)
        try:
            if local_model:
                logger.info(f"从本地缓存加载摘要模型: {local_model}")
                self._tokenizer = AutoTokenizer.from_pretrained(
                    str(local_model),
                    use_fast=use_fast,
                    local_files_only=True,
                )
                self._model = AutoModelForSeq2SeqLM.from_pretrained(
                    str(local_model),
                    local_files_only=True,
                )
                return True
        except Exception as e:
            logger.warning(f"本地摘要模型加载失败: {e}")

        if not settings.HF_ALLOW_REMOTE_DOWNLOADS:
            logger.warning("摘要模型本地缓存未命中，且已禁用远程下载")
            return False

        try:
            with huggingface_endpoint("https://huggingface.co"):
                self._tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=use_fast)
                self._model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            return True
        except Exception as e:
            logger.warning(f"远程摘要模型加载失败: {e}")
            return False

    def generate(self,
                text: str,
                min_length: Optional[int] = None,
                max_length: Optional[int] = None) -> str:
        """
        生成摘要

        Args:
            text: 原始文本
            min_length: 最小长度（可选）
            max_length: 最大长度（可选）

        Returns:
            摘要文本
        """
        if not text or not text.strip():
            return ""

        # 确保模型已加载
        self._load_model()

        min_len = min_length or self.min_length
        max_len = max_length or self.max_length

        # 根据模型类型生成摘要
        if self._actual_model_type == 'mt5':
            return self._generate_mt5(text, min_len, max_len)
        elif self._actual_model_type == 'bart':
            return self._generate_bart(text, min_len, max_len)
        else:  # simple
            return self._generate_simple(text, max_len)

    def _generate_mt5(self, text: str, min_length: int, max_length: int) -> str:
        """使用 mT5 生成摘要"""
        try:
            # 清理文本
            clean_text = re.sub(r"\s+", " ", re.sub(r"\n+", " ", text.strip()))

            # 编码
            inputs = self._tokenizer(
                clean_text,
                return_tensors="pt",
                padding="max_length",
                truncation=True,
                max_length=512,
            )

            # 生成
            summary_ids = self._model.generate(
                inputs["input_ids"],
                max_length=max_length,
                min_length=min_length,
                num_beams=4,
                no_repeat_ngram_size=2,
                early_stopping=True,
            )

            # 解码
            summary = self._tokenizer.decode(
                summary_ids[0],
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )

            return summary.strip()

        except Exception as e:
            logger.error(f"mT5 生成失败: {e}")
            return self._generate_simple(text, max_length)

    def _generate_bart(self, text: str, min_length: int, max_length: int) -> str:
        """使用 BART 生成摘要"""
        try:
            # 编码
            inputs = self._tokenizer(
                text,
                max_length=1024,
                truncation=True,
                return_tensors="pt"
            )

            # 生成
            summary_ids = self._model.generate(
                inputs["input_ids"],
                max_length=max_length,
                min_length=min_length,
                num_beams=4,
                early_stopping=True
            )

            # 解码
            summary = self._tokenizer.decode(
                summary_ids[0],
                skip_special_tokens=True
            )

            return summary.strip()

        except Exception as e:
            logger.error(f"BART 生成失败: {e}")
            return self._generate_simple(text, max_length)

    def _generate_simple(self, text: str, max_length: int) -> str:
        """
        简单摘要：提取文本前N个字符（在句子边界截断）

        Args:
            text: 原始文本
            max_length: 最大长度

        Returns:
            摘要文本
        """
        if len(text) <= max_length:
            return text.strip()

        # 尝试在句子边界截断
        summary = text[:max_length]

        # 查找最后一个句号/问号/感叹号
        for punct in ['。', '！', '？', '.', '!', '?']:
            last_punct = summary.rfind(punct)
            if last_punct > max_length * 0.5:  # 确保不会截断太多
                return summary[:last_punct + 1].strip()

        # 如果找不到合适的标点，直接截断并加省略号
        return summary.rstrip() + "..."

    def generate_batch(self,
                      texts: List[str],
                      min_length: Optional[int] = None,
                      max_length: Optional[int] = None) -> List[str]:
        """
        批量生成摘要

        Args:
            texts: 文本列表
            min_length: 最小长度
            max_length: 最大长度

        Returns:
            摘要列表
        """
        summaries = []
        for text in texts:
            try:
                summary = self.generate(text, min_length, max_length)
                summaries.append(summary)
            except Exception as e:
                logger.error(f"批量生成失败: {e}")
                summaries.append("")

        return summaries

    @property
    def is_model_available(self) -> bool:
        """检查模型是否可用"""
        self._load_model()
        return self._actual_model_type in ['mt5', 'bart']

    @property
    def current_model_type(self) -> str:
        """获取当前使用的模型类型"""
        self._load_model()
        return self._actual_model_type


# 全局单例
_summarizer: Optional[Summarizer] = None


def get_summarizer() -> Summarizer:
    """
    获取摘要生成器单例

    Returns:
        Summarizer实例
    """
    global _summarizer
    if _summarizer is None:
        _summarizer = Summarizer()
    return _summarizer
