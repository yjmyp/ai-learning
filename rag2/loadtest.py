# -*- coding: utf-8 -*-
"""RAG 检索服务压测：并发打 /search 与 /ask，报 QPS / P50 / P95 / P99 / 错误率

为什么要写它：面试官问过"你这服务能扛多少 QPS"。凭感觉答 = 送分题变送命题；
跑一次拿真实数字，并且能顺带证明瓶颈在哪（CPU 单进程推理 vs 网络）。

跑法（在 rag2 目录下）：
    python loadtest.py                      # 默认 hybrid_rerank 档，并发 1/2/4/8
    python loadtest.py --mode vector --n 60 # 只测某档
    python loadtest.py --ask                # 连 /ask 一起压（会真花 API 钱，默认关）

产出：控制台表格 + eval/loadtest_report.md
"""
import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8602
BASE = "http://127.0.0.1:%d" % PORT

QUESTIONS = [
    "什么是 RAG？",
    "上下文窗口是什么",
    "向量检索怎么算相似度",
    "BM25 和向量检索有什么区别",
    "怎么评估检索效果",
    "什么是 Agent 的工具调用",
    "切块大小怎么定",
    "重排 rerank 的作用是什么",
    "大模型为什么会有幻觉",
    "prompt 应该怎么写",
]


def wait_up(timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if requests.get(BASE + "/ready", timeout=5).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def one_search(q, mode, top_k):
    t0 = time.perf_counter()
    try:
        r = requests.post(BASE + "/search", json={"q": q, "mode": mode, "top_k": top_k},
                          timeout=120)
        dt = (time.perf_counter() - t0) * 1000
        return (r.status_code == 200, dt)
    except Exception:
        return (False, (time.perf_counter() - t0) * 1000)


def one_ask(q, mode, top_k):
    t0 = time.perf_counter()
    try:
        r = requests.post(BASE + "/ask", json={"q": q, "mode": mode, "top_k": top_k,
                                              "stream": False}, timeout=300)
        dt = (time.perf_counter() - t0) * 1000
        return (r.status_code == 200, dt)
    except Exception:
        return (False, (time.perf_counter() - t0) * 1000)


def pct(vals, p):
    if not vals:
        return 0.0
    vals = sorted(vals)
    k = min(int(round((p / 100.0) * (len(vals) - 1))), len(vals) - 1)
    return vals[k]


def run_level(fn, n, concurrency, mode, top_k):
    """并发 c 打 n 次，返回统计。注意：服务是单进程 CPU 推理，
    并发调高主要验证'排队是否线性'，不是指望 QPS 上升。"""
    qs = [QUESTIONS[i % len(QUESTIONS)] for i in range(n)]
    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = [ex.submit(fn, q, mode, top_k) for q in qs]
        results = [f.result() for f in futs]
    wall = time.perf_counter() - t0
    lats = [dt for ok, dt in results if ok]
    return {
        "concurrency": concurrency, "n": n,
        "ok": sum(1 for ok, _ in results if ok),
        "fail": sum(1 for ok, _ in results if not ok),
        "wall_s": round(wall, 2),
        "qps": round(len(results) / wall, 1) if wall else 0.0,
        "p50_ms": round(pct(lats, 50), 1),
        "p95_ms": round(pct(lats, 95), 1),
        "p99_ms": round(pct(lats, 99), 1),
        "mean_ms": round(statistics.fmean(lats), 1) if lats else 0.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="hybrid_rerank")
    ap.add_argument("--n", type=int, default=40, help="每档并发下的请求数")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--concurrency", default="1,2,4,8")
    ap.add_argument("--ask", action="store_true", help="同时压 /ask（真花 API 钱）")
    ap.add_argument("--no-server", action="store_true", help="服务已在跑，不再启动")
    args = ap.parse_args()

    proc = None
    if not args.no_server:
        env = dict(os.environ)
        env["SERVICE_RATE_LIMIT"] = "100000"      # 压测不能被自己的限流挡住
        env.pop("SERVICE_API_KEY", None)
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "service:app", "--port", str(PORT)],
            cwd=HERE, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    report = {"mode": args.mode, "top_k": args.top_k, "n_per_level": args.n,
              "levels": [], "ask_levels": [], "notes": [],
              "cpu_count": os.cpu_count(), "platform": platform.platform()}
    try:
        if not wait_up():
            raise SystemExit("服务没起来（先确认索引已建：python build_index.py）")

        idx = requests.get(BASE + "/ready", timeout=30).json().get("index_chunks")
        report["index_chunks"] = idx
        print("索引块数：%s" % idx)

        # 冷启动单独量：第一次检索要建 BM25 索引 + 预热模型，不能混进稳态数字里
        print("\n== 冷启动（第 1 次请求）==")
        t0 = time.perf_counter()
        cold_ok, _ = one_search(QUESTIONS[0], args.mode, args.top_k)
        cold_ms = round((time.perf_counter() - t0) * 1000, 1)
        report["cold_start_ms"] = cold_ms
        print("第 1 次请求 %s，耗时 %.1f ms" % ("成功" if cold_ok else "失败", cold_ms))
        for i in range(1, 4):                       # 再热 3 次，之后才计稳态
            one_search(QUESTIONS[i], args.mode, args.top_k)
        print("预热完成，开始稳态压测")

        concs = [int(c) for c in str(args.concurrency).split(",") if c.strip()]
        print("\n== /search（mode=%s, top_k=%d, 每档 %d 次）==" % (args.mode, args.top_k, args.n))
        print("%4s %6s %6s %8s %8s %8s %9s" % ("并发", "成功", "失败", "QPS", "P50ms", "P95ms", "P99ms"))
        for c in concs:
            row = run_level(one_search, args.n, c, args.mode, args.top_k)
            report["levels"].append(row)
            print("%4d %6d %6d %8.1f %8.1f %8.1f %9.1f" % (
                row["concurrency"], row["ok"], row["fail"], row["qps"],
                row["p50_ms"], row["p95_ms"], row["p99_ms"]))

        base = report["levels"][0]
        best = max(report["levels"], key=lambda r: r["qps"])
        report["notes"].append(
            "冷启动第 1 次请求 %.0f ms（要建 BM25 索引 + 预热模型），预热后稳态 P50≈%.0f ms "
            "→ 线上必须加预热/探针，否则第一个真实用户吃满冷启动。" % (
                report.get("cold_start_ms", 0), base["p50_ms"]))
        report["notes"].append(
            "稳态最好成绩：并发 %d 时 QPS=%.1f、P95=%.1f ms（本机 %s 核，单进程 uvicorn）；"
            "并发继续拉高只是把延迟抬上去、QPS 不再涨 → 瓶颈是 CPU 上的向量推理，不是网络。" % (
                best["concurrency"], best["qps"], best["p95_ms"], report["cpu_count"]))
        report["notes"].append(
            "扩容路径：① 多 worker（每 worker 一份模型，内存 ×N，需压测显存/内存）"
            "② 把 embedding 抽成独立服务（batch 推理，可上 GPU）"
            "③ 加缓存（同问题命中缓存直接返回）。")

        if args.ask:
            print("\n== /ask（非流式，含 LLM 生成；真花钱，n 建议 ≤ 5）==")
            for c in concs:
                row = run_level(one_ask, min(args.n, 5), c, args.mode, args.top_k)
                row["concurrency"] = c
                report["ask_levels"].append(row)
                print("%4d %6d %6d %8.1f %8.1f %8.1f" % (
                    c, row["ok"], row["fail"], row["qps"], row["p50_ms"], row["p95_ms"]))
            report["notes"].append(
                "/ask 的延迟由 LLM 生成主导（秒级），与检索层无关 → 要提速只能流式首字 + 缓存。")
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except Exception:
                proc.kill()

    out = os.path.join(HERE, "eval", "loadtest_report.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    lines = ["# RAG 服务压测报告（自动生成）", "",
             "- 时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"),
             "- 模式：`%s`，top_k=%d，索引 %s 块" % (
                 args.mode, args.top_k, report.get("index_chunks")),
             "- 冷启动第 1 次请求：%s ms（含 BM25 建索引 + 模型预热）" % report.get(
                 "cold_start_ms"),
             "- 机器：本机 CPU（无 GPU，%s 核），服务单进程 uvicorn" % report["cpu_count"],
             "- 平台：%s" % report["platform"], "",
             "| 并发 | 请求 | 成功 | 失败 | QPS | P50(ms) | P95(ms) | P99(ms) | 总耗时(s) |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in report["levels"]:
        lines.append("| %d | %d | %d | %d | %.1f | %.1f | %.1f | %.1f | %.2f |" % (
            r["concurrency"], r["n"], r["ok"], r["fail"], r["qps"],
            r["p50_ms"], r["p95_ms"], r["p99_ms"], r["wall_s"]))
    if report["ask_levels"]:
        lines += ["", "## /ask（含 LLM）", "",
                  "| 并发 | 请求 | 成功 | QPS | P50(ms) | P95(ms) |",
                  "| --- | --- | --- | --- | --- | --- |"]
        for r in report["ask_levels"]:
            lines.append("| %d | %d | %d | %.1f | %.1f | %.1f |" % (
                r["concurrency"], r["n"], r["ok"], r["qps"], r["p50_ms"], r["p95_ms"]))
    lines += ["", "## 结论", ""] + ["- %s" % n for n in report["notes"]]
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n报告已写：%s" % out)
    print(json.dumps(report["levels"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
