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


def run_batch(limit: int = None, force: bool = False) -> list:
    """批量打分核心逻辑（CLI 与 Web 共用）。返回按匹配分降序的 results。"""
    items = pending_unmatched(force)[:limit] if limit else pending_unmatched(force)
    if not items:
        return []
    profile = load_profile()
    reg = build_registry()
    results = []
    for i, (name, company, jd) in enumerate(items, 1):
        print(f"[{i}/{len(items)}] {company or name} …", flush=True)
        task = (f"请评估岗位质量并计算匹配度，只调用 assess_job 和 match_job 两个工具，"
                f"不要生成话术。\n【岗位】{company or ''} · {name}\n【JD】\n{jd[:800]}\n【画像】\n{profile[:600]}")
        final, state = run_worker("岗位分析师", task, reg)     # 独立记忆库，不污染用户画像
        score = extract_score(state.trace)
        if score is None:
            print(f"    ⚠️ {name} 未调 match_job（门禁未闭环），分数缺失，建议人工复核")
        meta_path = os.path.join(JDS_DIR, name + ".meta.json")
        try:
            meta = json.load(open(meta_path, encoding="utf-8"))
        except Exception:
            meta = {}
        meta["match_score"] = score
        meta["match_verdict"] = gate_verdict(score)
        json.dump(meta, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        results.append({"岗位": name, "公司": company, "匹配分": score,
                        "裁决": gate_verdict(score)})
        print(f"    → {name} 匹配分 {score} {gate_verdict(score)}")
    results.sort(key=lambda r: -(r["匹配分"] or 0))
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
