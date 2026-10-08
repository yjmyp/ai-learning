# -*- coding: utf-8 -*-
"""匹配打分一致性评估：证明"结构化打分"比"模型随口给分"稳

做法：同一批岗位，两种方法各跑 N 次
  · 旧法 = 直接让模型输出「匹配度 NN%」（当前线上用法）
  · 新法 = match_score.score_job（本地五维加权，无模型参与）
比较每个岗位的**均值与标准差**：标准差越小 = 越可复现 = 越能拿来做投递决策与回归测试。

用法：
    python eval_match_consistency.py                 # 默认 4 个岗位 × 5 次
    python eval_match_consistency.py --jobs 6 --runs 3
产物：offeragent/docs/match_consistency.md
"""
import argparse
import json
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "offeragent"))

import match_score as ms
from offer_agent_tools import _ask_model          # 复用引擎里的模型调用
from prompts import PROMPT_MATCH

OUT_PATH = os.path.join(HERE, "offeragent", "docs", "match_consistency.md")


def old_method_score(profile, jd):
    """旧法：让模型直接给一个匹配度百分比（现在线上就是这么干的）。"""
    import re
    report = _ask_model(PROMPT_MATCH, profile, jd[:6000])
    m = re.search(r"匹配度[:：]?\s*(\d{1,3})\s*%", report or "")
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--runs", type=int, default=5)
    args = ap.parse_args()

    profile = ms.profile_text()
    jobs = [j for j in ms.load_jobs() if j[2].strip()][:args.jobs]
    if not jobs:
        raise SystemExit("岗位库为空")

    rows = []
    for name, meta, jd in jobs:
        old, new = [], []
        print("评估：", name[:40])
        for i in range(args.runs):
            try:
                s = old_method_score(profile, jd)
            except Exception:
                s = None
            if s is not None:
                old.append(s)
            new.append(ms.score_job(profile, jd, meta, name=name)["score"])
            time.sleep(0.3)
        rows.append({"name": name, "old": old, "new": new})
        print("   旧法", old, "→ 均值 %.1f 标准差 %.2f"
              % (statistics.mean(old) if old else 0,
                 statistics.pstdev(old) if len(old) > 1 else 0))
        print("   新法", new, "→ 均值 %.1f 标准差 %.2f"
              % (statistics.mean(new), statistics.pstdev(new)))

    def agg(key):
        vals = [statistics.pstdev(r[key]) for r in rows if len(r[key]) > 1]
        means = [statistics.mean(r[key]) for r in rows if r[key]]
        return (statistics.mean(vals) if vals else 0,
                statistics.mean(means) if means else 0)

    old_std, old_mean = agg("old")
    new_std, new_mean = agg("new")
    lines = ["# 匹配打分一致性评估（脚本自动生成）", "",
             "> 同一批岗位、同一份画像，两种打分方法各跑 %d 次。"
             "「标准差」= 同一个岗位重复打分的波动，越小越可信。" % args.runs,
             "",
             "| 岗位 | 旧法（模型直接给分） | 旧法均值 | 旧法标准差 | 新法（结构化） | 新法均值 | 新法标准差 |",
             "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| %s | %s | %.1f | %.2f | %s | %.1f | %.2f |" % (
            r["name"][:36], r["old"], statistics.mean(r["old"]) if r["old"] else 0,
            statistics.pstdev(r["old"]) if len(r["old"]) > 1 else 0,
            r["new"], statistics.mean(r["new"]),
            statistics.pstdev(r["new"]) if len(r["new"]) > 1 else 0))
    lines += ["",
              "**汇总：旧法平均标准差 %.2f，新法平均标准差 %.2f**" % (old_std, new_std),
              "",
              "结论：结构化打分把同一岗位的重复打分波动从 "
              "%.2f 分降到 %.2f 分——**同样的输入永远得到同一个分数**，"
              "所以它能当投递决策依据，也能拿来做回归测试（换提示词/换模型不影响历史分数）。"
              % (old_std, new_std),
              "",
              "## 维度拆解（新法可解释性）", "",
              "新法把分数拆成五维并给出证据：硬技能 0.30 / 项目证据 0.25 / 地点 0.15 / "
              "时间 0.15 / 门槛 0.15；门槛里单独处理「硕士」「2028 届」「方向偏算法」这类硬冲突。",
              "示例（取一个岗位）："]
    name, meta, jd = jobs[0]
    demo = ms.score_job(profile, jd, meta, name=name)
    lines.append("")
    lines.append("**%s → %d 分（%s）**" % (name[:40], demo["score"], demo["verdict"]))
    for d in demo["dims"]:
        lines.append("- %s（权重 %.2f）= %d：%s" % (d["label"], d["weight"],
                                                   d["score"], d["evidence"]))
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print()
    print("旧法平均标准差 = %.2f ｜ 新法平均标准差 = %.2f" % (old_std, new_std))
    print("报告：", OUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
