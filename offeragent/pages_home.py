# -*- coding: utf-8 -*-
"""仪表/日报/数据日志/蒸馏引导 —— OfferAgent 页面域模块（2026-09-29 从 offer_agent_app.py 拆出）"""
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
import distill_chat
import plotly.graph_objects as go
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

def page_distill_chat():
    """问答式自我蒸馏：像聊天一样，一次问一个问题。"""
    hero("自我蒸馏", "问答式。一次一个问题，答完 15 题自动生成 6 份档案")
    state = distill_chat.load()
    done, total = distill_chat.progress(state)
    st.progress(done / total, text=f"已答 {done} / {total} 题")

    if not state["history"]:
        distill_chat.start(state)
        st.rerun()

    for m in state["history"]:
        with st.chat_message("assistant" if m["role"] == "assistant" else "user"):
            st.markdown(m["content"])

    if done >= total:
        st.divider()
        c1, c2 = st.columns([1, 1])
        if c1.button("🧬 生成 6 份档案", type="primary", key="chat_gen"):
            with st.spinner("蒸馏中…（约 20 秒）"):
                try:
                    outputs = distill.distill(
                        {"answers": state["answers"], "followups": {}},
                        lambda p: ask_chat(p))
                    st.success("已生成：" + "、".join(outputs.keys()))
                    next_step("profile_done")
                    for name, content in outputs.items():
                        with st.expander(f"看 {name}"):
                            st.markdown(content)
                except Exception as e:
                    st.error(str(e))
        if c2.button("↺ 重新开始（清空答案）", key="chat_reset"):
            distill_chat.reset()
            st.rerun()
    else:
        answer = st.chat_input("在这里回答；写不出可以输入「跳过」")
        if answer:
            with st.spinner("记下了…"):
                try:
                    distill_chat.reply_and_ask(state, answer, lambda p: ask_chat(p))
                except Exception as e:
                    st.error(str(e))
            st.rerun()

    with st.expander("看已答内容 / 重新开始"):
        st.json(state["answers"], expanded=False)
        if st.button("↺ 清空并重新开始", key="chat_reset2"):
            distill_chat.reset()
            st.rerun()


def onboarding_panel():
    """首屏引导：缺什么就给什么，一键跳过去。"""
    todo = []
    if not PROFILE_PATH.exists():
        todo.append(("还没有「个人画像」——匹配和话术都依赖它",
                     "distill", "花 10 分钟答完 15 题就有"))
    jobs = list_jobs()
    if not jobs:
        todo.append(("岗位库是空的", "jobs", "给关键词搜一次岗，勾选入库"))
    elif not any(m.get("match_score") is not None for _, m, _ in jobs):
        todo.append(("岗位还没有匹配度", "match", "跑一次就知道值不值得投"))
    if not any(m.get("status") in ("已投", "面试中", "已拒", "Offer")
               for _, m, _ in jobs):
        todo.append(("还没投出去过", "apply", "话术在这里生成，发送由你按"))

    if not todo:
        return
    st.markdown("### 🚩 还差这几步就能投递")
    for text, target, hint in todo:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"- **{text}**　<span style='color:#93A1AF;font-size:12.5px'>{hint}</span>",
                    unsafe_allow_html=True)
        if c2.button("去处理", key=f"ob_{target}"):
            goto_page(target)
    st.divider()


def page_today():
    hero("今日行动", "按匹配度排好的待投清单。生成话术、打开岗位页，发送由你自己按")
    onboarding_panel()
    ensure_dirs()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    pending = [j for j in jobs if j[1]["status"] == "待投"]
    applied = [j for j in jobs if j[1]["status"] == "已投"]

    c1, c2, c3 = st.columns(3)
    c1.metric("待投岗位", len(pending))
    c2.metric("已投岗位", len(applied))
    c3.metric("今天已投", apply_assist.applied_today())

    # 每日目标 + 连续投递天数
    try:
        _c = json.loads(read_text(CONFIG_PATH, "{}"))
    except Exception:
        _c = {}
    target = int(_c.get("daily_target", 3) or 3)
    today_n = apply_assist.applied_today()
    st.progress(min(today_n / max(target, 1), 1.0),
                text=f"今天的投递目标：{today_n} / {target} 家")
    with st.expander("看连续投递天数 / 改目标"):
        st.caption("每日投递目标在「⚙️ 设置」里改（设置项统一收在设置页）。")
        if st.button("去设置里改目标", key="to_target_setting"):
            goto_page("settings")
        dates = sorted({r.get("date") for r in apply_assist.load_applications()
                        if r.get("date")}, reverse=True)
        streak = 0
        d = time.strftime("%Y-%m-%d")
        for ds in dates:
            if ds == d or (streak and ds < d):
                streak += 1
                d = time.strftime("%Y-%m-%d", time.localtime(
                    time.mktime(time.strptime(ds, "%Y-%m-%d")) - 86400))
            else:
                break
        st.caption(f"连续投递天数：**{streak}** 天（有投递记录的连续日期）")

    # ---- 面试日历（v4.1）----
    reminders = v41.interview_reminders(jobs)
    with st.expander("🗓️ 面试日历" + (f"（{len(reminders)} 场）" if reminders else "")):
        st.caption("把岗位状态标成「面试中」并填日期，这里会倒计时提醒你。")
        alljobs = list_jobs()
        interviewable = [(n, m) for n, m, _ in alljobs if m["status"] != "排除"]
        if interviewable:
            iname = st.selectbox("岗位", [n for n, _ in interviewable], key="iv_pick")
            idate = st.text_input("面试日期（YYYY-MM-DD）", key="iv_date",
                                  placeholder="2026-10-05")
            if st.button("保存面试安排", key="iv_save"):
                imeta = dict(interviewable)[iname]
                if not re.match(r"\d{4}-\d{2}-\d{2}", idate.strip()):
                    st.warning("日期格式：YYYY-MM-DD")
                else:
                    imeta["status"] = "面试中"
                    imeta["interview_date"] = idate.strip()
                    v41.save_meta(iname, imeta)
                    st.success(f"已把 {iname} 标为面试中，日期 {idate.strip()}。")
                    st.rerun()
        else:
            st.caption("暂无岗位可安排。")
        if reminders:
            st.markdown("**即将到来**")
            for n, c, d, days in reminders[:8]:
                if days < 0:
                    st.markdown(f"- ⚠️ **{c}**（{n}）面试日已过 {abs(days)} 天，记得补状态")
                elif days == 0:
                    st.markdown(f"- 🔔 **今天面试：{c}**（{n}）{d}")
                elif days <= 7:
                    st.markdown(f"- ⏳ **{days} 天后：{c}**（{n}）{d}")
                else:
                    st.markdown(f"- {c}（{n}）{d}（还有 {days} 天）")
        else:
            st.caption("还没有面试安排。")

    mode = st.radio("投递模式",
                    ["🙋 手动：只给话术，我自己复制发送",
                     "🤝 半自动：帮我打开岗位页 + 话术写进剪贴板"],
                    horizontal=True)
    semi = "半自动" in mode
    st.caption("两种模式都不会替你发送。半自动的差别只是帮你把页面打开、把话术放进剪贴板。")

    if not pending:
        st.success("待投清单空了。去「岗位库」补新岗位，或者去「求职日报」看看该做什么。")
        return

    st.markdown("### 今天先打这几个")
    profile = read_text(PROFILE_PATH) or read_text(ME_PATH)
    for name, meta, jd in pending[:5]:
        score = meta.get("match_score")
        jinfo = {"jd": jd, "company": meta.get("company", ""),
                 "city": meta.get("city", ""), "salary": "",
                 "url": meta.get("source_url", "")}
        q = job_quality.assess(jinfo)
        qnote = "" if q["verdict"] == "正常" else f" · ⚠️ {job_quality.summarize(q)}"
        with st.expander(f"**{meta.get('company') or name}** · {name} · 匹配度 "
                         f"{score if score is not None else '未评'}"
                         f"{' · ' + meta['city'] if meta.get('city') else ''}{qnote}",
                         expanded=(pending.index((name, meta, jd)) == 0)):
            key = f"today_talk_{name}"
            b1, b2, b3 = st.columns([2, 2, 2])
            if b1.button("✍️ 去投递台生成话术", key=f"g_{name}",
                         help="全应用只有投递台生成话术，避免同一件事两套做法"):
                goto_page("apply", talk_pick=name)
            url = meta.get("source_url", "")
            if b2.button("🔗 打开岗位页", key=f"o_{name}", disabled=not url):
                if apply_assist.open_url(url):
                    st.success("已用默认浏览器打开（页面可能需登录）")
                else:
                    st.warning("打开失败，请手动复制链接：" + url)
            if b3.button("✅ 标记已投", key=f"a_{name}"):
                meta["status"] = "已投"
                meta["applied_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                save_meta(name, meta)
                apply_assist.log_application(
                    name, meta, st.session_state.get(key, ""))
                st.success("已记录投递。刷新后它会从待投清单消失。")
                next_step("applied")

            talk = st.session_state.get(key, "")
            if talk:
                st.markdown(f'<div class="oa-card">{talk.replace(chr(10), "<br>")}</div>',
                            unsafe_allow_html=True)
                if semi:
                    if st.button("📋 复制话术并放进剪贴板", key=f"c_{name}"):
                        ok = apply_assist.copy_to_clipboard(talk)
                        st.success("话术已进剪贴板，去 BOSS 里粘贴发送" if ok
                                   else "剪贴板写入失败，请手动选中复制")
                else:
                    st.code(talk + "\n\n" + v41.talk_attachments(), language="text")
                    st.caption("上面这块可以直接选中复制（含投递三件套）")
                hits = st.session_state.get(key + "_hits", [])
                if hits:
                    st.warning(f"仍含可疑用语：{hits}，建议手动改一版")


# ============================================================
# 页面：求职日报
# ============================================================
def page_report():
    hero("求职日报", "每天一条：投了什么、什么状态、明天先做什么")
    ensure_dirs()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    records = apply_assist.load_applications()
    today = time.strftime("%Y-%m-%d")
    today_records = [r for r in records if r.get("date") == today]

    jobs = [j for j in list_jobs()]
    pending = [j for j in jobs if j[1]["status"] == "待投"]
    applied = [j for j in jobs if j[1]["status"] == "已投"]
    excluded = [j for j in jobs if j[1]["status"] == "排除"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("岗位总数", len(jobs))
    c2.metric("待投", len(pending))
    c3.metric("已投", len(applied))
    c4.metric("今天投了", len(today_records))

    if today_records:
        st.markdown("### 今天投的")
        for r in today_records:
            st.markdown(f"- **{r.get('company') or r['job']}** · {r['job']}"
                        f" · {r.get('score', '')} · {r.get('time', '')[11:16]}")
    else:
        st.info("今天还没有投递记录。投完在「今日行动」点一下「标记已投」就会记进来。")

    st.divider()
    if st.button("📝 生成今天的日报（调用 DeepSeek）", type="primary"):
        with st.spinner("写日报中…"):
            try:
                overview = (
                    f"今天日期：{today}\n"
                    f"岗位总数：{len(jobs)}｜待投：{len(pending)}｜已投：{len(applied)}"
                    f"｜排除：{len(excluded)}\n"
                    f"今天投递记录：{len(today_records)} 条\n"
                    + "\n".join(
                        f"- {r.get('company') or r['job']}（{r['job']}，匹配度 {r.get('score')}）"
                        for r in today_records)
                    + f"\n\n待投里匹配度最高的三个：\n"
                    + "\n".join(
                        f"- {m.get('company') or n}（{n}，匹配度 {m.get('match_score')}）"
                        for n, m, _ in pending[:3])
                )
                prompt = """你是求职陪跑顾问。根据下面这份状态，写一份今天的求职日报。
要求：
1. 用三个小标题：## 今天做了什么 / ## 现在的局面 / ## 明天先做这三件
2. "明天先做这三件"必须具体到动作（投哪家、补哪块、练什么），不要写"继续努力"
3. 如果今天一条都没投，直接说清楚，不要绕
4. 全文 200 到 300 字，平实，不要鼓励式的话
"""
                report = ask_chat(prompt, overview)
                (REPORTS_DIR / f"{today}.md").write_text(report, encoding="utf-8")
                st.success(f"已存到 data/reports/{today}.md")
                st.markdown(report)
            except Exception as e:
                st.error(str(e))

    saved = sorted(REPORTS_DIR.glob("*.md"), reverse=True)
    if saved:
        with st.expander(f"历史日报（{len(saved)} 篇）"):
            pick = st.selectbox("选一天", [p.stem for p in saved], key="report_pick")
            st.markdown(read_text(REPORTS_DIR / f"{pick}.md"))


def page_data_log():
    """数据与日志：全应用唯一统计口径的地方 + 日报。

    以前「数据概览 / 求职日报 / 投递记录」三页各算一遍口径还不一样，
    现在统一在这里算：漏斗 → 趋势 → 岗位排名 → 日报。
    """
    hero("数据与日志", "漏斗、趋势、岗位排名、每日日报——统计口径只有这一处")
    ensure_dirs()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    jobs = list_jobs()
    rows = apply_assist.load_applications()
    fn = pipeline.funnel(jobs)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("已投出去", fn["submitted"])
    c2.metric("有回应", fn["interviewed"], help="面试中 / 已拒 / Offer 都算回应")
    c3.metric("Offer", fn["offers"])
    c4.metric("今天投递", apply_assist.applied_today())
    st.caption(f"回应率 {fn['reply_rate']}%　·　Offer 率 {fn['offer_rate']}%　·　"
               f"口径：岗位库里状态为已投 / 面试中 / 已拒 / Offer 的岗位")

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("##### 投递漏斗")
        if fn["submitted"] > 0:
            st.plotly_chart(v41.funnel_fig(fn["submitted"], fn["interviewed"], fn["offers"]),
                            use_container_width=True)
        else:
            st.caption("还没有投递记录。投出第一份后这里会出现漏斗。")
    with g2:
        st.markdown("##### 近 14 天投递趋势")
        if rows:
            st.plotly_chart(v41.weekly_fig(rows), use_container_width=True)
        else:
            st.caption("还没有投递记录。")

    active = [j for j in jobs if j[1]["status"] != "排除"]
    fig = rank_bar(active)
    if fig:
        st.markdown("##### 岗位匹配度排名")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("##### 🔁 一键复盘投递进度（多 Agent：投递复盘员读真实岗位库）")
    if st.button("🔁 跑一次投递复盘", key="agent_review"):
        with st.spinner("主管分派「投递复盘员」读取真实岗位库并分析…"):
            import sys as _sys
            _ROOT = DATA_DIR.parent.parent
            if str(_ROOT) not in _sys.path:
                _sys.path.insert(0, str(_ROOT))
            from offer_agent_multi import run_supervisor
            from offer_agent_tools import build_registry
            _fin, _ = run_supervisor(
                "请复盘当前投递进度：让投递复盘员用 review_status 读真实岗位库数据，算漏斗转化率并给跟进建议。",
                build_registry(), db_path=str(DATA_DIR / "memory.db"))
            st.markdown(_fin)

    st.markdown("##### ⚡ 批量打分排序（岗位分析师逐岗评估，按匹配分排投递优先级）")
    if st.button("⚡ 批量打分（待投岗位）", key="agent_batch_score"):
        with st.spinner("主管分派「岗位分析师」逐个评估岗位质量与匹配度…"):
            import sys as _sys
            _ROOT = DATA_DIR.parent.parent
            if str(_ROOT) not in _sys.path:
                _sys.path.insert(0, str(_ROOT))
            import batch_score as _bs
            _res = _bs.run_batch()
            if not _res:
                st.info("没有待投岗位可跑（加 --force 可强制重跑）。")
            else:
                st.dataframe(_res, use_container_width=True)
                st.success("匹配分已回填岗位库，投递优先级见上表（机器算分，人做决定）。")

    st.markdown("##### 🤖 Agent 运行洞察（引擎自动跑的记录）")
    _log_path = DATA_DIR / "agent_logs.jsonl"
    _logs = []
    if _log_path.exists():
        for _ln in _log_path.read_text(encoding="utf-8").strip().splitlines():
            try:
                _logs.append(json.loads(_ln))
            except Exception:
                pass
    if _logs:
        _g1, _g2 = st.columns(2)
        with _g1:
            _valid = [(l.get("company") or l.get("job"), l.get("match_score"))
                      for l in _logs if l.get("match_score") is not None]
            if _valid:
                _names = [v[0] for v in _valid]
                _scores = [v[1] for v in _valid]
                _bf = go.Figure(go.Bar(x=_names, y=_scores, marker_color="#5558D6",
                                       text=[f"{s}%" for s in _scores], textposition="outside"))
                _bf.update_layout(title="Agent 匹配分（按岗位）", height=280,
                                  yaxis_range=[0, 100], margin=dict(t=42, b=10, l=10, r=10),
                                  xaxis_tickangle=-20)
                st.plotly_chart(_bf, use_container_width=True)
        with _g2:
            st.caption("最近 Agent 运行：")
            _slim = [{"时间": l.get("time", "")[5:16], "公司": l.get("company", ""),
                      "岗位": l.get("job", ""), "匹配分": l.get("match_score"),
                      "Token": (l.get("tokens") or {}).get("prompt", 0),
                      "确认": "✅" if l.get("confirmed") else "—"}
                     for l in reversed(_logs[-6:])]
            st.dataframe(_slim, use_container_width=True)
        st.caption("口径：匹配分由 Agent 引擎自动计算并落盘；投递决定永远由人做——机器算分，人做决定。")
    else:
        st.caption("还没有 Agent 运行记录。去「找工作 → Agent 流程」跑一次，这里就会出现匹配分与运行轨迹。")

    st.markdown("##### 🔍 分数对账（单一权威源：岗位库 meta vs 日志历史快照）")
    _audit = audit_scores()
    if _audit:
        _at = [{"公司": r[0], "岗位库分(权威)": r[1], "日志最新分(快照)": r[2],
                "状态": "✅" if r[3] else "⚠️", "说明": r[4]} for r in _audit]
        st.dataframe(_at, use_container_width=True)
        _bad = [r for r in _audit if not r[3]]
        if _bad:
            st.warning(f"{len(_bad)} 项不一致：日志有事件分但岗位库未回填（以岗位库为准，重跑「⚡ 批量打分」可修复）。")
        else:
            st.caption("全部一致：岗位库分数是唯一权威，日志只记事件（历史快照不覆盖岗位库）。")
    else:
        st.caption("岗位库为空，无需对账。")

    st.markdown("---")
    page_report()

# ============================================================
# 页面：仪表盘
# ============================================================
# ============================================================
# 页面：我的画像
# ============================================================
