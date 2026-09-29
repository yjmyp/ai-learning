# -*- coding: utf-8 -*-
"""Agent 流程 —— OfferAgent 页面域模块（2026-09-29 从 offer_agent_app.py 拆出）"""
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

def page_agent():
    """Agent 流程：选岗位 → 一键跑完整工具链 → 看 trace → 执行动作停在你的确认。"""
    import sys

    ROOT = BASE_DIR.parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from offer_agent_core import AgentState, run_agent, continue_after_confirm, save_agent_log, extract_score
    from offer_agent_multi import run_supervisor
    from offer_agent_core import gate_verdict
    from offer_agent_tools import build_registry
    from agent_memory import Memory

    # 注入 API Key：部署版没有 local_key.py，key 在 Secrets / env / config
    ak = get_api_key()
    if ak:
        os.environ["DEEPSEEK_API_KEY"] = ak

    st.caption("引擎演示：模型拿到任务后**自主规划工具链**（质量评估 → JD 拆解 → 匹配 → 话术 → 校验 → 投递），"
               "执行类动作（打开投递链接）停在你的确认——发送前那一下由你做。")

    jobs = list_jobs()
    if not jobs:
        st.info("岗位库为空：先去「🔎 岗位库」添加岗位。")
        return
    options = {f"{m.get('company') or '未知'} · {n}" : (n, m) for n, m, _ in jobs}
    pick_label = st.selectbox("选择岗位", list(options), key="agent_pick")
    name, meta = options[pick_label]
    profile = read_text(PROFILE_PATH) or read_text(ME_PATH)
    if not profile.strip():
        st.warning("还没有画像：先去「🧬 自我蒸馏」生成画像，Agent 的匹配/话术才有素材。")

    _mt = meta
    _jd_len = len(read_text(JDS_DIR / (name + ".txt")))
    st.markdown(
        f'<div class="oa-card">'
        f'<span class="oa-tag oa-tag-amber">{_mt.get("status") or "待投"}</span>'
        f'<b>{_mt.get("company") or "未知"} · {name}</b>'
        f'　📍 {_mt.get("city") or "—"}　🔗 {_mt.get("url") or "无链接"}'
        f'<div style="color:var(--muted);font-size:13px;margin-top:3px;">'
        f'来源：{_mt.get("source") or "手动添加"}　·　JD {_jd_len} 字符　·　'
        f'匹配分：{_mt.get("match_score") if _mt.get("match_score") is not None else "未跑"}</div>'
        f'</div>', unsafe_allow_html=True)

    _mode = st.radio("运行模式", ["单 Agent（自主全链）", "多 Agent（主管分派：岗位分析师+话术专家）"],
                     horizontal=True, key="agent_mode")

    if st.button("🤖 一键跑 Agent 流程", type="primary", key="agent_run"):
        jd_text = read_text(JDS_DIR / (name + ".txt"))
        mem = Memory(db_path=DATA_DIR / "memory.db")
        mem.extract_facts("我是余剑，南京邮电大学网络工程2027届，做过RAG知识库问答系统和Agent求职助手，想投AI应用开发实习岗")
        state = AgentState(memory=mem, budget=14)
        task = (
            f"帮我把岗位「{meta.get('company') or ''} · {name}（{meta.get('city') or ''}）」的求职处理流程跑一遍。\n"
            f"【JD】\n{jd_text[:800]}\n\n【我的画像】\n{profile}\n\n"
            "请依次执行：1.assess_job 评估岗位质量 2.split_jd 拆解JD 3.match_job 算匹配度 "
            "4.generate_talk 生成BOSS话术 5.check_talk 校验话术 6.open_application 打开投递链接（这个会等我确认）。"
            "全部完成后给中文汇总：岗位质量结论、匹配度、最终话术、下一步建议。"
        )
        with st.spinner("Agent 正在自主规划并调用工具链…"):
            if _mode.startswith("多"):
                final, state = run_supervisor(task, build_registry(), state,
                                              db_path=DATA_DIR / "memory.db")
            else:
                final, state = run_agent(task, build_registry(), state)
        save_agent_log(name, meta.get("company", ""), state, final, confirmed=False)
        st.session_state["agent_final"] = final
        st.session_state["agent_state"] = state

    if "agent_state" not in st.session_state:
        st.info("选好岗位后点「一键跑 Agent 流程」。")
        return

    state = st.session_state["agent_state"]
    st.markdown("### 最终汇总")
    st.markdown(st.session_state.get("agent_final", ""))

    with st.expander("执行轨迹 trace（每步工具调用，可复盘）"):
        trace_slim = []
        for t in state.trace:
            args = {k: (v[:60] + "…" if isinstance(v, str) and len(v) > 60 else v)
                    for k, v in t.get("args", {}).items()}
            res = str(t.get("result", ""))
            res = res[:220] + ("…" if len(res) > 220 else "")
            trace_slim.append({"步": t.get("step"), "工具": t.get("tool"),
                               "参数": args, "成功": t.get("ok"), "结果": res})
        st.dataframe(trace_slim, use_container_width=True)

    if state.pending:
        st.warning(f"🔒 执行动作停在确认：**{state.pending['tool']}** — {state.pending['args']}")
        st.caption("按 OfferAgent 原则：打开投递链接前，先人工核对链接是否真实有效。")
        if st.button("✅ 确认执行（打开投递链接）", type="primary", key="agent_confirm"):
            with st.spinner("执行中…"):
                final, state = continue_after_confirm(build_registry(), state)
            save_agent_log(name, meta.get("company", ""), state, final, confirmed=True)
            st.session_state["agent_final"] = final
            st.session_state["agent_state"] = state
            st.rerun()

    # ===== 投递日志（Agent 运行资产：每次跑都落盘，可复盘可统计） =====
    st.markdown("### 投递日志（最近 Agent 运行）")
    _log_path = DATA_DIR / "agent_logs.jsonl"
    _logs = []
    if _log_path.exists():
        for _ln in _log_path.read_text(encoding="utf-8").strip().splitlines():
            try:
                _logs.append(json.loads(_ln))
            except Exception:
                pass
    if _logs:
        _slim = [{"时间": l.get("time", ""), "公司": l.get("company", ""),
                  "岗位": l.get("job", ""), "匹配分": l.get("match_score"),
                  "裁决": l.get("verdict", "—"),
                  "步数": l.get("steps"),
                  "确认": "✅" if l.get("confirmed") else "—"}
                 for l in reversed(_logs[-8:])]
        st.dataframe(_slim, use_container_width=True)
        st.caption(f"共 {len(_logs)} 条 Agent 运行记录，全部存于 data/agent_logs.jsonl（人机分工：机器算分，人做决定）。")
    else:
        st.caption("还没有 Agent 运行记录——跑一次就会出现在这里。")

    # ===== 批量处理：一键跑完所有「待投」岗位（商业化：把重复劳动交给引擎） =====
    with st.expander("⚡ 批量处理：一键跑完所有「待投」岗位（写入投递日志）"):
        _pending = [j for j in list_jobs() if j[1].get("status") == "待投"]
        st.caption(f"当前「待投」岗位 **{len(_pending)}** 个。逐个跑完整工具链（质量评估→JD拆解→匹配→话术→校验），"
                   f"模式跟随上方选择（当前：{'多 Agent（主管分派）' if _mode.startswith('多') else '单 Agent'}）；"
                   "结果落盘 agent_logs.jsonl；投递动作仍停在你的确认。")
        if st.button("🚀 开始批量跑", key="agent_batch"):
            if not _pending:
                st.info("没有待投岗位。")
            else:
                _pbar = st.progress(0, text="准备中…")
                _rows = []
                for _i, (_nm, _mm, _) in enumerate(_pending):
                    _pbar.progress((_i + 1) / len(_pending), text=f"正在处理 {_nm} …")
                    _jd = read_text(JDS_DIR / (_nm + ".txt"))
                    try:
                        _mem = Memory(db_path=DATA_DIR / "memory.db")
                        _mem.extract_facts("我是余剑，南京邮电大学网络工程2027届，AI应用开发实习生，正在批量评估岗位")
                        _stt = AgentState(memory=_mem, budget=10)
                        _task = (f"帮我把岗位「{_mm.get('company') or ''} · {_nm}」跑完整求职流程："
                                 f"assess_job→split_jd→match_job→generate_talk→check_talk→open_application(会等我确认)。"
                                 f"【JD】\n{_jd[:800]}\n【画像】\n{profile[:600]}")
                        if _mode.startswith("多"):
                            _fin, _stt = run_supervisor(_task, build_registry(), _stt,
                                                        db_path=DATA_DIR / "memory.db")
                        else:
                            _fin, _stt = run_agent(_task, build_registry(), _stt)
                        save_agent_log(_nm, _mm.get("company", ""), _stt, _fin, confirmed=False)
                        _rows.append({"岗位": _nm, "公司": _mm.get("company", ""),
                                      "匹配分": extract_score(_stt.trace),
                                      "裁决": gate_verdict(extract_score(_stt.trace)),
                                      "步数": len(_stt.trace),
                                      "状态": "停在确认" if _stt.pending else "完成"})
                    except Exception as _e:
                        _rows.append({"岗位": _nm, "公司": _mm.get("company", ""),
                                      "匹配分": None, "步数": 0, "状态": f"失败：{type(_e).__name__}"})
                _pbar.empty()
                st.dataframe(_rows, use_container_width=True)
                st.success(f"批量完成：{len(_rows)} 个岗位已写入 agent_logs.jsonl。点开记录逐个确认投递。")



# ============================================================
# 页面：批量投递台（半自动——话术/链接/三件套全备好，发送那一下留给你）
# ============================================================
