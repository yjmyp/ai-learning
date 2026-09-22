# -*- coding: utf-8 -*-
"""向量化：BGE 中文小模型（本地已缓存，懒加载）"""
from functools import lru_cache


@lru_cache(maxsize=1)
def _model():
    # 顺序很重要：必须先导 config（它会打开 HF_HUB_OFFLINE 等离线开关），
    # 再导 sentence_transformers（它在自己的导入时刻读取这些开关）。
    # 顺序反了 → 离线开关失效 → 加载模型时去连 HuggingFace → 网络不通就卡死。
    from config import EMBED_MODEL
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL, device="cpu")


class Embedder:
    """统一入口：encode([...]) → [[float, ...], ...]（已归一化）"""

    def encode(self, texts):
        model = _model()
        vectors = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32,
        )
        return [v.tolist() for v in vectors]
