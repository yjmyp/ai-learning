# -*- coding: utf-8 -*-
"""用评估集校准"拒答阈值"——而不是拍脑袋定一个 0.28

做法：
  1. 对评估集里两类问题（库内可回答 / 库外无答案）各跑一遍检索
  2. 抽出 top-1 的几个可解释特征：向量余弦、词面覆盖率、短语命中、RRF 分
  3. 打印两类特征的分布（这一步就能看出哪个特征真的有区分度）
  4. 在候选阈值上网格搜索，选"拒答准确率 - 误拒率"最大的那个点

产出：eval/refusal_calibration.md + 控制台推荐的阈值
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import get_engine
from rerank_v3 import coverage
from retriever_v3 import RetrieverV3

EVAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval")
EVAL_PATH = os.path.join(EVAL_DIR, "eval_v3.jsonl")
OUT_PATH = os.path.join(EVAL_DIR, "refusal_calibration.md")


def feats(retriever, question):
    res = retriever.retrieve(question, top_k=3, mode="hybrid_rerank")
    hits = res["hits"]
    if not hits:
        return {"vec": 0, "cov": 0, "rrf": 0, "rerank": 0}
    top = hits[0]
    return {
        "vec": float(top.get("vector_score") or 0),
        "cov": coverage(question, top.get("text", "")),
        "rrf": float(top.get("rrf_score") or 0),
        "rerank": float(top.get("rerank_score") or 0),
    }


def stat(vals):
    if not vals:
        return (0, 0, 0)
    return (min(vals), sum(vals) / len(vals), max(vals))


def main():
    with open(EVAL_PATH, encoding="utf-8") as f:
        items = [json.loads(l) for l in f if l.strip()]
    engine = get_engine()
    r = RetrieverV3(engine.store, engine.embedder, ask_model=None)

    ans = [it for it in items if it["kind"] == "answerable"]
    no = [it for it in items if it["kind"] == "no_answer"]
    print("采样：库内 %d 条 / 库外 %d 条" % (len(ans), len(no)))

    A = [feats(r, it["q"]) for it in ans]
    N = [feats(r, it["q"]) for it in no]

    lines = ["# 拒答阈值校准（脚本自动生成）", "",
             "| 类别 | 特征 | 最小 | 均值 | 最大 |", "|---|---|---|---|---|"]
    for name, group in (("库内可回答", A), ("库外无答案", N)):
        for key in ("vec", "cov", "rrf", "rerank"):
            lo, mid, hi = stat([g[key] for g in group])
            lines.append("| %s | %s | %.3f | %.3f | %.3f |"
                         % (name, key, lo, mid, hi))
            print("%-6s %-7s min=%.3f 均值=%.3f max=%.3f" % (name, key, lo, mid, hi))

    # 网格搜索：哪个 (特征, 阈值) 让"拒答对的 - 误拒的"最大
    best = None
    for key in ("vec", "cov", "rerank", "rrf"):
        grid = [i / 100 for i in range(1, 100)]
        for th in grid:
            refuse_ok = sum(1 for g in N if g[key] < th)
            false_ref = sum(1 for g in A if g[key] < th)
            score = refuse_ok / max(len(N), 1) - false_ref / max(len(A), 1)
            if best is None or score > best[0]:
                best = (score, key, th, refuse_ok / max(len(N), 1),
                        false_ref / max(len(A), 1))
    score, key, th, acc, fpr = best
    print("\n最佳单特征阈值：%s < %.2f  →  拒答准确率 %.0f%%，误拒 %.0f%%（净收益 %.2f）"
          % (key, th, acc * 100, fpr * 100, score))
    lines += ["", "## 网格搜索结果", "",
              "单特征最优：`%s < %.2f` → 拒答准确率 **%.0f%%**，误拒 **%.0f%%**，"
              "净收益 %.2f" % (key, th, acc * 100, fpr * 100, score), ""]

    # 组合规则：向量余弦低 **且** 词面覆盖低 → 更保守、误拒更少
    combos = [(0.35, 0.25), (0.40, 0.30), (0.45, 0.30), (0.40, 0.40), (0.45, 0.40)]
    lines += ["| 组合规则 | 拒答准确率 | 误拒率 | 净收益 |", "|---|---|---|---|"]
    best_combo = None
    for vth, cth in combos:
        ok = sum(1 for g in N if g["vec"] < vth or g["cov"] < cth)
        fr = sum(1 for g in A if g["vec"] < vth or g["cov"] < cth)
        net = ok / max(len(N), 1) - fr / max(len(A), 1)
        lines.append("| vec<%.2f 或 cov<%.2f | %.0f%% | %.0f%% | %.2f |"
                     % (vth, cth, ok / max(len(N), 1) * 100,
                        fr / max(len(A), 1) * 100, net))
        if best_combo is None or net > best_combo[0]:
            best_combo = (net, vth, cth)
    net, vth, cth = best_combo
    lines += ["", "组合最优：**vec<%.2f 或 cov<%.2f → 拒答**，净收益 %.2f" % (vth, cth, net), ""]
    print("组合最优：vec<%.2f 或 cov<%.2f → 净收益 %.2f" % (vth, cth, net))

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("写出：", OUT_PATH)


if __name__ == "__main__":
    main()
