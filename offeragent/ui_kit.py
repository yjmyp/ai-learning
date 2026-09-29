# -*- coding: utf-8 -*-
"""
ui_kit.py —— OfferAgent 渲染层（2026-09-29 从 offer_agent_app.py 抽出）
============================================================================
纯展示辅助：页头/标签/仪表盘图形/岗位档案/报告卡片/下一步提示。
依赖 streamlit + plotly，被页面函数 import。
"""
import re

import plotly.graph_objects as go
import streamlit as st

import job_detail
import job_quality
import theme

from store import MATCH_DIR, read_text, save_meta


def score_color(score):
    if score >= 75:
        return "#0F766E"
    if score >= 60:
        return "#2563EB"
    if score >= 45:
        return "#D97706"
    return "#B91C1C"


def score_gauge(score: int):
    color = score_color(score)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "%", "font": {"size": 44, "color": color, "family": "Arial Black"}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#CBD5E1"},
                "bar": {"color": color, "thickness": 0.28},
                "bgcolor": "#F1F5F9",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 45], "color": "#FEE2E2"},
                    {"range": [45, 60], "color": "#FEF3C7"},
                    {"range": [60, 75], "color": "#DBEAFE"},
                    {"range": [75, 100], "color": "#D1FAE5"},
                ],
            },
        )
    )
    fig.update_layout(height=240, margin=dict(l=20, r=20, t=10, b=10))
    return fig


def dim_radar(dims: dict):
    names = list(dims.keys())
    values = list(dims.values())
    fig = go.Figure(
        go.Scatterpolar(
            r=values + values[:1],
            theta=names + names[:1],
            fill="toself",
            line=dict(color="#2563EB", width=2),
            fillcolor="rgba(37,99,235,0.25)",
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10))),
        height=280,
        margin=dict(l=30, r=30, t=10, b=10),
        showlegend=False,
    )
    return fig


def rank_bar(jobs):
    rows = [(m["name"], m["match_score"] or 0) for _, m, _ in jobs
            if m["status"] != "排除" and m["match_score"] is not None]
    if not rows:
        return None
    rows.sort(key=lambda x: x[1])
    names = [r[0] for r in rows]
    scores = [r[1] for r in rows]
    colors = [score_color(s) for s in scores]
    fig = go.Figure(go.Bar(
        x=scores, y=names, orientation="h",
        marker=dict(color=colors),
        text=[f"{s}%" for s in scores], textposition="outside",
    ))
    fig.update_layout(
        xaxis=dict(range=[0, 105], title="匹配度", tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=12)),
        height=max(220, len(names) * 42),
        margin=dict(l=10, r=50, t=10, b=10),
        bargap=0.35,
    )
    return fig


def inject_css(variant: str = None):
    """样式统一在 theme.py 维护。三套主题：A 默认 / B Linear / C Stripe。"""
    st.markdown(theme.get_css(variant), unsafe_allow_html=True)


def hero(title, subtitle, sub2=""):
    """紧凑页头：标题 + 一行说明。不再用大块渐变，保持求职场合的克制。"""
    sub = subtitle or ""
    if sub2:
        sub = f"{sub}　|　{sub2}" if sub else sub2
    st.markdown(
        f'<div class="oa-head"><div class="oa-head-title">{title}</div>'
        f'<div class="oa-head-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def status_tag(status: str):
    m = {"待投": ("oa-tag-blue", "待投"), "已投": ("oa-tag-green", "已投"),
         "排除": ("oa-tag-red", "排除")}
    cls, label = m.get(status, ("oa-tag-amber", status))
    return f'<span class="oa-tag {cls}">{label}</span>'


def render_job_detail(name: str, meta: dict, jd: str):
    """岗位档案：为什么在列表里 + 为什么保留/排除 + 这个岗位要什么人。"""
    head = f"**{meta.get('company') or name}** · {meta.get('city') or '城市未填'}"
    if meta.get("salary"):
        head += f" · 薪资 {meta['salary']}"
    st.markdown(head)

    st.markdown("**① 它是怎么进到列表里的**")
    for r in job_detail.entry_reasons(meta):
        st.markdown(f"- {r['label']}：{r['detail']}")

    st.markdown("**② 为什么保留 / 为什么排除**")
    for r in job_detail.keep_or_drop(meta):
        icon = "✅" if r.get("ok") else ("❔" if r.get("ok") is None else "⛔")
        st.markdown(f"- {icon} {r['label']}：{r['detail']}")

    parts = job_detail.split_jd(jd)
    st.markdown("**③ 这个岗位要什么人**")
    if parts["duty"]:
        st.markdown("岗位职责：")
        st.markdown(parts["duty"][:1200])
    if parts["req"]:
        st.markdown("任职要求：")
        st.markdown(parts["req"][:1200])
    if not parts["duty"] and not parts["req"]:
        st.caption("这份 JD 没有明显的「职责 / 要求」分段，下面是原文：")
        st.text((parts["other"] or jd)[:1200])
    elif parts["other"].strip():
        with st.expander("其他信息 / 原文剩余部分"):
            st.text(parts["other"][:1200])

    report = read_text(MATCH_DIR / f"match_{name}.md")
    if report:
        m = re.search(r"## 结论\s*\n+(.+)", report)
        if m:
            st.markdown("**④ 匹配结论**")
            st.markdown(m.group(1).strip())

    if not isinstance(meta.get("quality"), dict):
        st.caption("这个岗位还没有质量检查结果（早期入库的岗位没有这项）")
    if st.button("🔄 跑一次质量检查并保存", key=f"qc_{name}"):
        meta["quality"] = job_quality.assess({
            "jd": jd, "company": meta.get("company", ""),
            "city": meta.get("city", ""), "salary": meta.get("salary", ""),
            "url": meta.get("source_url", ""),
        })
        save_meta(name, meta)
        st.success("质量检查已保存，刷新后能在上面看到逐项依据")
        st.rerun()


def render_section_cards(sections: dict):
    """把解析后的报告渲染成彩色卡片组（比 markdown 好看）"""
    style_map = {
        "匹配点": ("✅ 匹配点", "#0F766E", "#D1FAE5"),
        "差距": ("📌 差距", "#1D4ED8", "#DBEAFE"),
        "短板与风险": ("⚠️ 短板与风险", "#B45309", "#FEF3C7"),
        "结论": ("🎯 结论", "#1E293B", "#E2E8F0"),
    }
    for key in ("匹配点", "差距", "短板与风险", "结论"):
        items = sections.get(key) or sections.get("短板") or []
        if not items:
            continue
        label, color, bg = style_map.get(key, (key, "#334155", "#F1F5F9"))
        lis = "".join(
            f'<div style="padding:4px 0;font-size:14px;line-height:1.6">{"• " + it}</div>'
            for it in items if it
        )
        st.markdown(
            f'<div style="background:{bg};border:1px solid {color}33;'
            f'border-radius:12px;padding:12px 16px;margin-bottom:10px">'
            f'<div style="color:{color};font-weight:700;font-size:14px;margin-bottom:4px">{label}</div>'
            f'{lis}</div>',
            unsafe_allow_html=True,
        )


NEXT_HINTS = {
    "saved_job": "下一步：去「匹配分析」跑一次匹配，看这个岗位值不值得投。",
    "matched": "下一步：在同一个岗位卡片里点「ATS 检查」，看简历关键词覆盖够不够。",
    "ats_done": "下一步：生成投递话术，复制后去招聘平台发送。",
    "talk_done": "下一步：把话术发出去，然后回来点「标记已投」；7 天后没动静会自动进跟进提醒。",
    "applied": "下一步：等消息。有回信就粘到「投递记录 → 邮件识别」里判断怎么改状态。",
    "profile_done": "下一步：去「岗位」搜一次岗，勾选入库后跑匹配。",
    "resume_saved": "下一步：去「投递 → 简历定制」，选一个目标岗位做 ATS 覆盖检查。",
}


def next_step(key: str, extra: str = "", defer: bool = False):
    """每个动作完成后，明确告诉用户下一步做什么。
    defer=True 用于「紧接着就 st.rerun()」的场景：提示先存起来，重跑完在页面底部显示。"""
    hint = NEXT_HINTS.get(key)
    if not hint:
        return
    text = hint + (("　" + extra) if extra else "")
    if defer:
        st.session_state["_pending_hint"] = text
    else:
        st.info(text)
