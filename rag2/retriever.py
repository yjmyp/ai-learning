# -*- coding: utf-8 -*-
"""检索：向量召回 top-N → 可选重排 → 返回前 top_k"""
from config import DEFAULT_TOP_K, RERANK_TOP_K
from reranker import Reranker


class Retriever:
    def __init__(self, store, embedder, rerank_top_k=RERANK_TOP_K):
        self.store = store
        self.embedder = embedder
        self.rerank_top_k = rerank_top_k
        self.reranker = Reranker()

    def retrieve(self, question, top_k=DEFAULT_TOP_K, use_rerank=True):
        query_vec = self.embedder.encode([question])[0]
        n = max(top_k, self.rerank_top_k) if use_rerank else top_k
        res = self.store.query(query_vec, n_results=n)

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

        if use_rerank and len(hits) > 1:
            hits = self.reranker.rerank(question, hits)
        return hits[:top_k]
