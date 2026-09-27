# -*- coding: utf-8 -*-
"""
pipeline · 投递漏斗 / 跟进提醒 / 被拒归因
=========================================
三个能力：
  1. funnel(jobs)           —— 各状态计数 + 转化率（投了多少、有多少面试、多少 offer）
  2. needs_followup(jobs)   —— 投出去超过 N 天没有动静的，该跟进了
  3. analyze_rejections()   —— 连续被拒后，用大模型找出共同点（只基于真实记录，不编）
"""
import time

STATUSES = ["待投", "已投", "面试中", "已拒", "Offer", "排除"]
ACTIVE = ["待投", "已投", "面试中", "已拒", "Offer"]


def funnel(jobs: list) -> dict:
    """jobs 是 list_jobs() 的结果。返回各状态计数和转化率。"""
    counts = {s: 0 for s in STATUSES}
    for _, meta, _ in jobs:
        st = meta.get("status", "待投")
        counts[st] = counts.get(st, 0) + 1

    submitted = counts["已投"] + counts["面试中"] + counts["已拒"] + counts["Offer"]
    interviewed = counts["面试中"] + counts["已拒"] + counts["Offer"]
    offers = counts["Offer"]

    def rate(a, b):
        return round(a / b * 100, 1) if b else 0.0

    return {
        "counts": counts,
        "submitted": submitted,
        "interviewed": interviewed,
        "offers": offers,
        "reply_rate": rate(interviewed, submitted),
        "offer_rate": rate(offers, submitted),
    }


def needs_followup(jobs: list, days: int = 7) -> list:
    """投出去超过 days 天、状态还是「已投」的岗位，该跟进了。"""
    now = time.time()
    out = []
    for name, meta, jd in jobs:
        if meta.get("status") != "已投":
            continue
        stamp = meta.get("applied_at") or meta.get("created_at") or ""
        try:
            t = time.mktime(time.strptime(stamp[:19], "%Y-%m-%d %H:%M:%S"))
        except Exception:
            continue
        d = int((now - t) / 86400)
        if d >= days:
            out.append({"name": name, "meta": meta, "days": d, "jd": jd})
    out.sort(key=lambda x: -x["days"])
    return out


REJECT_PROMPT = """下面是一个学生最近被拒的投递记录（岗位名、公司、匹配度、备注）。

请做两件事，总共不超过 200 字：
1. 共同点：这些被拒的岗位有什么共同特征（行业、岗位类型、要求）？
2. 最可能的三个原因 + 各自的补法（要具体到做什么）

硬性要求：只根据我给的信息推断，推断不出来就写"信息不足，无法判断"。
不要写鼓励的话。不要编造这些岗位的细节。

记录：
"""


def analyze_rejections(rejected: list, ask_model) -> str:
    if not rejected:
        return ""
    body = "\n".join(
        f"- {r.get('job')} | {r.get('company') or '未知公司'} | 匹配度 {r.get('score')}"
        f" | 备注 {r.get('note') or '无'}" for r in rejected)
    return (ask_model(REJECT_PROMPT + body) or "").strip()
