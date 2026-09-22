# -*- coding: utf-8 -*-
"""检索：向量召回 →（可选 BM25 混合）→ 可选重排 → 返回前 top_k"""
from config import BM25_WEIGHT, DEFAULT_TOP_K, HYBRID_TOPK, RERANK_TOP_K
from bm25 import BM25
from reranker import Reranker


class Retriever:
    def __init__(self, store, embedder, rerank_top_k=RERANK_TOP_K):
        self.store = store
        self.embedder = embedder
        self.rerank_top_k = rerank_top_k
        self.reranker = Reranker()
        self.bm25 = None
        self.bm25_ids = None
        self.bm25_texts = None
        self.bm25_metas = None

    def _ensure_bm25(self):
        """懒加载 BM25 索引（首次使用时构建一次）。"""
        if self.bm25 is None:
            data = self.store.get_all()
            self.bm25_ids = data["ids"]
            self.bm25_texts = data["documents"]
            self.bm25_metas = data["metadatas"]
            self.bm25 = BM25(self.bm25_texts)
        return self.bm25

    def retrieve(self, question, top_k=DEFAULT_TOP_K, use_rerank=True, use_bm25=True):
        query_vec = self.embedder.encode([question])[0]
        n_vec = max(top_k, HYBRID_TOPK) if use_bm25 else max(top_k, self.rerank_top_k) if use_rerank else top_k
        res = self.store.query(query_vec, n_results=n_vec)

        hits = []
        ids = res["ids"][0]
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        dists = res["distances"][0]
        for i in range(len(ids)):
            hits.append({
                "id": ids[i],
                "text": docs[i],
                "source": (metas[i] or {}).get("source", ""),
                "vector_score": round(1 - dists[i], 4),  # 余弦相似度
            })

        if use_bm25:
            hits = self._hybrid(question, hits)

        if use_rerank and len(hits) > 1:
            hits = self.reranker.rerank(question, hits)
        return hits[:top_k]

    def _hybrid(self, question, vec_hits):
        """向量与 BM25 双路召回 → 各自归一化 → 加权融合。"""
        bm25 = self._ensure_bm25()
        cand = {}
        for h in vec_hits:
            cand[h["id"]] = {
                "vec": h["vector_score"], "bm25": 0.0,
                "text": h["text"], "source": h["source"],
            }
        for idx, score in bm25.search(question, HYBRID_TOPK):
            cid = self.bm25_ids[idx]
            if cid in cand:
                cand[cid]["bm25"] = score
            else:
                meta = self.bm25_metas[idx] or {}
                cand[cid] = {
                    "vec": 0.0, "bm25": score,
                    "text": self.bm25_texts[idx],
                    "source": meta.get("source", ""),
                }

        ids_list = list(cand.keys())
        vec_vals = [cand[i]["vec"] for i in ids_list]
        bm_vals = [cand[i]["bm25"] for i in ids_list]
        vec_norm = self._minmax(vec_vals)
        bm_norm = self._minmax(bm_vals)

        fused = []
        for pos, cid in enumerate(ids_list):
            c = cand[cid]
            fused.append({
                "id": cid,
                "text": c["text"],
                "source": c["source"],
                "vector_score": round(c["vec"], 4),
                "bm25_score": round(c["bm25"], 4),
                "hybrid_score": round(
                    (1 - BM25_WEIGHT) * vec_norm[pos] + BM25_WEIGHT * bm_norm[pos], 4
                ),
            })
        fused.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return fused

    @staticmethod
    def _minmax(vals):
        """最小-最大归一化到 [0,1]；全相等时给 0.5 避免除零。"""
        lo, hi = min(vals), max(vals)
        if hi - lo < 1e-9:
            return [0.5] * len(vals)
        return [(v - lo) / (hi - lo) for v in vals]
