# -*- coding: utf-8 -*-
"""长期记忆的语义检索（把记忆从"键值式"升级成"可语义召回"）

问题：agent_memory.py 存的是事实表（键值），"上次那个高匹配的南京岗位"这种
模糊指代根本查不出来——键值只能精确匹配。

三档自动降级，保证任何环境都能跑：
  1) bge 向量   —— 本地有 sentence-transformers + 缓存模型（语义最准）
  2) TF-IDF     —— 有 scikit-learn（词面相似，短记忆够用）
  3) 词面重合   —— 纯标准库兜底

存储：offeragent/data/memory_vec.jsonl，一行一条 {ts, text, meta...}
接口：add_memory(text, **meta) / search(query, k) / context_block(query, k)
"""
import json
import time
from pathlib import Path

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
STORE = DATA_DIR / "memory_vec.jsonl"

_embedder = None
_backend = None


def _load():
    if not STORE.exists():
        return []
    out = []
    for line in STORE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def add_memory(text, **meta):
    """写一条长期记忆（同文本自动去重）。"""
    text = (text or "").strip()
    if not text:
        return None
    rows = _load()
    if any(r.get("text") == text for r in rows):
        return None
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "text": text}
    rec.update(meta)
    with STORE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def _get_embedder():
    """优先用 bge（和 RAG 项目同一个模型，本地已缓存）。""" 
    global _embedder, _backend
    if _backend is not None:
        return _embedder
    # 踩坑：必须先设离线开关再 import sentence_transformers。
    # 否则它会去 HuggingFace 查版本，网络不通时是"卡住几分钟"而不是抛异常
    # （test_agent_v3 卡死就是这个原因）。没缓存就干脆不联网，直接降级。
    import os
    hub = os.path.expanduser("~/.cache/huggingface/hub")
    if not os.path.isdir(os.path.join(hub, "models--BAAI--bge-small-zh-v1.5")):
        _embedder, _backend = None, None
        return None
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    try:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("BAAI/bge-small-zh-v1.5", device="cpu")
        _backend = "bge"
    except Exception:
        _embedder, _backend = None, None
    return _embedder


def _tfidf_scores(query, texts):
    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3), sublinear_tf=True)
    m = vec.fit_transform(texts + [query])
    return list((m[:-1] @ m[-1].T).toarray().ravel())


def _overlap_scores(query, texts):
    qs = set(query)
    return [len(qs & set(t)) / max(len(qs), 1) for t in texts]


def search(query, k=3):
    """返回 [{text, score, backend, ...}]，按相关性降序。"""
    rows = _load()
    if not rows:
        return []
    texts = [r["text"] for r in rows]
    model = _get_embedder()
    if model is not None:
        try:
            import numpy as np
            embs = model.encode(texts + [query], normalize_embeddings=True,
                                show_progress_bar=False)
            scores = list((np.array(embs[:-1]) @ np.array(embs[-1])).ravel())
            backend = "bge"
        except Exception:
            scores, backend = _overlap_scores(query, texts), "overlap"
    else:
        try:
            scores, backend = _tfidf_scores(query, texts), "tfidf"
        except Exception:
            scores, backend = _overlap_scores(query, texts), "overlap"
    ranked = sorted(zip(rows, scores), key=lambda x: -x[1])[:k]
    out = []
    for r, s in ranked:
        item = dict(r)
        item["score"] = round(float(s), 4)
        item["backend"] = backend
        out.append(item)
    return out


def context_block(query, k=3, min_score=0.35):
    """给 Agent 用的记忆注入块：召回到的记忆拼成一段文字接在 system 后面。"""
    hits = [h for h in search(query, k) if h["score"] >= min_score]
    if not hits:
        return ""
    lines = ["【长期记忆（按相关性召回，仅供参考，不当新事实用）】"]
    for h in hits:
        lines.append("- (%s, %.2f) %s" % (h.get("ts", "")[:10], h["score"],
                                          h["text"][:160]))
    return "\n".join(lines)
