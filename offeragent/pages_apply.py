# -*- coding: utf-8 -*-
"""批量投递台 —— OfferAgent 页面域模块（2026-09-29 从 offer_agent_app.py 拆出）"""
import json
import os
import re
import time
from pathlib import Path

import streamlit as st

# 分层公共层 + 业务子模块（宽 import 兜底，页面函数保持原名调用）
from store import *
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

# 跨模块页面（拆分后补 import）
from pages_home import page_distill_chat
from pages_work import page_profile
from pages_match import page_talk

def page_batch_apply(vkey: str = "boss"):
    st.caption("批量模式：一次给全部待投岗位生成话术 → 逐条确认 → 复制 / 打开 / 标记已投。"
               "发送那一下永远留给你（自动群发会被平台风控封号）。")
    jobs = [j for j in list_jobs() if j[1]["status"] == "待投"]
    if not jobs:
        st.info("当前没有待投岗位。去「找工作 → 岗位库」把岗位状态设为「待投」。")
        return
    st.markdown(f"待投 **{len(jobs)}** 家　·　今日已投 **{apply_assist.applied_today()}** 家")

    c1, c2 = st.columns([1, 3])
    if c1.button("⚡ 批量生成全部话术", type="primary", key="bg_gen"):
        fprof = read_text(PROFILE_PATH) or read_text(ME_PATH)
        if not fprof.strip():
            st.warning("先到「🧬 我的 → 自我蒸馏」生成画像")
        else:
            queue = {}
            with st.spinner(f"为 {len(jobs)} 家生成话术…（每家几秒）"):
                for n, m, jd in jobs:
                    try:
                        t, h = generate_talk(lambda p, *mm: ask_chat(p, *mm),
                                             vkey, fprof, jd or "")
                        queue[n] = {"talk": t, "hits": h}
                    except Exception as e:
                        queue[n] = {"talk": "", "hits": [str(e)[:80]]}
                write_text(TALKQ_PATH, json.dumps(queue, ensure_ascii=False, indent=2))
            st.session_state["bg_done"] = len(queue)
            st.rerun()
    if st.session_state.get("bg_done"):
        st.success(f"已生成 {st.session_state.pop('bg_done')} 条话术。下面逐条确认、复制、打开、标记。")
        st.caption("建议节奏：复制话术 → 打开岗位 → 粘贴发送 → 回来标记已投。")

    queue = {}
    try:
        queue = json.loads(read_text(TALKQ_PATH, "{}"))
    except Exception:
        queue = {}

    for n, m, jd in sorted(jobs, key=lambda x: -(x[1].get("match_score") or 0)):
        comp = m.get("company") or n
        score = m.get("match_score")
        sc = f" · 匹配 {score}%" if score is not None else ""
        with st.expander(f"{comp}　{m.get('city', '')}{sc}", expanded=False):
            if m.get("source_url"):
                st.caption(f"🔗 {m['source_url']}")
            q = queue.get(n, {})
            talk = st.text_area("话术（可改，改完点保存）", q.get("talk", ""),
                                key=f"bq_{n}", height=90)
            if q.get("hits"):
                st.warning(f"仍含可疑用语：{q['hits']}")
            cc = st.columns(4)
            if cc[0].button("📋 复制话术", key=f"bc_{n}"):
                ok = apply_assist.copy_to_clipboard(talk)
                st.toast("已复制到剪贴板" if ok else "复制失败", icon="✅" if ok else "⚠️")
            if cc[1].button("🌐 打开岗位", key=f"bo_{n}"):
                _gate = check_apply_allowed(n, m)
                if not _gate["allowed"]:
                    st.warning(_gate["reason"])
                else:
                    ok = apply_assist.open_url(m.get("source_url", ""))
                    st.toast("已在浏览器打开" if ok else "该岗位没有链接", icon="✅" if ok else "⚠️")
            if cc[2].button("✏️ 保存修改", key=f"bs_{n}"):
                queue[n] = {"talk": talk, "hits": q.get("hits", [])}
                write_text(TALKQ_PATH, json.dumps(queue, ensure_ascii=False, indent=2))
                st.toast("已保存", icon="✅")
            if cc[3].button("✅ 发出去了，标记已投", type="primary", key=f"bm_{n}"):
                _gate = check_apply_allowed(n, m)
                if not _gate["allowed"]:
                    st.warning(_gate["reason"])
                else:
                    mark_applied(n, m)
                    apply_assist.log_application(n, m, talk or q.get("talk", ""))
                    st.session_state["_pending_hint"] = f"已标记投递：{comp}"
                    st.rerun()



def distill_section():
    """自我蒸馏（问答式 / 填表式）。chat_input 必须在页面级，所以用 radio 切换。"""
    mode = st.radio("模式", ["💬 问答式（推荐）", "📋 填表式"],
                    horizontal=True, key="distill_mode")
    if "问答" in mode:
        page_distill_chat()
    else:
        page_profile()


def page_apply_desk():
    """投递台：全应用唯一生成投递话术的地方（单条精修 / 批量一次到位）。"""
    hero("投递台", "话术、岗位链接、投递三件套一次备好；发送那一下由你自己按")
    labels = [v[0] for v in TALK_VARIANTS.values()]
    vlabel = st.segmented_control("话术场景", labels, default=labels[0],
                                  key="desk_variant") or labels[0]
    vkey = list(TALK_VARIANTS.keys())[labels.index(vlabel)]
    mode = st.segmented_control(
        "工作方式", ["🗂 批量（一次处理全部待投）", "✍️ 单条精修（一家一版）"],
        default="🗂 批量（一次处理全部待投）", key="desk_mode") \
        or "🗂 批量（一次处理全部待投）"
    st.caption("批量：适合已经筛完、要一次性推进多家。"
               "单条：适合重点公司，想逐句改。两者都只**生成**话术，发送永远由你按。")
    if "单条" in mode:
        page_talk(embedded=True, vkey=vkey)
    else:
        page_batch_apply(vkey=vkey)




# ============================================================
# 公开数字人名片页（?twin=1）：考官/HR 知情访问
# 合规说明：AI 分身基于真实画像回答，不冒充本人，最终以真人沟通为准。
# ============================================================
