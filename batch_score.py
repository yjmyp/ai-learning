# -*- coding: utf-8 -*-
"""
batch_score.py —— 岗位分析师批量打分排序（商业化：按匹配分排投递优先级）
============================================================================
对全部「待投且未匹配」岗位，分派「岗位分析师」子 Agent 逐个评估质量 + 算匹配度，
把 match_score 回填到 jds/*.meta.json，最后输出按匹配分从高到低的投递优先级表。

用法：
  python batch_score.py                 # 跑全部待投且未匹配的岗位
  python batch_score.py --limit 3       # 只跑前 3 个（省钱）
  python batch_score.py --force         # 重跑全部待投岗位（含已打分的，覆盖回填）
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "offeragent"))

from offer_agent_tools import build_registry
from offer_agent_multi import run_worker
from offer_agent_core import extract_score, gate_verdict

JDS_DIR = os.path.join(HERE, "offeragent", "data", "jds")
PROFILE_PATH = os.path.join(HERE, "offeragent", "data", "profile.md")
MEMORY_DB = os.path.join(HERE, "offeragent", "data", "memory.db")


def load_profile() -> str:
    try:
        return open(PROFILE_PATH, encoding="utf-8").read()
    except FileNotFoundError:
        return "余剑，南京邮电大学网络工程2027届，AI应用开发实习生（RAG/Agent）"


def pending_unmatched(force: bool = False) -> list:
    """[(name, company, jd)] 待投 且（未匹配 或 force 强制重跑）。"""
    out = []
    for p in sorted(os.listdir(JDS_DIR)):
        if not p.endswith(".txt"):
            continue
        name = p[: -len(".txt")]
        meta_path = os.path.join(JDS_DIR, name + ".meta.json")
        try:
            meta = json.load(open(meta_path, encoding="utf-8"))
        except Exception:
            meta = {}
        if meta.get("status") not in ("待投", None):
            continue
        if not force and meta.get("match_score") is not None:
            continue
        jd = open(os.path.join(JDS_DIR, p), encoding="utf-8").read()
        out.append((name, meta.get("company", ""), jd))
    return out


def _score_one(item: tuple, profile: str, reg: dict) -> dict:
    """单个岗位：拼任务 → 调模型 → 抠分数（只算不写文件，文件由主线程统一写，避免并发写冲突）。"""
    t0 = time.time()
    name, company, jd = item
    task = (f"请评估岗位质量并计算匹配度，只调用 assess_job 和 match_job 两个工具，"
            f"不要生成话术。\n【岗位】{company or ''} · {name}\n【JD】\n{jd[:800]}\n【画像】\n{profile[:600]}")
    final, state = run_worker("岗位分析师", task, reg)     # 独立记忆库，不污染用户画像
    score = extract_score(state.trace)
    return {"name": name, "company": company, "score": score,
            "elapsed_s": round(time.time() - t0, 1)}


def run_batch(limit: int | None = None, force: bool = False) -> list:
    """批量打分核心逻辑（CLI 与 Web 共用）。返回按匹配分降序的 results。
    并发版：每个岗位一次 LLM 调用，互相独立 → 线程池 3 个同时打，串行 13 岗 ≈ 并发后约 1/3 时间。"""
    items = pending_unmatched(force)[:limit] if limit else pending_unmatched(force)
    if not items:
        return []
    profile = load_profile()
    reg = build_registry()
    results = []
    t_total = time.time()
    with ThreadPoolExecutor(max_workers=3) as pool:   # 3 个工人同时跑，map 保持输入顺序
        for i, res in enumerate(pool.map(lambda it: _score_one(it, profile, reg), items), 1):
            print(f"[{i}/{len(items)}] {res['company'] or res['name']} …", flush=True)
            if res["score"] is None:
                print(f"    ⚠️ {res['name']} 未调 match_job（门禁未闭环），分数缺失，建议人工复核")
            meta_path = os.path.join(JDS_DIR, res["name"] + ".meta.json")
            try:
                meta = json.load(open(meta_path, encoding="utf-8"))
            except Exception:
                meta = {}
            meta["match_score"] = res["score"]
            meta["match_verdict"] = gate_verdict(res["score"])
            meta["score_elapsed_s"] = res["elapsed_s"]      # 性能量化：每岗耗时
            meta["score_run_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            json.dump(meta, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            results.append({"岗位": res["name"], "公司": res["company"],
                            "匹配分": res["score"], "裁决": gate_verdict(res["score"]),
                            "耗时s": res["elapsed_s"]})
            print(f"    → {res['name']} 匹配分 {res['score']} {gate_verdict(res['score'])} "
                  f"({res['elapsed_s']}s)", flush=True)
    results.sort(key=lambda r: -(r["匹配分"] or 0))
    # 性能汇总：耗时分布（面试能报 P50/P95/总耗时）
    el = sorted(r["耗时s"] for r in results)
    n = len(el)
    perf = {
        "count": n,
        "total_s": round(time.time() - t_total, 1),
        "per_job_p50_s": round(el[int(n * 0.5) - 1], 1) if n else 0,
        "per_job_p95_s": round(el[int(n * 0.95) - 1], 1) if n else 0,
        "max_s": round(el[-1], 1) if n else 0,
        "workers": 3,
    }
    perf_path = os.path.join(HERE, "offeragent", "docs", "batch_score_perf.json")
    os.makedirs(os.path.dirname(perf_path), exist_ok=True)
    with open(perf_path, "w", encoding="utf-8") as f:
        json.dump(perf, f, ensure_ascii=False, indent=2)
    print(f"  性能：{n} 岗总耗时 {perf['total_s']}s，单岗 P50 {perf['per_job_p50_s']}s / "
          f"P95 {perf['per_job_p95_s']}s（3 并发）→ offeragent/docs/batch_score_perf.json", flush=True)
    return results


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    force = "--force" in sys.argv
    results = run_batch(limit=limit, force=force)
    if not results:
        print("没有「待投」岗位可跑（全部已打分？加 --force 强制重跑）。")
        return
    print(f"\n=== 投递优先级（按匹配分从高到低）===")
    for r in results:
        print(f"  {r['匹配分'] or '—':>4}  {r['岗位']:<16} {r['公司']}  [{r['裁决']}]")


if __name__ == "__main__":
    main()
