# -*- coding: utf-8 -*-
"""结构化 trace：每次问答落一条 JSONL，用于可观测与成本核算

为什么必须有（招聘方最看重的一层）：demo 和系统的差别就在"出问题能不能查"。
这里记录每次请求的：问题 / 改写后的检索式 / 候选块数 / top-k 分数与来源 /
是否拒答 / 各阶段耗时 / token 用量与估算成本。
有了它才能回答"P95 多少、贵不贵、错在哪一步"这类问题。
"""
import json
import os
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TRACE_DIR = os.path.join(HERE, "data")
TRACE_PATH = os.path.join(TRACE_DIR, "trace.jsonl")
TRACE_MAX_BYTES = int(os.environ.get("TRACE_MAX_BYTES", str(5 * 1024 * 1024)))
_lock = threading.Lock()

# DeepSeek 价格（元/百万 token，官方价目取整，仅用于成本估算不用于计费）
PRICE_IN = 1.0
PRICE_OUT = 2.0


def _ensure():
    os.makedirs(TRACE_DIR, exist_ok=True)


def _rotate_if_needed():
    """日志轮转：trace 只留最近一份备份，避免线上无限长下去把磁盘写满。

    为什么必须有：JSONL 每问一次就追加一行，长期跑下去是典型的"悄悄吃满磁盘"的坑。
    """
    try:
        if TRACE_MAX_BYTES <= 0 or not os.path.exists(TRACE_PATH):
            return
        if os.path.getsize(TRACE_PATH) < TRACE_MAX_BYTES:
            return
        backup = TRACE_PATH + ".1"
        if os.path.exists(backup):
            os.remove(backup)
        os.replace(TRACE_PATH, backup)
    except Exception:
        pass          # 轮转失败不能影响写日志


def log(event, **fields):
    """追加一条 trace。任何异常都不能影响主流程。"""
    try:
        _ensure()
        rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "event": event}
        rec.update(fields)
        with _lock:
            _rotate_if_needed()
            with open(TRACE_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def load(limit=2000):
    if not os.path.exists(TRACE_PATH):
        return []
    out = []
    with open(TRACE_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out[-limit:]


def stats():
    """从 trace 聚合服务指标：跑了多少次、拒答率、P50/P95、候选数、成本。"""
    rows = [r for r in load() if r.get("event") == "ask"]
    if not rows:
        return {"asks": 0}
    lat = sorted(r.get("latency_ms", 0) for r in rows)
    refused = sum(1 for r in rows if r.get("refused"))
    cost = sum(r.get("cost_cny", 0) for r in rows)

    def q(p):
        return lat[min(len(lat) - 1, int(len(lat) * p))]

    return {
        "asks": len(rows),
        "refused": refused,
        "refusal_rate": round(refused / len(rows), 3),
        "p50_ms": q(0.5),
        "p95_ms": q(0.95),
        "avg_candidates": round(sum(r.get("candidates", 0) for r in rows) / len(rows), 1),
        "total_cost_cny": round(cost, 4),
        "avg_cost_cny": round(cost / len(rows), 6),
    }


def estimate_cost(prompt_tokens, completion_tokens):
    return round(prompt_tokens / 1e6 * PRICE_IN
                 + completion_tokens / 1e6 * PRICE_OUT, 6)
