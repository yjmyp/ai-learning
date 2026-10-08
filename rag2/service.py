# -*- coding: utf-8 -*-
"""RAG v3 HTTP 服务（FastAPI）：把项目从"本地能跑"变成"能部署、能被调用"

端点：
    GET  /health          服务与索引状态
    GET  /stats           索引规模（按来源分组）+ 服务指标（来自 trace）
    POST /search          {q, mode, top_k} → 检索结果（带分数与来源）
    POST /ask             {q, mode, top_k, stream} → 带引用的回答；stream=true 返回 SSE
    POST /reindex         {force} → 重建索引（需 X-API-Key，防止被误触发）

启动：
    uvicorn service:app --port 8600            （在 rag2 目录下）
    docker compose up --build                  （容器方式，见 Dockerfile）

鉴权：设了环境变量 SERVICE_API_KEY 时，/ask 与 /reindex 需要请求头 X-API-Key。
"""
import json
import os
import sys
import time
import uuid
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import config
import trace as trace_mod
from engine import get_engine
from qa_v3 import answer as answer_v3
from retriever_v3 import ALL_MODES, RetrieverV3

app = FastAPI(title="RAG v3 检索服务", version="3.0")
_engine = None
_retriever = None


def engine():
    global _engine, _retriever
    if _engine is None:
        _engine = get_engine()
        _retriever = RetrieverV3(_engine.store, _engine.embedder, ask_model=_ask)
    return _engine, _retriever


def _ask(prompt):
    """给「查询改写 / 答案级自检」用的模型调用（非流式、短输出）。"""
    import qa_v3
    resp = qa_v3._chat(prompt, config.get_api_key(), stream=False,
                       temperature=0.2, max_tokens=400)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _check_key(api_key):
    expect = os.environ.get("SERVICE_API_KEY", "")
    if expect and api_key != expect:
        raise HTTPException(status_code=401, detail="X-API-Key 不正确")


class SearchReq(BaseModel):
    q: str
    mode: str = "hybrid_rerank"
    top_k: int = 5


class AskReq(BaseModel):
    q: str
    mode: str = "hybrid_rerank"
    top_k: int = 5
    stream: bool = False
    selfcheck: bool = True


class ReindexReq(BaseModel):
    force: bool = True


@app.get("/health")
def health():
    eng, _ = engine()
    return {"status": "ok", "index_chunks": eng.store.count(),
            "embed_model": config.EMBED_MODEL, "llm_model": config.LLM_MODEL,
            "modes": ALL_MODES, "server_time": time.strftime("%Y-%m-%d %H:%M:%S")}


@app.get("/stats")
def stats():
    eng, _ = engine()
    data = eng.store.get_all()
    by_src = Counter((m or {}).get("source", "") for m in data["metadatas"])
    return {"index_chunks": eng.store.count(),
            "sources": len(by_src),
            "top_sources": by_src.most_common(10),
            "service": trace_mod.stats()}


@app.post("/search")
def search(req: SearchReq):
    if req.mode not in ALL_MODES:
        raise HTTPException(status_code=400, detail="mode 必须是 %s" % ALL_MODES)
    _, retriever = engine()
    res = retriever.retrieve(req.q, top_k=req.top_k, mode=req.mode)
    hits = [{"id": h["id"], "source": h.get("source"),
             "vector_score": h.get("vector_score"),
             "bm25_score": h.get("bm25_score"),
             "rrf_score": h.get("rrf_score"),
             "rerank_score": h.get("rerank_score"),
             "text": (h.get("text") or "")[:300]} for h in res["hits"]]
    return {"question": req.q, "mode": req.mode, "queries": res.get("queries"),
            "candidates": res.get("candidates"),
            "latency_ms": res.get("latency_ms"), "hits": hits}


@app.post("/ask")
def ask(req: AskReq, x_api_key: str = Header(default="")):
    _check_key(x_api_key)
    if req.mode not in ALL_MODES:
        raise HTTPException(status_code=400, detail="mode 必须是 %s" % ALL_MODES)
    _, retriever = engine()
    out = answer_v3(req.q, retriever, config.get_api_key(), mode=req.mode,
                    top_k=req.top_k, use_selfcheck=req.selfcheck, stream=req.stream)
    if req.stream and not out["refused"]:
        rid = uuid.uuid4().hex[:12]

        def sse():
            yield "event: meta\ndata: %s\n\n" % json.dumps(
                {"request_id": rid, "citations": out["citations"],
                 "candidates": out["candidates"]}, ensure_ascii=False)
            for piece in out["stream"]:
                yield "data: %s\n\n" % json.dumps({"delta": piece}, ensure_ascii=False)
            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(sse(), media_type="text/event-stream")
    out.pop("stream", None)
    return out


@app.post("/reindex")
def reindex(req: ReindexReq, x_api_key: str = Header(default="")):
    _check_key(x_api_key)
    global _retriever
    eng, _ = engine()
    eng.ensure_index(force=req.force)
    _retriever = RetrieverV3(eng.store, eng.embedder, ask_model=_ask)
    trace_mod.log("reindex", chunks=eng.store.count())
    return {"status": "reindexed", "index_chunks": eng.store.count()}
