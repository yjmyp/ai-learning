# -*- coding: utf-8 -*-
"""
pages_home_pro.py · 产品级首页 v3（2026-10-19 重构）
=====================================================
和 v2 的区别：
  1. 去掉「同一组数字出现 3 次」的问题：Hero 只负责情绪 + 一张目标环，
     统计只出现一次（KPI 条），漏斗只出现一次（右栏）。
  2. 「现在做这一件事」压成一张深色行动卡，一屏内只有一个主张。
  3. 快捷入口改成真正可点的 st.page_link，不再是点了没反应的 div。
"""
import json

import streamlit as st

import apply_assist
from store import list_jobs, read_text, ensure_dirs, CONFIG_PATH
from ui_kit import PAGES, onboarding_panel
from theme_pro import _flat, hero, section_title


def _kpi(value, label, highlight=False):
    cls = "oa-kpi oa-kpi-hl" if highlight else "oa-kpi"
    return f'<div class="{cls}"><div class="oa-kpi-n">{value}</div><div class="oa-kpi-l">{label}</div></div>'




def _co(meta, fallback="公司未标注"):
    """公司名兜底：抓 JD 失败会留下 company#308034 这种脏值，别摆给 HR 看。"""
    import re as _re
    name = (meta or {}).get("company") or ""
    if not name or _re.fullmatch(r"company#\d+", str(name)):
        return fallback
    return str(name)


def _plink(key, label, icon=None, stretch=True):
    """页面跳转：优先用 st.Page 对象（url_path 字符串在这里不合法）。"""
    page = PAGES.get(key)
    if page is None:
        return
    st.page_link(page, label=label, icon=icon, width="stretch" if stretch else "content")


def page_home_pro():
    """产品级首页 v3。"""
    ensure_dirs()

    all_jobs = list_jobs()
    total = len(all_jobs)
    pending = sum(1 for _, m, _ in all_jobs if m.get("status") == "待投")
    applied = sum(1 for _, m, _ in all_jobs if m.get("status") == "已投")
    replied = sum(1 for _, m, _ in all_jobs if m.get("status") in ("面试中", "Offer"))
    matched = sum(1 for _, m, _ in all_jobs if m.get("match_score"))
    today_applied = apply_assist.applied_today()

    top_pending = sorted(
        [(name, meta) for name, meta, _ in all_jobs
         if meta.get("status") == "待投" and meta.get("match_score")],
        key=lambda x: x[1].get("match_score", 0),
        reverse=True,
    )[:5]

    try:
        cfg = json.loads(read_text(CONFIG_PATH, "{}"))
        daily_target = int(cfg.get("daily_target", 3) or 3)
    except Exception:
        daily_target = 3

    onboarding_panel()

    # ── Hero ──────────────────────────────────────────────
    left_n = max(0, daily_target - today_applied)
    pct = int(round(min(100, today_applied / max(1, daily_target) * 100)))
    foot = ("还差 <b>%d</b> 家达标" % left_n) if left_n else "<b>今日目标已达成</b>"
    visual = (
        '<div class="hv-card">'
        '<div class="hv-card-head"><span class="hv-dot"></span><span class="hv-dot"></span>'
        '<span class="hv-dot"></span><span class="hv-card-title">今日投递</span></div>'
        + '<div class="hv-ring" style="--pct:%d">' % pct
        + '<div class="hv-ring-inner"><b>%d</b><span>/%d</span></div></div>'
        % (today_applied, daily_target)
        + '<div class="hv-card-foot">' + foot + '</div></div>'
    )
    hero(
        "让求职变成一件专业的事",
        "AI 驱动的求职智能体：画像、匹配、话术、复盘一条线。不再瞎投，每一家都有策略。",
        stats=None,
        label="OfferAgent Pro",
        visual=visual,
    )

    # KPI 条：全页唯一一处统计
    st.markdown(
        _flat('<div class="oa-kpi-strip" style="margin:-6px 4px 18px">'
              + _kpi(total, "岗位在库")
              + _kpi(matched, "已完成匹配")
              + _kpi(pending, "待投递", highlight=True)
              + _kpi(f"{applied} / {replied}", "已投 / 有回应")
              + "</div>"),
        unsafe_allow_html=True,
    )

    # ── 现在做这一件事 ────────────────────────────────────
    if top_pending:
        name, meta = top_pending[0]
        cta_title = f"投最高匹配：{_co(meta)} · {name}"
        cta_desc = f"匹配度 {meta.get('match_score', 0)}% · 先生成话术，再看一眼 JD 再发"
        cta_right = "现在开始 →"
        cta_page = "apply"
        cta_ico = "🎯"
    elif pending:
        cta_title = f"给 {pending} 个待投岗位跑一遍匹配"
        cta_desc = "先有分数再决定投不投，比海投省时间"
        cta_right = "现在开始 →"
        cta_page = "match"
        cta_ico = "📊"
    else:
        cta_title = "先去搜一批岗位"
        cta_desc = "多平台一键搜岗、自动去重、抓 JD"
        cta_right = "现在开始 →"
        cta_page = "jobs"
        cta_ico = "🔎"

    n1, n2 = st.columns([4.2, 1.1], vertical_alignment="center")
    with n1:
        st.markdown(
            _flat(f'<div class="oa-next"><div class="oa-next-ico">{cta_ico}</div>'
                  f'<div><div class="oa-next-t">{cta_title}</div>'
                  f'<div class="oa-next-d">{cta_desc}</div></div></div>'),
            unsafe_allow_html=True,
        )
    with n2:
        _plink(cta_page, "开始", ":material/arrow_forward:")

    # ── 今日行动 ──────────────────────────────────────────
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    section_title("今日行动", f"目标 {daily_target} 家 · 已完成 {today_applied}")

    actions = []
    if top_pending:
        name, meta = top_pending[0]
        actions.append(("🎯", f"投递：{_co(meta)}",
                        f"匹配度 {meta.get('match_score', 0)}%，话术已可生成", "apply", "去投递"))
    actions.append(("🔎", f"补充 {pending} 个待投岗位的匹配分",
                    "有分数才能排序，别按感觉投", "match", "去匹配"))
    actions.append(("📄", "按目标岗位做一次 ATS 覆盖检查",
                    "关键词覆盖率会直接影响初筛", "resume", "去检查"))
    if replied == 0 and applied > 0:
        actions.append(("📞", f"跟进已投的 {applied} 家",
                        "7 天没回应就该主动问一次", "records", "去跟进"))

    for icon, title, desc, page, btn in actions:
        c1, c2 = st.columns([6, 1], vertical_alignment="center")
        with c1:
            st.markdown(
                _flat(f'<div style="display:flex;gap:12px;align-items:center;padding:9px 2px">'
                      f'<div style="width:34px;height:34px;border-radius:10px;flex:0 0 auto;'
                      f'display:flex;align-items:center;justify-content:center;font-size:16px;'
                      f'background:linear-gradient(180deg,#F4F5FF,#ECEEFF);'
                      f'border:1px solid #E3E6FA">{icon}</div>'
                      f'<div><div style="font-size:13.5px;font-weight:640;color:#141B33">{title}</div>'
                      f'<div style="font-size:12px;color:#78829A;margin-top:2px">{desc}</div></div></div>'),
                unsafe_allow_html=True,
            )
        with c2:
            _plink(page, btn)

    # ── 岗位 + 漏斗 ───────────────────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    c_left, c_right = st.columns([1.5, 1], gap="large")

    with c_left:
        section_title("最值得投的岗位", "按匹配度")
        if top_pending:
            from theme_pro import list_item
            rows = '<div class="p-card" style="padding:8px 20px">'
            for name, meta in top_pending:
                score = meta.get("match_score", 0)
                variant = "success" if score >= 75 else ("primary" if score >= 60 else "warning")
                sub = _co(meta) + (
                    " · " + meta["source"] if meta.get("source") else "")
                rows += list_item("💼", name, sub, right_tag=(f"{score}%", variant))
            rows += "</div>"
            st.markdown(_flat(rows), unsafe_allow_html=True)
            _plink("jobs", "查看全部岗位", ":material/arrow_forward:", stretch=False)
        else:
            st.markdown(_flat(
                '<div class="p-card" style="text-align:center;padding:40px 20px">'
                '<div style="font-size:38px;margin-bottom:10px">📭</div>'
                '<div style="font-weight:650;color:#1A2140;font-size:14.5px">还没有待投岗位</div>'
                '<div style="font-size:12.5px;color:#78829A;margin-top:4px">'
                '先去搜岗，抓一批 JD 回来</div></div>'),
                unsafe_allow_html=True)
            _plink("jobs", "去搜岗", ":material/search:", stretch=False)

    with c_right:
        section_title("求职漏斗", "全流程")
        funnel = [
            ("岗位库", total),
            ("已匹配", matched),
            ("待投", pending),
            ("已投", applied),
            ("有回应", replied),
        ]
        rows = '<div class="p-card" style="padding:16px 18px">'
        for label, num in funnel:
            width = 0 if not num else max(6, min(100, num / max(1, total) * 100))
            rows += (f'<div class="oa-funnel-row"><div class="oa-funnel-l">{label}</div>'
                     f'<div class="oa-funnel-bar"><div class="oa-funnel-fill" '
                     f'style="width:{width:.1f}%"></div></div>'
                     f'<div class="oa-funnel-n">{num}</div></div>')
        rows += '</div>'
        st.markdown(_flat(rows), unsafe_allow_html=True)
        st.caption("从「有回应」往回看，卡在哪一步就补哪一步。")


__all__ = ["page_home_pro"]
