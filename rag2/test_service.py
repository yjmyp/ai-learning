# -*- coding: utf-8 -*-
"""服务层验收：起 uvicorn → 打四个端点 → 检查 SSE 流 → 看 trace 指标

跑法：python test_service.py        （在 rag2 目录下；会占用 8600 端口约 1 分钟）
"""
import json
import os
import subprocess
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PORT = 8600
BASE = "http://127.0.0.1:%d" % PORT
HERE = os.path.dirname(os.path.abspath(__file__))


def wait_up(timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if requests.get(BASE + "/health", timeout=5).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def main():
    env = dict(os.environ)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "service:app", "--port", str(PORT)],
        cwd=HERE, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    checks = []
    try:
        if not wait_up():
            raise SystemExit("服务没起来")
        h = requests.get(BASE + "/health", timeout=10).json()
        checks.append(("健康检查 + 索引块数", h.get("status") == "ok"
                       and h.get("index_chunks", 0) > 100))
        print("   /health →", {k: h[k] for k in ("status", "index_chunks", "llm_model")})

        st = requests.get(BASE + "/stats", timeout=30).json()
        checks.append(("索引来源数 ≥ 20", st.get("sources", 0) >= 20))
        print("   /stats → 来源 %d 篇 / 共 %d 块" % (st.get("sources", 0),
                                                    st.get("index_chunks", 0)))

        s = requests.post(BASE + "/search",
                          json={"q": "什么是 RAG？", "mode": "hybrid_rerank",
                                "top_k": 3}, timeout=60).json()
        checks.append(("检索返回 3 条且带分数",
                       len(s.get("hits", [])) == 3
                       and s["hits"][0].get("rrf_score") is not None))
        print("   /search → top1 =", (s["hits"][0]["source"] if s.get("hits") else None),
              "| rerank =", s["hits"][0].get("rerank_score") if s.get("hits") else None)

        a = requests.post(BASE + "/ask",
                          json={"q": "什么是 RAG？", "mode": "hybrid_rerank",
                                "stream": False}, timeout=120).json()
        checks.append(("问答返回答案 + 引用 + 不拒答",
                       (not a.get("refused")) and a.get("answer")
                       and len(a.get("citations", [])) > 0))
        print("   /ask → 拒答 =", a.get("refused"), "| 引用数 =",
              len(a.get("citations", [])), "| 延迟 =", a.get("latency_ms"), "ms")

        r = requests.post(BASE + "/ask",
                          json={"q": "特斯拉 Model 3 电池包容量多少度",
                                "stream": False}, timeout=120).json()
        checks.append(("库外问题被拒答", bool(r.get("refused"))))
        print("   /ask(库外) → 拒答 =", r.get("refused"), "| 理由 =", r.get("reason"))

        events, deltas = [], 0
        with requests.post(BASE + "/ask",
                           json={"q": "RAG 里怎么找到最相关资料？", "stream": True},
                           timeout=180, stream=True) as resp:
            for raw in resp.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                if raw.startswith("event:"):
                    events.append(raw.split(":", 1)[1].strip())
                elif raw.startswith("data:") and '"delta"' in raw:
                    deltas += 1
        checks.append(("SSE 流式：有 meta/done 且有增量块",
                       "meta" in events and "done" in events and deltas > 0))
        print("   /ask(stream) → 事件", events, "| 增量块数 =", deltas)

        st2 = requests.get(BASE + "/stats", timeout=30).json()
        svc = st2.get("service", {})
        checks.append(("trace 指标已统计（asks≥3）", svc.get("asks", 0) >= 3))
        print("   服务指标 →", svc)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except Exception:
            proc.kill()

    ok = 0
    print()
    for name, good in checks:
        print(("✅ " if good else "❌ ") + name)
        ok += 1 if good else 0
    print("\n%d/%d 通过" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
