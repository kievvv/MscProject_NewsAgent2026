"""
统一的模型加载器
避免重复加载模型，提升性能
"""
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional

from config.settings import settings
logger = logging.getLogger(__name__)

# 全局模型缓存
_spacy_model_cache = {}
_keybert_model = None


def _normalize_model_variants(model_name: str) -> List[str]:
    """生成可能的 HF repo id 变体。"""
    candidates = [model_name]
    if "/" not in model_name:
        candidates.append(f"sentence-transformers/{model_name}")
    return list(dict.fromkeys(candidates))


def find_local_hf_model(model_name: str) -> Optional[Path]:
    """
    查找本地 Hugging Face 缓存中的模型目录。

    优先读取本机已有快照，避免因为镜像或外网问题阻塞加载。
    """
    raw_path = Path(model_name).expanduser()
    if raw_path.exists():
        return raw_path

    hub_root = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    for repo_id in _normalize_model_variants(model_name):
        repo_dir = hub_root / f"models--{repo_id.replace('/', '--')}"
        refs_main = repo_dir / "refs" / "main"
        snapshots_dir = repo_dir / "snapshots"

        if refs_main.exists():
            revision = refs_main.read_text(encoding="utf-8").strip()
            candidate = snapshots_dir / revision
            if candidate.exists():
                return candidate

        if snapshots_dir.exists():
            snapshots = [path for path in snapshots_dir.iterdir() if path.is_dir()]
            if snapshots:
                snapshots.sort(key=lambda path: path.stat().st_mtime, reverse=True)
                return snapshots[0]

    return None


@contextmanager
def huggingface_endpoint(endpoint: Optional[str] = None) -> Iterator[None]:
    """
    临时切换 HF_ENDPOINT。

    当项目里配置了失效镜像时，这里允许在单次模型加载时显式回退到官方端点。
    """
    previous = os.environ.get("HF_ENDPOINT")
    try:
        if endpoint:
            os.environ["HF_ENDPOINT"] = endpoint
        else:
            os.environ.pop("HF_ENDPOINT", None)
        yield
    finally:
        if previous is None:
            os.environ.pop("HF_ENDPOINT", None)
        else:
            os.environ["HF_ENDPOINT"] = previous


def get_spacy_model(model_name: str = "zh_core_web_sm"):
    """
    获取 spaCy 模型（单例模式）

    Args:
        model_name: 首选模型名称，如果加载失败会尝试其他模型

    Returns:
        加载好的 spaCy 模型

    Raises:
        RuntimeError: 如果没有找到任何可用的模型
    """
    import spacy

    if model_name in _spacy_model_cache:
        logger.debug(f"使用缓存的 spaCy 模型: {model_name}")
        return _spacy_model_cache[model_name]

    # 优先级列表
    model_priority = [
        model_name,
        "zh_core_web_lg",
        "zh_core_web_trf",
        "zh_core_web_md",
        "zh_core_web_sm"
    ]

    # 去重
    model_priority = list(dict.fromkeys(model_priority))

    for model in model_priority:
        try:
            logger.info(f"正在加载 spaCy 模型: {model}...")
            nlp = spacy.load(model)
            _spacy_model_cache[model] = nlp
            logger.info(f"成功加载 spaCy 模型: {model}")
            return nlp
        except OSError:
            logger.debug(f"模型 {model} 未找到，尝试下一个...")
            continue
        except Exception as e:
            logger.warning(f"加载模型 {model} 失败: {e}")
            continue

    raise RuntimeError(
        f"未找到可用的 spaCy 中文模型。\n"
        f"请运行以下命令之一安装：\n"
        f"  python -m spacy download zh_core_web_lg\n"
        f"  python -m spacy download zh_core_web_md\n"
        f"  python -m spacy download zh_core_web_sm"
    )


def get_keybert_model(model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
    """
    获取 KeyBERT 模型（单例模式）

    Args:
        model_name: 模型名称

    Returns:
        加载好的 KeyBERT 模型，如果加载失败返回 None
    """
    global _keybert_model

    if _keybert_model is not None:
        logger.debug("使用缓存的 KeyBERT 模型")
        return _keybert_model

    try:
        from keybert import KeyBERT
        from sentence_transformers import SentenceTransformer

        local_model_path = find_local_hf_model(model_name)
        if local_model_path:
            logger.info(f"正在从本地缓存加载 KeyBERT 模型: {local_model_path}")
            sentence_model = SentenceTransformer(str(local_model_path))
            _keybert_model = KeyBERT(model=sentence_model)
            logger.info(f"成功从本地缓存加载 KeyBERT 模型: {local_model_path}")
            return _keybert_model

        if not settings.HF_ALLOW_REMOTE_DOWNLOADS:
            logger.warning("KeyBERT 本地缓存未命中，且已禁用远程下载")
            return None

        logger.info(f"本地未命中 KeyBERT 模型缓存，尝试远程加载: {model_name}")
        for candidate in _normalize_model_variants(model_name):
            try:
                with huggingface_endpoint("https://huggingface.co"):
                    sentence_model = SentenceTransformer(candidate)
                _keybert_model = KeyBERT(model=sentence_model)
                logger.info(f"成功远程加载 KeyBERT 模型: {candidate}")
                return _keybert_model
            except Exception as exc:
                logger.warning(f"远程加载 KeyBERT 模型失败: {candidate}, error={exc}")

        logger.error(
            "KeyBERT 模型不可用：本地缓存未命中且远程加载失败。"
            " 可在联网环境中预下载 sentence-transformers 模型后重试。"
        )
        return None
    except ImportError:
        logger.error("KeyBERT 未安装，请运行: pip install keybert sentence-transformers")
        return None
    except Exception as e:
        logger.error(f"KeyBERT 模型加载失败: {e}")
        return None


def clear_model_cache():
    """清空模型缓存（用于测试或节省内存）"""
    global _spacy_model_cache, _keybert_model
    _spacy_model_cache.clear()
    _keybert_model = None
    logger.info("模型缓存已清空")
