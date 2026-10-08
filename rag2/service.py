# -*- coding: utf-8 -*-
"""RAG v3 HTTP 服务（FastAPI）：把项目从"本地能跑"变成"能部署、能被调用"

端点：
    GET  /live            存活探针（极轻，不加载模型）——给 K8s livenessProbe
    GET  /ready           就绪探针（索引非空才 200，否则 503）——给 readinessProbe
    GET  /health          服务与索引详情（会加载模型，较重）
    GET  /stats           索引规模（按来源分组）+ 服务指标（来自 trace）
    POST /search          {q, mode, top_k} → 检索结果（带分数与来源）
    POST /ask             {q, mode, top_k, stream} → 带引用的回答；stream=true 返回 SSE
    POST /reindex         {force} → 重建索引（需 X-API-Key，防止被误触发）

探针分工（线上必须区分，否则会出现"模型正在加载却被判死"或"索引空却接流量"）：
    liveness  → /live   只问进程活着没，绝不能碰模型（探针每秒都在打）
    readiness → /ready  只问能不能接流量（索引块数 > 0）

启动：
    uvicorn service:app --port 8600            （在 rag2 目录下）
    docker compose up --build                  （容器方式，见 Dockerfile）

鉴权：设了环境变量 SERVICE_API_KEY 时，/ask 与 /reindex 需要请求头 X-API-Key。
限流：SERVICE_RATE_LIMIT / SERVICE_RATE_WINDOW 控制固定窗口速率，探针端点不占额度。
"""
import json
import os
import sys
import time
import uuid
import threading
from contextlib import asynccontextmanager
from collections import deque

from fastapi import Request
from fastapi.responses import JSONResponse
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import config
import trace as trace_mod
from engine import get_engine
from qa_v3 import answer as answer_v3
from retriever_v3 import ALL_MODES, RetrieverV3

_engine = None
_retriever = None


def _warmup():
    """启动预热：把模型加载 + BM25 索引构建 + Chroma 首次查询都提前做掉。

    压测实测：不预热时**第一个真实请求要等 15.3 秒**（见 eval/loadtest_report.md），
    预热后稳态 P50 只有 66ms。开启方式：SERVICE_WARMUP=1（Dockerfile 里默认开）。
    """
    if os.environ.get("SERVICE_WARMUP", "0") not in ("1", "true", "yes"):
        return {"warmed": False, "reason": "SERVICE_WARMUP 未开启"}
    t0 = time.time()
    try:
        eng, ret = engine()
        if eng.store.count() == 0:
            return {"warmed": False, "reason": "索引为空，跳过预热（先建库）"}
        for mode in ("vector", "hybrid_rerank"):     # 各有独立的懒加载路径
            ret.retrieve("预热查询：什么是 RAG？", top_k=1, mode=mode)
        ms = round((time.time() - t0) * 1000, 1)
        trace_mod.log("warmup", ok=True, latency_ms=ms)
        print("[warmup] 预热完成：%.0f ms" % ms, flush=True)
        return {"warmed": True, "latency_ms": ms}
    except Exception as e:                            # 预热失败不能拖垮启动
        trace_mod.log("warmup", ok=False, error=str(e)[:200])
        print("[warmup] 预热失败（不影响启动）：%s" % e, flush=True)
        return {"warmed": False, "reason": str(e)[:200]}


@asynccontextmanager
async def _lifespan(app):
    """启动钩子：预热。放后台线程跑，避免把端口监听也一起挡住。"""
    global _warmup_result
    th = threading.Thread(target=lambda: _warmup_result.update(_warmup()),
                          name="warmup", daemon=True)
    th.start()
    yield


_warmup_result = {}

if not os.environ.get("SERVICE_API_KEY", ""):
    print("[warn] 未设置 SERVICE_API_KEY：/ask、/search、/reindex、/stats 将不鉴权。"
          "公网部署必须设置。", flush=True)

app = FastAPI(title="RAG v3 检索服务", version="3.0", lifespan=_lifespan)

# ---------------- 生产化：鉴权 / 限流 / 请求 ID / 结构化错误 ----------------
SERVICE_VERSION = "3.1.0"
_STARTED_AT = time.time()
RATE_LIMIT = int(os.environ.get("SERVICE_RATE_LIMIT", "60"))   # 每窗口允许的请求数
RATE_WINDOW = float(os.environ.get("SERVICE_RATE_WINDOW", "60"))  # 窗口秒数
# 探针/文档类端点不计入限流：负载均衡和 K8s liveness 会高频打 /health，
# 若算进用户配额，正常流量会被探针挤爆（这是限流最常见的线上踩坑）。
EXEMPT_PATHS = frozenset({"/health", "/live", "/ready", "/version",
                          "/docs", "/openapi.json", "/redoc"})
_hits = {}                       # key -> deque[timestamps]
_hits_lock = threading.Lock()


def _client_key(request):
    return (request.headers.get("x-api-key")
            or (request.client.host if request.client else "unknown"))


def _rate_ok(key):
    """固定窗口限流（够用且可解释；要更平滑可换令牌桶）。"""
    now = time.time()
    with _hits_lock:
        q = _hits.setdefault(key, deque())
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return False, len(q)
        q.append(now)
        return True, len(q)


@app.middleware("http")
async def _observe(request: Request, call_next):
    """给每个请求配 ID、做限流、异常统一成结构化错误（不把堆栈丢给客户端）。"""
    rid = uuid.uuid4().hex[:12]
    path = str(request.url.path)
    key = _client_key(request)
    if path in EXEMPT_PATHS:
        # 探针不占额度，只看当前用量，用于回填 X-RateLimit-Remaining
        with _hits_lock:
            used = len(_hits.get(key, ()))
        ok = True
    else:
        ok, used = _rate_ok(key)
    if not ok:
        resp = JSONResponse(status_code=429, content={
            "error": {"code": "rate_limited",
                      "message": "请求过于频繁，%d 秒内上限 %d 次" % (RATE_WINDOW, RATE_LIMIT),
                      "request_id": rid}})
        resp.headers["Retry-After"] = str(int(RATE_WINDOW))
        resp.headers["X-Request-ID"] = rid
        resp.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
        resp.headers["X-RateLimit-Remaining"] = "0"
        trace_mod.log("http", request_id=rid, path=path,
                      status=429, client=key[:24])
        return resp
    t0 = time.time()
    try:
        resp = await call_next(request)
    except Exception as e:                       # 未捕获异常 → 结构化 500
        trace_mod.log("http", request_id=rid, path=path,
                      status=500, error=str(e)[:200])
        resp = JSONResponse(status_code=500, content={
            "error": {"code": "internal_error", "message": str(e)[:200],
                      "request_id": rid}})
    resp.headers["X-Request-ID"] = rid
    resp.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
    resp.headers["X-RateLimit-Remaining"] = str(max(RATE_LIMIT - used, 0))
    trace_mod.log("http", request_id=rid, path=path,
                  status=getattr(resp, "status_code", 0),
                  latency_ms=round((time.time() - t0) * 1000, 1))
    return resp


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
    # 输入校验 = 最便宜的防滥用手段：不限制的话一个 1MB 的问题就能把 embedding 拖死
    q: str = Field(min_length=1, max_length=2000)
    mode: str = "hybrid_rerank"
    top_k: int = Field(default=5, ge=1, le=50)


class AskReq(BaseModel):
    q: str = Field(min_length=1, max_length=2000)
    mode: str = "hybrid_rerank"
    top_k: int = Field(default=5, ge=1, le=50)
    stream: bool = False
    selfcheck: bool = True


class ReindexReq(BaseModel):
    force: bool = True


@app.get("/health")
def health():
    eng, _ = engine()
    return {"status": "ok", "version": SERVICE_VERSION,
            "index_chunks": eng.store.count(),
            "embed_model": config.EMBED_MODEL, "llm_model": config.LLM_MODEL,
            "modes": ALL_MODES, "server_time": time.strftime("%Y-%m-%d %H:%M:%S")}


@app.get("/live")
def live():
    """存活探针：不触碰模型/索引，保证秒回。"""
    return {"status": "alive", "version": SERVICE_VERSION,
            "pid": os.getpid(), "uptime_s": round(time.time() - _STARTED_AT, 1)}


@app.get("/ready")
def ready():
    """就绪探针：索引为空、或还在预热（SERVICE_WARMUP=1）时返回 503，让网关先别转流量过来。

    为什么要等预热：实测首检索要 28 秒（加载向量模型 + 建 BM25 索引）。
    "进程活着"不代表"能快速服务"，就绪语义应该是后者；不然第一个真实用户吃满冷启动。
    """
    eng, _ = engine()
    n = eng.store.count()
    warming_cfg = os.environ.get("SERVICE_WARMUP", "0") in ("1", "true", "yes")
    still_warming = warming_cfg and not _warmup_result        # 预热线程还没回来
    body = {"status": "warming_up" if still_warming else ("ready" if n else "indexing"),
            "version": SERVICE_VERSION, "index_chunks": n, "modes": ALL_MODES,
            "warmup": _warmup_result}
    if not n or still_warming:
        return JSONResponse(status_code=503, content=body)
    return body


@app.get("/version")
def version():
    """给部署用：一眼看出线上跑的是哪版（配合本地指纹比对）。"""
    return {"service": SERVICE_VERSION, "protocol": "rest+sse",
            "modes": ALL_MODES, "rate_limit": "%d req / %ds" % (RATE_LIMIT, RATE_WINDOW),
            "auth_required": bool(os.environ.get("SERVICE_API_KEY", "")),
            "warmup": _warmup_result}


@app.get("/stats")
def stats(x_api_key: str = Header(default="")):
    _check_key(x_api_key)          # 索引规模与服务指标属于内部信息，要鉴权
    eng, _ = engine()
    data = eng.store.get_all()
    by_src = Counter((m or {}).get("source", "") for m in data["metadatas"])
    return {"index_chunks": eng.store.count(),
            "sources": len(by_src),
            "top_sources": by_src.most_common(10),
            "service": trace_mod.stats()}


@app.post("/search")
def search(req: SearchReq, x_api_key: str = Header(default="")):
    _check_key(x_api_key)
    if req.mode not in ALL_MODES:
        raise HTTPException(status_code=422, detail={
            "code": "bad_mode", "message": "mode 必须是 %s" % ALL_MODES})
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
