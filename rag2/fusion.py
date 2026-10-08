# -*- coding: utf-8 -*-
"""多路召回融合：RRF（Reciprocal Rank Fusion）

为什么不用"加权求和"（v2 的做法）：
  向量分是余弦相似度（0~1），BM25 分是**没有上界的**实数（几十到几百都可能）。
  直接加权求和，等于让 BM25 的分数量纲压过向量分——权重 w=0.3 只是个错觉。
  RRF 只看"排第几"，天然免疫量纲差异，是工业界做混合检索的默认做法：

      score(d) = Σ 1 / (k + rank_i(d))        k 通常取 60

参考：Cormack et al. 2009 (RRF)；Elasticsearch / Vespa 的混合检索都用它。
"""


def rrf_fuse(ranked_lists, k=60, weights=None):
    """把多路召回结果融合成一个有序列表。

    ranked_lists: [[id, id, ...], ...] 每路已按相关性降序排好（只用到顺序）
    weights:      每路的权重（可选），例如 [1.0, 0.7] 表示第二路弱一点
    返回: [(id, fused_score), ...] 按分数降序
    """
    scores = {}
    weights = weights or [1.0] * len(ranked_lists)
    for li, ids in enumerate(ranked_lists):
        w = weights[li] if li < len(weights) else 1.0
        for rank, _id in enumerate(ids, start=1):
            scores[_id] = scores.get(_id, 0.0) + w / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])


def normalize(scores):
    """把一组分数线性归一到 0~1（只在需要展示/比较时用，融合本身不需要）。"""
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-9:
        return [1.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]
