# -*- coding: utf-8 -*-
"""重排 v3：三档，按可用性自动降级

  ① cross-encoder  —— 最强（bge-reranker-*），需要本地有模型；离线没缓存就跳过
  ② llm-listwise   —— 让大模型直接给候选块排序（一次调用排 20 个），效果接近
                      交叉编码器，代价是 1 次 LLM 调用；没有 key 时跳过
  ③ feature        —— 永远可用的兜底：BM25 分 + 向量分 + 词面覆盖率 + 短语命中，
                      各特征归一化后加权。纯本地、零成本、可解释。

v2 用的 TF-IDF 字符 n-gram 属于 ③ 的一种，但只用了"字符相似"一个信号；
这里把多个信号显式拆开，既能解释"为什么这块排第一"，也方便做消融实验。
"""
import re

from bm25 import tokenize
from fusion import normalize

CN_STOP = set("的了是在和与或而及其这那有无不为对把被从到于中上下个把等及以" )


def _terms(text):
    return [t for t in tokenize(text) if t not in CN_STOP]


def coverage(query, text):
    """查询词在块里的覆盖率（词面命中比例）——回答"是不是每个问题词都出现了"。"""
    q = set(_terms(query))
    if not q:
        return 0.0
    t = set(_terms(text))
    return len(q & t) / len(q)


def phrase_bonus(query, text, n=4):
    """查询的前 n 个字是否原样出现在块里——中文里这是很强的相关性信号。"""
    q = re.sub(r"\s+", "", query)
    if len(q) < n:
        return 0.0
    return 1.0 if q[:n] in re.sub(r"\s+", "", text) else 0.0


def feature_rerank(question, chunks,
                   w_vec=0.35, w_cov=0.35, w_phrase=0.20, w_rank=0.10):
    """③ 兜底重排：多特征加权。chunks 需要带 vector_score / bm25_score / rank。

    特征的量纲都先归一化到 0~1，再加权 —— 这是和 v2 最大的区别：
    v2 直接拿 TF-IDF 相似度当最终分，各信号混在一起无法解释、也无法调权重。
    """
    if len(chunks) <= 1:
        return chunks
    vec = normalize([float(c.get("vector_score") or 0.0) for c in chunks])
    bm = normalize([float(c.get("bm25_score") or 0.0) for c in chunks])
    cov = [coverage(question, c.get("text", "")) for c in chunks]
    ph = [phrase_bonus(question, c.get("text", "")) for c in chunks]
    # 融合阶段的名次也要保留一点权重（RRF 名次本身是有信息的）
    rk = normalize([-float(c.get("rrf_rank") or 99) for c in chunks])

    out = []
    for i, c in enumerate(chunks):
        # bm25 和向量各占一半的"相关性"，避免只有一种信号时权重浪费
        rel = 0.5 * (vec[i] + bm[i]) if bm[i] else vec[i]
        score = (w_vec * rel + w_cov * cov[i] + w_phrase * ph[i] + w_rank * rk[i])
        item = dict(c)
        item["rerank_score"] = round(score, 4)
        item["feat"] = {"vec": round(vec[i], 3), "bm25": round(bm[i], 3),
                        "coverage": round(cov[i], 3), "phrase": ph[i]}
        out.append(item)
    out.sort(key=lambda x: -x["rerank_score"])
    for pos, it in enumerate(out, start=1):
        it["rerank_rank"] = pos
    return out


LLM_RERANK_PROMPT = """下面有一个用户问题和若干候选资料片段。请判断哪些片段真正能回答这个问题。

只输出 JSON 数组，元素是片段编号，按"能回答问题的程度"从高到低排列，最多 {n} 个；
完全无关的片段不要出现在结果里。不要解释、不要代码块。

问题：{q}

候选片段：
{cands}
"""


def llm_rerank(question, chunks, ask_model, top_n=8):
    """② 让大模型做 listwise 重排。ask_model(prompt) -> str。失败则返回 None。"""
    if not chunks or ask_model is None:
        return None
    cands = "\n".join(f"[{i}] {(c.get('text') or '')[:180]}"
                      for i, c in enumerate(chunks, start=1))
    prompt = LLM_RERANK_PROMPT.format(n=top_n, q=question, cands=cands)
    try:
        raw = (ask_model(prompt) or "").strip()
        m = re.search(r"\[[\s\d,]+\]", raw)
        if not m:
            return None
        order = [int(x) for x in re.findall(r"\d+", m.group(0))]
    except Exception:
        return None
    picked = []
    for idx in order:
        if 1 <= idx <= len(chunks):
            item = dict(chunks[idx - 1])
            item["llm_rank"] = len(picked) + 1
            picked.append(item)
    # 模型没提到的片段按原顺序补在后面（不丢候选，方便后续接阈值判断）
    picked_ids = {id(x) for x in picked}
    for c in chunks:
        if id(c) not in picked_ids:
            picked.append(c)
    return picked


def cross_encoder_rerank(question, chunks, model_name="BAAI/bge-reranker-base"):
    """① 交叉编码器重排。本地没缓存模型时直接返回 None（离线环境不下载）。"""
    try:
        from sentence_transformers import CrossEncoder
        model = CrossEncoder(model_name, device="cpu")
    except Exception:
        return None
    try:
        pairs = [(question, c.get("text", "")) for c in chunks]
        scores = model.predict(pairs)
    except Exception:
        return None
    out = []
    for c, s in zip(chunks, scores):
        item = dict(c)
        item["ce_score"] = round(float(s), 4)
        out.append(item)
    out.sort(key=lambda x: -x["ce_score"])
    return out
