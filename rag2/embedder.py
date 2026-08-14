# -*- coding: utf-8 -*-
"""向量化：BGE 中文小模型（本地已缓存，懒加载）"""
from functools import lru_cache


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    from config import EMBED_MODEL
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
