# -*- coding: utf-8 -*-
"""Agent 运行记录（trace 可视化）

把 data/agent_logs.jsonl 从"一行行 JSON"变成能看懂的东西：
  · 顶部四个指标：运行次数 / 平均步数 / 工具调用总数 / 待确认投递
  · 工具调用分布：哪个工具被调得多、哪个从没被调过（能发现"死工具"）
  · 每次运行一条时间线：第几步、调了什么工具、参数摘要、结果，最后是模型总结

为什么单独做一页：Agent 的可观测性是招聘方最看重的一层——
  能说清"每一步发生了什么、错在哪一步"，比多写一个功能有价值。
"""
import json
from collections import Counter

import streamlit as st

from store import DATA_DIR, read_text
from ui_kit import hero

LOG_PATH = DATA_DIR / "agent_logs.jsonl"


def load_agent_logs():
    txt = read_text(LOG_PATH, "")
    rows = []
    for line in txt.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _arg_brief(args, limit=70):
    if not isinstance(args, dict):
        return str(args)[:limit]
    parts = []
    for k, v in args.items():
        s = str(v).replace("\n", " ")
        parts.append("%s=%s" % (k, s[:40]))
    return "；".join(parts)[:limit]


def page_agent_trace():
    hero("Agent 运行记录", "每次 Agent 跑完都落一条 JSONL：步骤 → 工具 → 结果，可复盘可统计")
    rows = load_agent_logs()
    if not rows:
        st.info("还没有运行记录。去「找工作 → 岗位库」的岗位卡片跑一次 Agent，"
                "或者用「批量打分」跑一批，就会出现在这里。")
        return

    steps_all = [len(r.get("trace") or []) for r in rows]
    tools = Counter(t.get("tool") for r in rows for t in (r.get("trace") or [])
                    if t.get("tool"))
    pending = sum(1 for r in rows if not r.get("confirmed"))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("运行次数", len(rows))
    c2.metric("平均步数", round(sum(steps_all) / len(steps_all), 1))
    c3.metric("工具调用总数", sum(tools.values()))
    c4.metric("待确认投递", pending)

    g1, g2 = st.columns([2, 1])
    with g1:
        st.markdown("##### 工具调用分布（哪些工具真在被用）")
        if tools:
            st.bar_chart({"调用次数": dict(tools.most_common())})
        else:
            st.caption("没有工具调用记录")
    with g2:
        st.markdown("##### 工具覆盖率")
        st.caption("被调过 %d 种工具；分布集中在少数几个工具，说明其余工具"
                   "暂时没被任务用到——这是判断「工具集是否臃肿」的依据。" % len(tools))
        st.metric("平均每次步数", round(sum(steps_all) / len(steps_all), 1),
                  help="步数突然变多通常意味着任务变复杂或模型绕路")

    st.markdown("##### 每次运行的时间线")
    for r in list(reversed(rows))[:10]:
        title = "%s · %s · %d 步 · 匹配分 %s" % (
            r.get("time", "")[:16], r.get("company") or r.get("job") or "未知",
            len(r.get("trace") or []), r.get("match_score"))
        with st.expander(title):
            st.markdown("**结果**：" + (r.get("final") or "")[:400])
            st.caption("裁决：%s ｜ tokens：%s ｜ 已确认投递：%s"
                       % (r.get("verdict"), r.get("tokens"), bool(r.get("confirmed"))))
            for i, t in enumerate(r.get("trace") or [], start=1):
                st.markdown("`%02d` **%s**　%s" % (i, t.get("tool") or t.get("step"),
                                                  _arg_brief(t.get("args"))))
