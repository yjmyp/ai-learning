# -*- coding: utf-8 -*-
"""匹配分析与话术 —— OfferAgent 页面域模块（2026-09-29 从 offer_agent_app.py 拆出）"""
import json
import os
import re
import time
from pathlib import Path

import streamlit as st

# 分层公共层 + 业务子模块（宽 import 兜底，页面函数保持原名调用）
from store import *
from prompts import PROMPT_PROFILE, PROMPT_MATCH, PROMPT_HIGHLIGHT, TALK_VARIANTS, generate_talk, check_talk
from jd_fetcher import fetch_jd
from llm import *
from ui_kit import *
import apply_assist
import digital_twin
import distill
import job_sources
import theme
import job_quality
import resume_tailor
import interview_drill
import pipeline
import inbox_parse
import v41
import company_lookup
import job_detail
import doc_io
import resume_builder
import resume_clean
import resume_templates

def render_struct_score(profile, jd, meta, name, model_score=None):
    """结构化匹配分面板：本地五维加权，不依赖模型报告（所以进页面就能看）。"""
    import sys as _sys
    from pathlib import Path as _Path
    _root = str(_Path(__file__).resolve().parent.parent)
    if _root not in _sys.path:
        _sys.path.insert(0, _root)              # match_score.py 在仓库根目录
    try:
        import match_score as _ms
        res = _ms.score_job(profile, jd, meta, name=name)
    except Exception as e:
        st.caption("（结构化打分模块不可用：%s）" % str(e)[:80])
        return
    st.markdown("##### 🧮 结构化匹配分（本地五维加权，同样的输入永远同一个分）")
    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("结构化总分", "%d" % res["score"], help=res["method"])
    c2.metric("模型主观分", ("%s" % model_score) if model_score is not None else "未跑",
              help="模型读报告给的分，只作参考：同一岗位重复跑会波动（实测平均 ±3.31 分）")
    c3.markdown("**裁决**：" + res["verdict"])
    for d in res["dims"]:
        st.markdown(
            '<div style="margin:2px 0;">'
            '<span class="oa-tag oa-tag-blue">%s</span>'
            '<b style="margin:0 6px;">%d</b>'
            '<span style="color:#94A3B8;font-size:12px;">权重 %.2f</span>'
            '　<span style="font-size:12.5px;">%s</span></div>'
            % (d["label"], d["score"], d["weight"], d["evidence"]),
            unsafe_allow_html=True)
    if res["hard_blocks"]:
        st.error("硬门槛冲突：" + "；".join(res["hard_blocks"]) + "　→ 分数再高也别投")
    with st.expander("为什么是这个分（完整证据）"):
        st.markdown("**JD 里识别到的技能词**：" + ("、".join(res["jd_terms"]) or "无"))
        st.markdown("**命中**：" + ("、".join(res["matched"]) or "无"))
        st.markdown("**缺失**：" + ("、".join(res["missing"]) or "无"))
        st.caption("维度权重：硬技能 0.30 / 项目证据 0.25 / 地点 0.15 / 时间 0.15 / 门槛 0.15。"
                   "一致性评估：旧法平均波动 3.31 分，结构化法 0.00 分"
                   "（见 offeragent/docs/match_consistency.md）。")
    if st.button("💾 用结构化分覆盖岗位库里的分数", key="use_struct_" + name[:20]):
        meta["match_score"] = res["score"]
        meta["match_method"] = res["method"]
        meta["match_dims"] = res["dims"]
        meta["match_hard_blocks"] = res["hard_blocks"]
        save_meta(name, meta)
        st.success("已写入 %d 分（结构化）" % res["score"])
        st.rerun()
    st.markdown("---")


def page_match():
    hero("匹配分析", "画像 × JD → 匹配度 + 五维雷达 + 逐条拆解（卡片式）")
    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    if jobs:
        names = [j[0] for j in jobs]
        default_idx = 0
        if st.session_state.get("match_target") in names:
            default_idx = names.index(st.session_state["match_target"])
        name = st.selectbox("选择已有岗位", names, index=default_idx,
                            format_func=lambda n: f"{n}（{dict((j[0], j[1]['match_score']) for j in jobs).get(n, '未匹配')}%）",
                            key="match_pick")
        meta = dict((j[0], j[1]) for j in jobs)[name]
        jd = read_text(JDS_DIR / f"{name}.txt")
    else:
        name, meta, jd = None, {}, ""

    with st.expander("⚡ 快速直配：粘贴新岗位 URL（不保存，直接分析）", expanded=False):
        quick_url = st.text_input("岗位 URL", key="quick_url")
        if st.button("🚀 抓取并直接匹配", key="quick_match"):
            if not quick_url.strip():
                st.warning("请粘贴岗位 URL")
            elif not FETCHER_OK:
                st.error("jd_fetcher 模块未加载")
            else:
                with st.spinner("抓取页面…"):
                    try:
                        fetched = fetch_jd(quick_url.strip())
                        jd = fetched["jd"]
                        name = fetched["name"] + "（URL直配）"
                        st.success(f"抓取成功：{fetched['name']}（{len(jd)} 字）")
                    except Exception as e:
                        st.error(str(e))
                        return

    if not name or not jd:
        st.info("先在岗位库添加岗位，或在上方粘贴 URL 直配")
        return

    with st.expander("查看 JD", expanded=False):
        st.text(jd[:2000])

    profile = read_text(PROFILE_PATH)
    if not profile:
        st.warning("尚未生成画像：请先到「我的画像」页生成")
        if st.button("🧬 立即用 me.txt 素材生成画像"):
            with st.spinner("生成中…"):
                try:
                    profile = ask_chat(PROMPT_PROFILE, read_text(ME_PATH))
                    write_text(PROFILE_PATH, profile)
                    st.success("画像已生成")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        return

    # ---------- 结构化打分（v3：本地五维，可复算、可解释，不依赖模型报告） ----------
    render_struct_score(profile, jd, meta, name)
    cache_key = f"match_{name}.md" if not name.endswith("URL直配") else None
    cached = read_text(MATCH_DIR / cache_key) if cache_key else ""
    if cached:
        st.caption("已显示上次结果，点「重新匹配」可刷新（模型打分有波动，看档次不看绝对值）")
    if st.button("🔍 运行匹配分析", type="primary"):
        with st.spinner(f"正在分析 {name} …（约 20-60 秒）"):
            try:
                report = ask_chat(PROMPT_MATCH, profile, jd)
                if cache_key:
                    write_text(MATCH_DIR / cache_key, report)
                score = extract_score(report)
                if score is not None and not name.endswith("URL直配"):
                    meta["match_score"] = score
                    save_meta(name, meta)
                st.session_state["last_report"] = report
                st.session_state["last_report_name"] = name
                next_step("matched", defer=True)
                st.rerun()
            except Exception as e:
                st.error(str(e))
                return

    report = st.session_state.get("last_report") or (read_text(MATCH_DIR / cache_key) if cache_key else "")
    if not report:
        st.info("尚未运行匹配，点上方按钮开始")
        return

    score = extract_score(report)
    dims = extract_dim_scores(report)
    render_struct_score(profile, jd, meta, name, model_score=score)
    c1, c2 = st.columns([1, 1.2])
    with c1:
        if score is not None:
            st.plotly_chart(score_gauge(score), use_container_width=True)
        else:
            st.info("报告未含匹配度（可能格式异常）")
    with c2:
        if dims:
            st.plotly_chart(dim_radar(dims), use_container_width=True)
        else:
            st.caption("（无维度评分数据）")
    st.markdown("---")
    sections = parse_report(report)
    if sections:
        render_section_cards(sections)
    with st.expander("查看完整报告（Markdown）"):
        st.markdown(report)
        st.code(report, language="markdown")


# ============================================================
# 页面：投递话术（v2 · 自然口语 + 双版本）
# ============================================================
def page_talk(embedded: bool = False, vkey: str = ""):
    if not embedded:
        hero("投递话术", "三个场景按真人说话的方式写；生成后自动检查禁用词并重写")
    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    if not jobs:
        st.info("先到「找工作 → 岗位库」添加岗位")
        return
    _names = [j[0] for j in jobs]
    _idx = 0
    if st.session_state.get("talk_pick") in _names:
        _idx = _names.index(st.session_state["talk_pick"])
    name = st.selectbox("选择岗位", _names, index=_idx, key="talk_pick")
    jd = read_text(JDS_DIR / f"{name}.txt")
    profile = read_text(PROFILE_PATH) or read_text(ME_PATH)

    if st.session_state.get("highlights") is None:
        st.session_state["highlights"] = ""
    with st.expander("✨ 个人亮点（可选：不生成也能写，生成了更聚焦）", expanded=False):
        if st.button("提取亮点", key="gen_hl"):
            with st.spinner("提取中…"):
                try:
                    st.session_state["highlights"] = ask_chat(PROMPT_HIGHLIGHT, profile)
                except Exception as e:
                    st.error(str(e))
        if st.session_state["highlights"]:
            st.markdown(st.session_state["highlights"])

    labels = [v[0] for v in TALK_VARIANTS.values()]
    if vkey and vkey in TALK_VARIANTS:
        variant = vkey
        st.caption(f"话术场景：**{TALK_VARIANTS[variant][0]}**（在上面切换）")
    else:
        variant = list(TALK_VARIANTS.keys())[labels.index(
            st.radio("场景", labels, horizontal=True, key="talk_variant"))]

    if st.button("生成话术", type="primary"):
        with st.spinner("生成中…"):
            try:
                prompt_hint = ""
                if st.session_state["highlights"]:
                    prompt_hint = ("\n\n参考亮点（可选用，用了读起来不自然就别用）：\n"
                                   + st.session_state["highlights"])
                talk, hits = generate_talk(
                    lambda p, *m: ask_chat(p + prompt_hint, *m), variant, profile, jd
                )
                st.session_state[f"talk_{name}_{variant}"] = talk
                st.session_state[f"talkhits_{name}_{variant}"] = hits
                next_step("talk_done")
            except Exception as e:
                st.error(str(e))

    talk = st.session_state.get(f"talk_{name}_{variant}", "")
    if talk:
        st.markdown(f'<div class="oa-card">{talk.replace(chr(10), "<br>")}</div>',
                    unsafe_allow_html=True)
        st.code(talk + "\n\n" + v41.talk_attachments(), language="text")
        st.caption("上方为话术正文 + 投递三件套（简历 PDF / 上线项目 / GitHub），直接复制发送即可")
        hits = st.session_state.get(f"talkhits_{name}_{variant}", [])
        if hits:
            st.warning(f"这一版仍含可疑用语：{hits}。建议手动改一版再发。")
        else:
            st.success("已通过禁用词检查（模板腔、贵司、期待您的回复这类都没有）")


# ============================================================
# 页面：简历建议
# ============================================================
