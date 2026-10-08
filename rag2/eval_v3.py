# -*- coding: utf-8 -*-
"""RAG v3 评估：四种检索模式跑同一套评估集，量化 Recall@k / MRR / 拒答 / 延迟

和 v2 评估（eval_rag2.py）的区别：
  v2 用 "source 包含 + 关键词出现" 当命中判据，容易被"关键词在别的块里也出现"污染；
  v3 的评估集每条都绑定**生成它的那个块 id**，命中就是命中，可复现、可追责。

用法：
    python eval_v3.py                    # 跑全部四种模式
    python eval_v3.py --modes full       # 只跑某一种
    python eval_v3.py --limit 10         # 先小样本试跑
产物：eval/report_v3.md
"""
import argparse
import json
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from engine import get_engine
from qa import ask_deepseek
from retriever_v3 import ALL_MODES, RetrieverV3, should_refuse

EVAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval")
EVAL_PATH = os.path.join(EVAL_DIR, "eval_v3.jsonl")
REPORT_PATH = os.path.join(EVAL_DIR, "report_v3.md")
TOP_K = 5


def load_eval():
    with open(EVAL_PATH, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def run_mode(retriever, items, mode, gate=None):
    ans = [it for it in items if it["kind"] == "answerable"]
    # 负例分两档：easy = 明显跨领域；hard = 提到库内术语但答案不在库里
    no = [it for it in items if it["kind"] == "no_answer" and not it.get("hard")]
    hard = [it for it in items if it.get("hard")]
    stats = {"recall1": 0, "recall3": 0, "recall5": 0, "mrr": 0.0,
             "refuse_ok": 0, "false_refuse": 0, "lat": [], "cands": [],
             "hard_ok": 0}
    misses = []
    for it in ans:
        t0 = time.time()
        res = retriever.retrieve(it["q"], top_k=TOP_K, mode=mode)
        stats["lat"].append((time.time() - t0) * 1000)
        stats["cands"].append(res.get("candidates", 0))
        ids = [h["id"] for h in res["hits"]]
        pos = ids.index(it["chunk_id"]) + 1 if it["chunk_id"] in ids else 0
        if pos == 1:
            stats["recall1"] += 1
        if 0 < pos <= 3:
            stats["recall3"] += 1
        if 0 < pos <= TOP_K:
            stats["recall5"] += 1
            stats["mrr"] += 1.0 / pos
        else:
            misses.append((it["q"], it["source"]))
        refuse, _why = should_refuse(res, it["q"])
        if not refuse and gate is not None:
            ok, _ev, _miss = gate(it["q"], res["hits"])
            refuse = not ok
        if refuse:
            stats["false_refuse"] += 1
    for it in no:
        res = retriever.retrieve(it["q"], top_k=TOP_K, mode=mode)
        refuse, _why = should_refuse(res, it["q"])
        if not refuse and gate is not None:
            ok, _ev, _miss = gate(it["q"], res["hits"])
            refuse = not ok
        if refuse:
            stats["refuse_ok"] += 1
    for it in hard:
        res = retriever.retrieve(it["q"], top_k=TOP_K, mode=mode)
        refuse, _why = should_refuse(res, it["q"])
        if not refuse and gate is not None:
            ok, _ev, _miss = gate(it["q"], res["hits"])
            refuse = not ok
        if refuse:
            stats["hard_ok"] += 1
    return stats, misses


def pct(a, b):
    return (100.0 * a / b) if b else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", default=",".join(ALL_MODES))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--selfcheck", action="store_true",
                    help="拒答判定再加一道「答案级自检」（多一次 LLM 调用）")
    args = ap.parse_args()

    items = load_eval()
    if args.limit:
        keep = [it for it in items if it["kind"] == "no_answer"][:2]
        keep += [it for it in items if it["kind"] == "answerable"][:args.limit]
        items = keep
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    engine = get_engine()
    api_key = config.get_api_key()

    def ask(prompt):
        return ask_deepseek(prompt, [{"source": "", "text": ""}], api_key)

    retriever = RetrieverV3(engine.store, engine.embedder, ask_model=ask)
    gate = None
    if args.selfcheck:
        import selfcheck as _sc
        gate = lambda q, hits: _sc.assess(q, hits, ask)   # noqa: E731
    n_ans = sum(1 for it in items if it["kind"] == "answerable")
    hard = [it for it in items if it.get("hard")]
    n_no = sum(1 for it in items if it["kind"] == "no_answer" and not it.get("hard"))
    print("评估集：%d 条（可回答 %d + 拒答 %d）| 索引块数 %d | top_k=%d"
          % (len(items), n_ans, n_no, engine.store.count(), TOP_K))

    rows, all_misses = [], {}
    for mode in modes:
        t0 = time.time()
        st, misses = run_mode(retriever, items, mode, gate=gate)
        all_misses[mode] = misses
        lat = st["lat"] or [0]
        row = {
            "mode": mode,
            "R@1": pct(st["recall1"], n_ans),
            "R@3": pct(st["recall3"], n_ans),
            "R@5": pct(st["recall5"], n_ans),
            "MRR": st["mrr"] / n_ans if n_ans else 0,
            "拒答准确": pct(st["refuse_ok"], n_no),
            "难负例拒答": pct(st["hard_ok"], len(hard)),
            "误拒": pct(st["false_refuse"], n_ans),
            "P50延迟ms": round(statistics.median(lat), 0),
            "P95延迟ms": round(sorted(lat)[int(len(lat) * 0.95) - 1], 0),
            "候选数": round(statistics.mean(st["cands"]), 1) if st["cands"] else 0,
            "耗时s": round(time.time() - t0, 1),
        }
        rows.append(row)
        print("%-14s R@1=%.0f%% R@3=%.0f%% R@5=%.0f%% MRR=%.3f "
              "拒答=%.0f%%(难负例%.0f%%) 误拒=%.0f%% P95=%.0fms"
              % (mode, row["R@1"], row["R@3"], row["R@5"], row["MRR"],
                 row["拒答准确"], row["难负例拒答"], row["误拒"],
                 row["P95延迟ms"]))

    # ---------- 写报告 ----------
    os.makedirs(EVAL_DIR, exist_ok=True)
    lines = ["# RAG v3 检索评估报告", "",
             "> 自动生成（`rag2/eval_v3.py`）。评估集 `eval_v3.jsonl`："
             "%d 条可回答问题（每条绑定 ground-truth 块 id）+ %d 条库外问题"
             "（%d 条明显跨领域 + %d 条难负例，测拒答）。"
             % (n_ans, n_no + len(hard), n_no, len(hard)),
             "> 索引：%d 块 / %d 篇资料。命中判据 = 期望块出现在 top-k（不靠关键词猜）。"
             % (engine.store.count(), len(set(it["source"] for it in items if it["source"]))),
             "",
             "| 模式 | R@1 | R@3 | R@5 | MRR | 拒答准确 | 难负例拒答 | 误拒 | P50 延迟 | P95 延迟 | 候选块 |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| `%s` | %.0f%% | %.0f%% | %.0f%% | %.3f | %.0f%% | %.0f%% | %.0f%% "
                     "| %.0fms | %.0fms | %.1f |"
                     % (r["mode"], r["R@1"], r["R@3"], r["R@5"], r["MRR"],
                        r["拒答准确"], r["难负例拒答"], r["误拒"],
                        r["P50延迟ms"], r["P95延迟ms"], r["候选数"]))
    lines += ["", "## 结论（脚本自动填的原始数据，人话解读自己写）", ""]
    if len(rows) >= 2:
        base = rows[0]
        for r in rows[1:]:
            lines.append("- `%s` 相对 `%s`：R@5 %+.0f 个点，MRR %+.3f，"
                         "P95 延迟 %+.0fms"
                         % (r["mode"], base["mode"], r["R@5"] - base["R@5"],
                            r["MRR"] - base["MRR"],
                            r["P95延迟ms"] - base["P95延迟ms"]))
    for mode, misses in all_misses.items():
        if not misses:
            continue
        lines += ["", "### `%s` 没命中的问题（%d 条，用于下一步定位）" % (mode, len(misses))]
        for q, src in misses[:12]:
            lines.append("- [%s] %s" % (os.path.basename(src), q))
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n报告已写入：%s" % REPORT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
