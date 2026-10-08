# -*- coding: utf-8 -*-
"""问答 v3：检索 → 拒答判断 → 答案级自检 → 带引用生成（支持流式）

相对 v2 的 qa.py 的三点变化：
  1. 生成前多了两道门：统计门禁（should_refuse）+ 答案级自检（selfcheck）
     —— 资料不够就直接说"资料里没有"，不编。
  2. 引用改成**结构化返回**（编号 / 来源 / 片段 / 分数），前端可以直接定位到段落，
     不是让模型在正文里手写 [1] 完事。
  3. 支持流式（stream=True 返回生成器），并把 token 用量与耗时写进 trace。
"""
import json
import re
import time

import requests

import trace as trace_mod
from config import LLM_MODEL, LLM_URL
from retriever_v3 import should_refuse
import selfcheck as selfcheck_mod

SYSTEM_PROMPT = ("你是知识库问答助手。只能依据提供的资料回答；"
                 "资料不足就直说没有，不要编。回答里用 [编号] 标注引用。")


def build_prompt(question, hits):
    lines = ["下面是从知识库检索到的资料片段，请只依据它们回答。", ""]
    for i, h in enumerate(hits, start=1):
        lines.append("[%d] 来源：%s\n%s" % (i, h.get("source", "未知"), h.get("text", "")))
    lines += ["", "问题：%s" % question,
              "要求：先给结论，再说依据；资料里没有的内容直接说「资料里没有相关内容」。"]
    return "\n\n".join(lines)


def citations(question, hits):
    """结构化引用：编号 / 来源 / **句级引文 + 偏移** / 相关性分。

    句级引文靠 locate.py 从命中的块里再挑一句——用户点开引用要核对的是具体依据，
    给一整块（200-300 字）等于让他自己找。
    """
    from locate import locate
    out = []
    for i, h in enumerate(hits, start=1):
        loc = locate(question, h.get("text") or "")
        out.append({
            "index": i,
            "source": h.get("source", ""),
            "snippet": (h.get("text") or "")[:200],
            "quote": loc["quote"],
            "offset": loc["offset"],
            "locate_score": loc["score"],
            "score": h.get("rerank_score") or h.get("rrf_score") or 0,
            "chunk_id": h.get("id", ""),
        })
    return out


def _chat(prompt, api_key, stream=False, temperature=0.3, max_tokens=1024):
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if stream:
        payload["stream"] = True
    return requests.post(LLM_URL,
                         headers={"Authorization": "Bearer " + api_key},
                         json=payload, stream=stream, timeout=120)


def _iter_stream(resp):
    """解析 OpenAI 兼容的 SSE 流，逐块 yield 文本。"""
    for raw in resp.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data:"):
            continue
        data = raw[5:].strip()
        if data == "[DONE]":
            break
        try:
            delta = json.loads(data)["choices"][0].get("delta", {})
        except Exception:
            continue
        piece = delta.get("content")
        if piece:
            yield piece


def answer(question, retriever, api_key, mode="hybrid_rerank", top_k=5,
           use_selfcheck=True, stream=False):
    """返回 dict：{answer, citations, refused, reason, trace:{...}}。
    stream=True 时额外带 "stream": 生成器（HTTP 层用 StreamingResponse 转发）。"""
    t0 = time.time()
    res = retriever.retrieve(question, top_k=top_k, mode=mode)
    hits = res["hits"]
    refuse, reason = should_refuse(res, question)
    checked = None
    if not refuse and use_selfcheck:
        ok, evidence, missing = selfcheck_mod.assess(question, hits, retriever.ask_model)
        checked = {"answerable": ok, "evidence": evidence, "missing": missing}
        if not ok:
            refuse, reason = True, "答案级自检判定资料不足" + (("：" + missing) if missing else "")
    base = {
        "question": question, "mode": mode, "queries": res.get("queries"),
        "candidates": res.get("candidates"),
        "citations": citations(question, hits), "selfcheck": checked,
        "retrieval_ms": res.get("latency_ms"),
    }
    if refuse:
        out = dict(base, answer="资料里没有相关内容。", refused=True, reason=reason,
                   latency_ms=round((time.time() - t0) * 1000, 1))
        trace_mod.log("ask", question=question, mode=mode, refused=True,
                      reason=reason, candidates=res.get("candidates"),
                      latency_ms=out["latency_ms"], cost_cny=0, source_hits=[])
        return out
    prompt = build_prompt(question, hits)
    if stream:
        resp = _chat(prompt, api_key, stream=True)

        def gen():
            buf = []
            for piece in _iter_stream(resp):
                buf.append(piece)
                yield piece
            text = "".join(buf)
            el = round((time.time() - t0) * 1000, 1)
            trace_mod.log("ask", question=question, mode=mode, refused=False,
                          candidates=res.get("candidates"), latency_ms=el,
                          answer_chars=len(text), cost_cny=0,
                          source_hits=[c["source"] for c in base["citations"]])

        out = dict(base, answer="", refused=False, reason="", stream=gen(),
                   latency_ms=None)
        return out
    resp = _chat(prompt, api_key, stream=False)
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    cost = trace_mod.estimate_cost(usage.get("prompt_tokens", 0),
                                   usage.get("completion_tokens", 0))
    el = round((time.time() - t0) * 1000, 1)
    trace_mod.log("ask", question=question, mode=mode, refused=False,
                  candidates=res.get("candidates"), latency_ms=el,
                  answer_chars=len(text), cost_cny=cost,
                  prompt_tokens=usage.get("prompt_tokens"),
                  completion_tokens=usage.get("completion_tokens"),
                  source_hits=[c["source"] for c in base["citations"]])
    out = dict(base, answer=text, refused=False, reason="", latency_ms=el,
               cost_cny=cost, tokens=usage)
    return out
