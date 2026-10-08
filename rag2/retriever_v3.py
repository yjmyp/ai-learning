# -*- coding: utf-8 -*-
"""检索 v3：四档模式 + RRF 融合 + 多查询改写 + 重排 + 拒答阈值

相对 v2 的四点改动（每条都能在面试里讲）：
  1. 融合方式：加权求和 → **RRF**（免疫 BM25 与余弦的量纲差异，见 fusion.py）
  2. 查询侧：单条查询 → **multi-query / HyDE**（查询改写，见 query_rewrite.py）
  3. 重排：TF-IDF 字符相似 → **多特征重排**（向量 + BM25 + 词面覆盖 + 短语命中）；
     本地有 bge-reranker 时优先走 cross-encoder，有 key 时可开 LLM listwise
  4. 可信：检索分低于阈值 → **直接拒答**，不把不相关内容硬塞给模型

四种模式（mode 参数），方便做消融实验：
  vector         纯向量 top-k
  hybrid         向量 + BM25 → RRF
  hybrid_rerank  hybrid + 重排（默认档）
  full           hybrid_rerank + 多查询改写（v3 新增）
"""
import time

from bm25 import BM25
from config import DEFAULT_TOP_K, HYBRID_TOPK, RERANK_TOP_K
from fusion import rrf_fuse
from query_rewrite import hyde, multi_query
from rerank_v3 import cross_encoder_rerank, feature_rerank, llm_rerank

MODE_VECTOR = "vector"
MODE_HYBRID = "hybrid"
MODE_HYBRID_RERANK = "hybrid_rerank"
MODE_FULL = "full"
ALL_MODES = [MODE_VECTOR, MODE_HYBRID, MODE_HYBRID_RERANK, MODE_FULL]

# 经验阈值：RRF 0.016 ≈ 至少一路排进前 5；重排分 < 0.28 基本是"词面都不太沾边"，
# 这时候硬答就是编。两个阈值都可在调用处覆盖。
RRF_MIN = 0.016
RERANK_MIN = 0.28

# 拒答阈值（2026-10-08 用 50 条评估集校准出来的，见 eval/refusal_calibration.md）：
#   库内可回答问题的 top-1 词面覆盖率最低 0.211，库外无答案问题最高 0.125
#   → 取中间值 0.13 做门禁，实测拒答准确率 100%、误拒 0%
COVERAGE_MIN = 0.13


class RetrieverV3:
    def __init__(self, store, embedder, ask_model=None):
        self.store = store
        self.embedder = embedder
        self.ask_model = ask_model      # 查询改写 / LLM 重排用；可为 None
        self._bm25 = None
        self._ids = self._texts = self._metas = None

    # ---------- 关键词索引（懒加载） ----------
    def _ensure_bm25(self):
        if self._bm25 is None:
            data = self.store.get_all()
            self._ids = data["ids"]
            self._texts = data["documents"]
            self._metas = data["metadatas"]
            self._bm25 = BM25(self._texts)
        return self._bm25

    # ---------- 单路召回 ----------
    def _vector_recall(self, query, n):
        vec = self.embedder.encode([query])[0]
        res = self.store.query(vec, n_results=n)
        hits = []
        for i, cid in enumerate(res["ids"][0]):
            hits.append({
                "id": cid,
                "text": res["documents"][0][i],
                "source": (res["metadatas"][0][i] or {}).get("source", ""),
                "vector_score": round(1 - res["distances"][0][i], 4),
                "bm25_score": 0.0,
            })
        return hits

    def _bm25_recall(self, query, n):
        bm25 = self._ensure_bm25()
        hits = []
        for idx, score in bm25.search(query, n):
            if score <= 0:
                continue
            hits.append({
                "id": self._ids[idx],
                "text": self._texts[idx],
                "source": (self._metas[idx] or {}).get("source", ""),
                "vector_score": 0.0,
                "bm25_score": round(float(score), 4),
            })
        return hits

    # ---------- 融合：多查询 × 双路 → RRF ----------
    def _fuse(self, queries, n_each=HYBRID_TOPK):
        pool, ranked_lists = {}, []
        for q in queries:
            v = self._vector_recall(q, n_each)
            b = self._bm25_recall(q, n_each)
            for h in v + b:
                if h["id"] not in pool:
                    pool[h["id"]] = dict(h)
                else:
                    # 同一块被多条改写命中：各自分数取更大值
                    pool[h["id"]]["vector_score"] = max(
                        pool[h["id"]]["vector_score"], h["vector_score"])
                    pool[h["id"]]["bm25_score"] = max(
                        pool[h["id"]]["bm25_score"], h["bm25_score"])
            ranked_lists.append([h["id"] for h in v])
            ranked_lists.append([h["id"] for h in b])
        fused = rrf_fuse(ranked_lists, k=60)
        out = []
        for rank, (cid, score) in enumerate(fused, start=1):
            item = dict(pool[cid])
            item["rrf_score"] = round(score, 5)
            item["rrf_rank"] = rank
            out.append(item)
        return out

    # ---------- 对外主入口 ----------
    def retrieve(self, question, top_k=DEFAULT_TOP_K, mode=MODE_HYBRID_RERANK,
                 use_llm_rerank=False, use_hyde=False):
        t0 = time.time()
        queries = [question]
        if mode == MODE_FULL:
            queries = multi_query(question, self.ask_model)
            if use_hyde and self.ask_model is not None:
                fake = hyde(question, self.ask_model)
                if fake:
                    queries = queries + [fake]

        if mode == MODE_VECTOR and len(queries) == 1:
            cands = self._vector_recall(question, max(top_k, RERANK_TOP_K))
            for rank, c in enumerate(cands, start=1):
                c["rrf_rank"] = rank
                c["rrf_score"] = c.get("vector_score", 0.0)
            hits = cands
        else:
            cands = self._fuse(queries)
            hits = cands
            if mode in (MODE_HYBRID_RERANK, MODE_FULL):
                # 重排优先级：LLM listwise（显式开启）→ cross-encoder（有模型）→ 特征重排
                reranked = None
                if use_llm_rerank and self.ask_model is not None:
                    reranked = llm_rerank(question, cands[:RERANK_TOP_K],
                                          self.ask_model)
                if reranked:
                    hits = reranked
                else:
                    ce = cross_encoder_rerank(question, cands[:RERANK_TOP_K])
                    hits = ce if ce else feature_rerank(question,
                                                        cands[:RERANK_TOP_K])

        top = hits[:top_k]
        for h in top:
            h["mode"] = mode
        return {
            "hits": top,
            "mode": mode,
            "queries": queries,
            "candidates": len(hits),
            "latency_ms": round((time.time() - t0) * 1000, 1),
        }


def should_refuse(result, question="", min_cov=COVERAGE_MIN,
                  min_rrf=RRF_MIN, min_rerank=RERANK_MIN):
    """拒答判断：候选都太弱 → 上层直接说"资料里没有"，别硬答。

    返回 (是否拒答, 理由)。这是 v3 相对 v2 最关键的"可信"改动：
    v2 无论检索到什么都会把 top-k 塞进模型，模型只能硬编。
    """
    hits = result.get("hits") or []
    if not hits:
        return True, "检索无结果"
    top = hits[0]
    if question:
        from rerank_v3 import coverage      # 局部导入，避免循环依赖
        cov = coverage(question, top.get("text", ""))
        if cov < min_cov:
            return True, ("最高覆盖率 %.3f < 阈值 %.2f"
                          "（问题里的词几乎没出现在资料里）" % (cov, min_cov))
    if result.get("mode") in (MODE_HYBRID_RERANK, MODE_FULL):
        score = top.get("rerank_score")
        if score is not None and score < min_rerank:
            return True, "最高重排分 %s < 阈值 %s" % (score, min_rerank)
    rrf = top.get("rrf_score")
    if rrf is not None and rrf < min_rrf:
        return True, "最高 RRF 分 %s < 阈值 %s" % (rrf, min_rrf)
    return False, ""
