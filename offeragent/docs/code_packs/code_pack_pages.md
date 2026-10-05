# 代码包：页面域（首页 / 更多 / 分身 / Agent / 对比）

> 内容包括：今日台/蒸馏聊天首页、更多页（建议/设置/对比/公司/拷问/投递记录）、数字分身页、Agent 控制台、对比页。目标是让 AI 看懂 11 页面的 UI 编排方式。

## 怎么喂
把本文件全文复制给 DeepSeek，开头加一句：
> 「先读完全文代码，再按我的水平逐块讲解，一次一小步，先框架后填空，不直接给完整答案。」

## 包含的文件

| 文件 | 行数 | 说明 |
|---|---|---|
| `offeragent/pages_home.py` | 449 | 见下方代码 |
| `offeragent/pages_more.py` | 423 | 见下方代码 |
| `offeragent/pages_twin.py` | 413 | 见下方代码 |
| `offeragent/pages_agent.py` | 199 | 见下方代码 |
| `offeragent/pages_match.py` | 209 | 见下方代码 |

**合计 1693 行**（约 6KB），在 DeepSeek 上下文内。

---

## ===== offeragent/pages_home.py（449 行）=====

```python
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
```

## ===== offeragent/pages_more.py（423 行）=====

```python
# -*- coding: utf-8 -*-
"""建议/设置/对比/公司/拷问/投递记录（简历页已拆到 pages_resume.py） —— OfferAgent 页面域模块（2026-09-29 从 offer_agent_app.py 拆出）"""
import json
import os
import re
import time
from pathlib import Path

import streamlit as st

# 分层公共层 + 业务子模块（宽 import 兜底，页面函数保持原名调用）
from store import *
from prompts import PROMPT_ADVICE
from pages_twin import find_avatar
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


def page_advice():
    hero("简历建议", "匹配报告 + 简历 → 3 条可执行修改建议")
    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    if not jobs:
        st.info("先到「岗位库」添加岗位")
        return
    name = st.selectbox("选择岗位", [j[0] for j in jobs], key="advice_pick")
    report = read_text(MATCH_DIR / f"match_{name}.md")
    if not report:
        st.warning("该岗位还没跑匹配，先到「匹配分析」页运行")
        return
    default_resume = read_text(BASE_DIR / ".." / "简历" / "余剑-简历-AI应用开发实习-v2.md") \
        if (BASE_DIR / ".." / "简历" / "余剑-简历-AI应用开发实习-v2.md").exists() else ""
    default_resume = resume_clean.clean(default_resume)[0]
    resume = st.text_area("简历全文（默认读取 v2，可粘贴覆盖）", default_resume,
                          height=300, key="resume_area")
    if st.button("📝 生成简历建议", type="primary"):
        resume = resume_clean.clean(resume)[0]
        with st.spinner("生成中…"):
            try:
                st.session_state["advice_result"] = ask_chat(PROMPT_ADVICE, report, resume)
            except Exception as e:
                st.error(str(e))
    advice = st.session_state.get("advice_result", "")
    if advice:
        st.markdown(advice)
        st.code(advice, language="markdown")


# ============================================================
# 页面：设置
# ============================================================


def page_settings():
    hero("设置", "API Key 与模型配置")
    ensure_dirs()
    api_key = get_api_key()
    if api_key:
        st.success("API Key 已配置（来自 Secrets/环境变量/本地配置）")
    else:
        st.warning("未配置 API Key")
    cfg = json.loads(read_text(CONFIG_PATH, "{}"))
    new_key = st.text_input("DeepSeek API Key（只保存在本机 data/config.json，不上传）",
                            value=cfg.get("api_key", ""), type="password")
    model = st.selectbox("模型", MODEL_OPTIONS,
                         index=MODEL_OPTIONS.index(cfg.get("model", DEFAULT_MODEL))
                         if cfg.get("model") in MODEL_OPTIONS else 0)
    if st.button("💾 保存设置", type="primary"):
        cfg["api_key"] = new_key.strip()
        cfg["model"] = model
        write_text(CONFIG_PATH, json.dumps(cfg, ensure_ascii=False, indent=2))
        st.success("设置已保存")
    st.markdown("---")
    st.markdown("##### 🎯 每日投递目标")
    st.caption("定一个每天要投几家的数，首屏会显示今天的完成进度。"
               "别定太高——连续投递比一次投很多更重要。")
    _tgt_now = int(cfg.get("daily_target", 3) or 3)
    tgt_new = st.number_input("每天投几家", min_value=1, max_value=20,
                              value=_tgt_now, key="set_target_in")
    if st.button("保存投递目标", key="set_target_save"):
        cfg["daily_target"] = int(tgt_new)
        write_text(CONFIG_PATH, json.dumps(cfg, ensure_ascii=False, indent=2))
        st.success(f"已保存：每天 {int(tgt_new)} 家")
    st.markdown("---")
    st.markdown("##### 💰 花费保护：每天最多调用几次模型")
    st.caption("公开链接被人乱点、或你自己狂跑批量匹配，都是按调用次数烧钱的。"
               "这里设一个每日上限，超过就拒绝调用并提示。填 0 = 不限制。")
    _lim_now = daily_limit()
    _left, _ = usage_left()
    new_lim = st.number_input("每日调用上限（次）", min_value=0, max_value=100000,
                              value=int(cfg.get("daily_call_limit", 200) or 200),
                              step=50, key="lim_in")
    st.caption(f"当前生效：{'不限' if _lim_now <= 0 else str(_lim_now) + ' 次'}　·　"
               f"今天已用 {0 if _lim_now <= 0 else _lim_now - _left} 次")
    if st.button("保存上限", key="lim_save"):
        cfg["daily_call_limit"] = int(new_lim)
        write_text(CONFIG_PATH, json.dumps(cfg, ensure_ascii=False, indent=2))
        st.success("已保存。部署版也可以在 Secrets 里加 `DAILY_CALL_LIMIT = \"100\"` 覆盖。")
    st.markdown("---")
    st.markdown("##### 连接测试")
    if st.button("🔌 测试 API 连接"):
        with st.spinner("测试中…"):
            try:
                st.success(f"连接正常：{ask_chat('只回复两个字：正常')[:50]}")
            except Exception as e:
                st.error(str(e))
    st.markdown("---")
    st.caption("部署到 Streamlit Cloud：Settings → Secrets 填入 "
               "`DEEPSEEK_API_KEY = \"sk-...\"` 即可。")
    st.markdown("---")
    st.caption("分享链接、名片页、简历导出都在「📇 展示」页；"
               "照片、简历正文和模板在「🎯 找工作 → 简历」页。")
    st.markdown("---")
    st.markdown("##### 🔒 访问密码（上线公网前设置）")
    st.caption("设置后访问应用需要先输密码。密码以 SHA-256 哈希保存在本机 config.json，"
               "不存明文；部署时也可用 Secrets 的 `APP_PASSWORD`。")
    cur_pw = st.text_input("设置/修改访问密码（留空 = 清除密码）", type="password",
                           key="set_pw")
    if st.button("保存密码", key="set_pw_save"):
        if cur_pw.strip():
            cfg["app_password_hash"] = v41.hash_password(cur_pw.strip())
            write_text(CONFIG_PATH, json.dumps(cfg, ensure_ascii=False, indent=2))
            st.success("访问密码已设置（哈希保存）。")
        else:
            cfg.pop("app_password_hash", None)
            write_text(CONFIG_PATH, json.dumps(cfg, ensure_ascii=False, indent=2))
            st.success("已清除访问密码。")


# ============================================================
# 入口
# ============================================================


def page_compare():
    """多个岗位并排对比。"""
    hero("岗位对比", "选 2-4 个岗位并排比：匹配度、五维评分、岗位质量、城市薪资")
    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    if len(jobs) < 2:
        st.info("至少要有 2 个岗位才能对比。先去「岗位库 / 关键词搜岗」加几个。")
        return
    names_all = [j[0] for j in jobs]
    picks = st.multiselect("选择岗位（2 到 4 个）", names_all,
                           default=names_all[:min(2, len(names_all))], key="cmp_pick")
    if len(picks) < 2:
        st.info("至少选 2 个岗位。")
        return
    meta_map = dict((j[0], j[1]) for j in jobs)
    rows = []
    for name in picks[:4]:
        meta = meta_map[name]
        report = read_text(MATCH_DIR / f"match_{name}.md")
        dims = extract_dim_scores(report) or {}
        jd = read_text(JDS_DIR / f"{name}.txt")
        q = job_quality.assess({"jd": jd, "company": meta.get("company", ""),
                                "city": meta.get("city", ""),
                                "url": meta.get("source_url", "")})
        rows.append({
            "岗位": name,
            "公司": meta.get("company") or "-",
            "城市": meta.get("city") or "-",
            "匹配度": meta.get("match_score") or "-",
            "岗位质量": q["score"],
            "质量结论": q["verdict"],
            "技术栈": dims.get("技术栈", "-"),
            "项目匹配": dims.get("项目匹配", "-"),
            "背景": dims.get("背景", "-"),
            "地点": dims.get("地点", "-"),
            "时长": dims.get("时长", "-"),
        })
    st.dataframe(rows, use_container_width=True)
    st.caption("匹配度来自「匹配分析」的报告；岗位质量来自规则检查（0-100，越高越可信）。"
               "没跑过匹配的岗位匹配度会显示 -。")
    for name in picks[:4]:
        report = read_text(MATCH_DIR / f"match_{name}.md")
        if report:
            with st.expander(f"{name} 的结论"):
                m = re.search(r"## 结论\s*\n+(.+)", report)
                st.markdown(m.group(1).strip() if m else "（报告里没找到结论段）")


def page_company():
    """公司速查（结论可信度较低，界面上显著提示）。"""
    hero("公司速查", "投之前先看一眼这家公司的公开线索（结论是线索，不是事实）")
    st.warning("这个功能的输出**可信度明显低于其它功能**：数据来自公开网页抓取 + 模型总结，"
               "可能过时或不完整。工商/融资/口碑没有权威免费接口，拿不到准数。"
               "**结论只能当线索，不要据此判断公司好坏。**")
    company = st.text_input("公司名", key="co_input", placeholder="例如：蔚蓝智能")
    if st.button("🔎 查一下（抓公开页面，约 20 秒）", type="primary"):
        if not company.strip():
            st.warning("先填公司名")
            return
        with st.spinner("抓公开页面 + 提取线索…"):
            try:
                st.session_state["co_out"] = company_lookup.lookup(
                    company.strip(), lambda p: ask_chat(p))
            except Exception as e:
                st.error(str(e))
    out = st.session_state.get("co_out")
    if not out:
        return
    if not out["report"]:
        st.error("没抓到可用的公开页面。可以换个公司全称再试，或者跳过这项直接投。")
        return
    st.markdown(out["report"])
    with st.expander("看抓到的原始来源（可自己核对）"):
        for url, text in out["sources"]:
            st.markdown(f"**{url}**")
            st.text(text[:1200])


def page_drill():
    """面试拷问：AI 当面试官，逐题点评。"""
    hero("面试拷问", "AI 当面试官追问你；每答一题给三段反馈。可中断续答")
    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    if not jobs:
        st.info("先到「🎯 找工作 → 岗位库」添加岗位")
        return
    name = st.selectbox("针对哪个岗位练", [j[0] for j in jobs], key="drill_pick")
    jd = read_text(JDS_DIR / f"{name}.txt")
    profile = read_text(PROFILE_PATH) or read_text(ME_PATH)
    state = interview_drill.load_state(name)

    c1, c2 = st.columns([1, 1])
    if c1.button("🎤 生成 10 个追问（调用 DeepSeek）", type="primary"):
        with st.spinner("面试官在想问题…"):
            try:
                text, qs = interview_drill.make_questions(profile, jd,
                                                          lambda p: ask_chat(p))
                state["questions"] = text
                state["items"] = [{"q": q, "a": "", "f": ""} for q in qs]
                interview_drill.save_state(state)
                st.rerun()
            except Exception as e:
                st.error(str(e))
    if c2.button("↺ 重来（清空这个岗位的记录）"):
        state = {"job": name, "questions": "", "items": []}
        interview_drill.save_state(state)
        st.rerun()

    items = state.get("items") or []
    if not items:
        st.caption("点上面的按钮开始。生成的题目会存在本地，明天回来接着答。")
        return

    answered = sum(1 for it in items if it.get("a", "").strip())
    st.progress(answered / len(items), text=f"已答 {answered} / {len(items)} 题")
    for i, it in enumerate(items):
        with st.expander(f"{i + 1}. {it['q'][:60]}", expanded=(i == answered)):
            ans = st.text_area("你的回答", it.get("a", ""), key=f"ans_{name}_{i}", height=110)
            if st.button(f"提交第 {i + 1} 题并要反馈", key=f"fb_{name}_{i}"):
                if not ans.strip():
                    st.warning("先写点内容")
                else:
                    with st.spinner("面试官在点评…"):
                        try:
                            it["a"] = ans.strip()
                            it["f"] = interview_drill.feedback(it["q"], it["a"],
                                                               lambda p: ask_chat(p))
                            interview_drill.save_state(state)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
            if it.get("f"):
                st.markdown(it["f"])

    if answered == len(items):
        if st.button("📋 生成总评（最危险的三个问题 + 该补的一件事）", type="primary"):
            with st.spinner("汇总中…"):
                try:
                    st.session_state[f"drill_review_{name}"] = interview_drill.total_review(
                        items, lambda p: ask_chat(p))
                except Exception as e:
                    st.error(str(e))
        if st.session_state.get(f"drill_review_{name}"):
            st.markdown(st.session_state[f"drill_review_{name}"])
        st.markdown("---")
        st.caption("把这轮拷问存进复盘库，数字分身就能拿它调整以后的回答（存本地，不上传）。")
        if st.button("💾 存进复盘库（数字分身据此进化）", key=f"drill_save_{name}"):
            lines = []
            for i, it in enumerate(items, 1):
                lines.append(f"Q{i}. {it['q']}")
                if it.get("a"):
                    lines.append(f"我的回答：{it['a']}")
            if st.session_state.get(f"drill_review_{name}"):
                lines.append("\n【模拟面试总评】\n"
                             + st.session_state[f"drill_review_{name}"])
            body = "\n".join(lines) + "\n\n（来源：面试拷问模式·模拟练习）"
            meta_board = dict((j[0], j[1]) for j in jobs)
            digital_twin.save_review(name, meta_board.get(name, {}).get("company", ""), body)
            st.success(f"已存进复盘库：{name}")
        st.caption("去「🧬 我的 → 复盘入库」能看到它，"
                   "点「提炼画像更新」会给你画像修改建议。")


def page_applications():
    """投递记录：每一条投了什么、用了什么话术、该跟进谁。

    统计口径统一收敛到「今天 → 数据与日志」那一页，这里只记录事实，避免同一个数字
    在三个页面各算一遍。
    """
    hero("投递记录", "每一条投了什么、用了什么话术、该跟进谁")
    rows = apply_assist.load_applications()
    all_jobs = list_jobs()
    applied_jobs = [j for j in all_jobs
                    if j[1]["status"] in ("已投", "面试中", "已拒", "Offer")]
    st.caption(f"共 {len(rows)} 条记录。漏斗和趋势在「🚀 今天 → 数据与日志」里看。")

    # 跟进提醒
    follow = pipeline.needs_followup(all_jobs, days=7)
    if follow:
        st.markdown("### ⏰ 该跟进了（投出去超过 7 天没更新状态）")
        for f in follow[:8]:
            st.markdown(f"- **{f['meta'].get('company') or f['name']}** · {f['name']}"
                        f" · 已投 {f['days']} 天")
        st.caption("跟进话术去「投递台 → 单条精修」用「内推消息」或「BOSS 打招呼」模板改写。")
    else:
        st.caption("暂时没有需要跟进的岗位（投出去满 7 天会自动出现在这里）。")

    # 邮件 / 消息 → 状态识别（粘贴式，不接邮箱）
    with st.expander("📨 收到邮件或消息？粘贴进来，帮你判断该怎么改状态"):
        st.caption("不接邮箱、不要授权。你把内容粘进来，程序判断类型并给改状态的建议。"
                   "内容不会上传保存，除非你自己点保存。")
        mail = st.text_area("粘贴邮件或聊天内容", key="inbox_text", height=160,
                            placeholder="例：您好，我们想邀请您参加线上技术面试，时间定在……")
        if st.button("🔎 判断这是什么消息", key="inbox_go"):
            if not mail.strip():
                st.warning("先粘贴内容")
            else:
                with st.spinner("判断中…"):
                    try:
                        info = inbox_parse.classify(mail, lambda p: ask_chat(p))
                        st.session_state["inbox_out"] = info
                    except Exception as e:
                        st.error(str(e))
        info = st.session_state.get("inbox_out")
        if info:
            st.success(f"类型：**{info['type']}**"
                       f"{'　公司：' + info['company'] if info['company'] else ''}"
                       f"{'　岗位：' + info['job'] if info['job'] else ''}"
                       f"{'　时间：' + info['time'] if info['time'] else ''}")
            st.info("建议：" + info["hint"])
            st.caption("改状态请去「岗位」→ 岗位库，或「今日」里点对应岗位的按钮。"
                       "程序不会自动改，避免误判。")

    # 被拒归因
    rejected = [r for r in rows if r.get("status") == "已拒"]
    rejected_names = [n for n, m, _ in all_jobs if m.get("status") == "已拒"]
    if rejected_names:
        st.markdown("### 🔍 被拒归因")
        st.caption(f"库里标记为「已拒」的岗位有 {len(rejected_names)} 个。"
                   "连续被拒 3 个以上时，归因才有参考价值。")
        if len(rejected_names) >= 3:
            if st.button("分析这些被拒岗位的共同点（调用 DeepSeek）"):
                with st.spinner("分析中…"):
                    try:
                        recs = [{"job": n, "company": m.get("company"),
                                 "score": m.get("match_score"), "note": ""}
                                for n, m, _ in all_jobs if m.get("status") == "已拒"]
                        st.session_state["reject_analysis"] = pipeline.analyze_rejections(
                            recs, lambda p: ask_chat(p))
                    except Exception as e:
                        st.error(str(e))
            if st.session_state.get("reject_analysis"):
                st.markdown(st.session_state["reject_analysis"])
        else:
            st.info(f"现在只有 {len(rejected_names)} 个「已拒」，再多几个再跑归因。")

    if not rows and not applied_jobs:
        st.info("还没有投递记录。去「🚀 今日」投第一家，投完点「标记已投」就会记在这里。")
        return

    if rows:
        st.markdown("### 投递流水")
        for r in rows[:30]:
            with st.expander(f"**{r.get('company') or r['job']}** · {r['job']} · "
                             f"{r.get('time', '')[:16]}"
                             f"{' · 匹配度 ' + str(r['score']) if r.get('score') else ''}"):
                if r.get("url"):
                    st.caption("岗位链接：" + r["url"])
                if r.get("talk"):
                    st.markdown("**当时发的话术**")
                    st.code(r["talk"], language="text")
                else:
                    st.caption("没存话术（当时可能没用工具生成）")
                if r.get("note"):
                    st.caption("备注：" + r["note"])

    if applied_jobs:
        st.markdown("### 岗位库里的投递状态")
        for name, meta, _ in applied_jobs:
            st.markdown(
                f"- {status_tag(meta.get('status', '已投'))} **{meta.get('company') or name}**"
                f" · {name}"
                f"{' · 匹配度 ' + str(meta.get('match_score')) if meta.get('match_score') else ''}"
                f"{' · ' + meta.get('applied_at', '')[:16] if meta.get('applied_at') else ''}",
                unsafe_allow_html=True)


# ============================================================
# 导航：用 Streamlit 原生多页（st.navigation）
# 为什么换掉自定义导航：
#   1. 原生导航有真实 URL（/resume、/apply…）→ 可刷新、可前进后退、可分享
#   2. 侧边栏是真·两级树（分区标题 + 页），不再是"横排按钮组"那种说不清层级的东西
#   3. 跨页跳转用 st.switch_page，不用再靠 session_state 里塞"待跳转标记"
# 规则不变：一个动作只有一个入口；同一个数字只有一个出处。
# ============================================================
```

## ===== offeragent/pages_twin.py（413 行）=====

```python
# -*- coding: utf-8 -*-
"""公开数字名片 —— OfferAgent 页面域模块（2026-09-29 从 offer_agent_app.py 拆出）"""
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

AVATAR_CANDIDATES = [
    BASE_DIR / "assets" / "avatar.png",
    BASE_DIR / "assets" / "avatar.jpg",
    BASE_DIR / "assets" / "avatar.jpeg",
    BASE_DIR.parent / "简历" / "照片.jpg",
    BASE_DIR.parent / "简历" / "照片.png",
    BASE_DIR.parent / "简历" / "头像.jpg",
    BASE_DIR.parent / "简历" / "头像.png",
]


def find_avatar():
    """找本人照片：放在 offeragent/assets/avatar.jpg 或 简历/照片.jpg 都会被自动用上。"""
    for p in AVATAR_CANDIDATES:
        if p.exists() and p.is_file():
            return p
    return None


def avatar_bytes():
    p = find_avatar()
    if not p:
        return None
    try:
        return p.read_bytes()
    except Exception:
        return None


def public_base_url() -> str:
    """当前部署的公开地址（用于生成「分享/转载」链接）。"""
    try:
        u = str(getattr(st.context, "url", "") or "")
        if u.startswith("http"):
            return u.split("?")[0].rstrip("/")
    except Exception:
        pass
    return "https://ai-learning-c62pgpcfp7us6rztelatpj.streamlit.app"


RAG_APP_URL = "https://ai-learning-fphncazxmg3pnesntwchz6.streamlit.app/"
GITHUB_URL = "https://github.com/yjmyp/ai-learning"
CONTACT_EMAIL = "yj2994762833@gmail.com"
PRESET_QUESTIONS = [
    "介绍下你的 RAG 项目，做了什么、做到什么程度？",
    "你做过 Agent 相关的东西吗？",
    "你的网络工程背景对做 AI 应用有什么帮助？",
    "你怎么评估你的 RAG 系统效果？",
    "你最大的短板是什么？",
    "为什么想投 AI 应用开发实习？",
]


def _twin_answer(profile: str, question: str) -> str:
    return digital_twin.twin_answer(profile, question, lambda p: ask_chat(p))


def _resume_pdf_path():
    """名片页下载按钮用的 PDF：优先新的 v3，其次旧版。"""
    for fn in ("余剑-简历-AI应用开发实习-v3.pdf",
               "余剑-应聘AI应用开发实习-本科.pdf"):
        p = BASE_DIR.parent / "简历" / fn
        if p.exists():
            return p
    return None


def page_twin_portal():
    """公开数字名片页（?twin=1）。免密，给 HR / 考官知情访问。

    结构：① 名片头（照片 + 标签 + 一条分享链接）→ ② 直接问数字人 → ③ 我是谁 / 项目证据。
    合并原三个 tab 的原因：把「能对话」放首屏，简历式信息往后放，更像名片而不是简历页。
    """
    profile = read_text(PROFILE_PATH) or read_text(ME_PATH)
    me = read_text(ME_PATH)
    if not profile.strip():
        st.warning("画像还没生成，名片页暂不可用。")
        st.caption("（给余剑本人：进主界面 →「🧬 我的 → 自我蒸馏」答完 15 题即可）")
        return

    av = avatar_bytes()
    pdf = _resume_pdf_path()
    twin_url = public_base_url() + "/?twin=1"

    # ── ① 名片头 ───────────────────────────────────────────
    with st.container(border=True):
        c1, c2 = st.columns([1, 4], vertical_alignment="center")
        with c1:
            if av:
                st.image(av, width=132)
            else:
                st.markdown(
                    '<div style="width:132px;height:132px;border-radius:50%;'
                    'background:linear-gradient(135deg,#5558D6,#1B2A4A);color:#fff;'
                    'display:flex;align-items:center;justify-content:center;'
                    'font-size:46px;font-weight:700;">余</div>',
                    unsafe_allow_html=True)
        with c2:
            st.markdown("## 余剑 · AI 应用开发实习生")
            with st.container(horizontal=True):
                st.badge("南京邮电大学", icon=":material/school:", color="blue")
                st.badge("网络工程 · 2027 届", icon=":material/badge:", color="gray")
                st.badge("南京 / 可远程", icon=":material/location_on:", color="green")
                st.badge("2026.09 下旬可到岗", icon=":material/event_available:", color="violet")
            st.caption("LLM 应用 · RAG 检索增强 · Agent 工具调用。"
                       "下面每个数字都能现场演示，不靠形容词。")
            with st.container(horizontal=True):
                st.link_button("RAG 应用（在线）", RAG_APP_URL, icon=":material/open_in_new:")
                st.link_button("GitHub 代码", GITHUB_URL, icon=":material/code:")
                if pdf:
                    st.download_button("简历 PDF", pdf.read_bytes(),
                                       file_name=pdf.name, mime="application/pdf",
                                       key="twin_pdf_head", icon=":material/download:")
                with st.popover("分享 / 转载此名片", icon=":material/share:"):
                    st.caption("把下面这个链接发给 HR、同学或群里，对方打开就是你正在看的这页，"
                               "**不需要密码**：")
                    st.code(twin_url, language=None)
                    st.caption("链接里的 `?twin=1` 是关键，它免密。不带这个参数的主链接是要密码的，"
                               "那是余剑自己用的工作台。")
                    if av is None:
                        st.caption("（给本人：把照片放到 `简历/照片.jpg` 或 "
                                   "`offeragent/assets/avatar.png` 并提交到 GitHub，"
                                   "这张名片就会自动带上头像。）")

    # ── ② 直接问数字人（主入口） ────────────────────────────
    st.markdown("#### 有问题直接问他")
    st.caption("回答由 AI 基于他的真实画像实时生成；画像里没写过的事，它会直接说没有。"
               "AI 生成内容可能有误，正式信息以本人沟通为准。")
    if "twin_chat" not in st.session_state:
        st.session_state["twin_chat"] = []
    if not st.session_state["twin_chat"]:
        picked = st.pills("常见问题（点一下就问）", PRESET_QUESTIONS,
                          label_visibility="collapsed", key="twin_pills")
        if picked:
            st.session_state["twin_chat"].append({"role": "user", "content": picked})
            st.rerun()
    for msg in st.session_state["twin_chat"]:
        who = "assistant" if msg["role"] == "assistant" else "user"
        with st.chat_message(who, avatar=(av if who == "assistant" else None)):
            st.markdown(msg["content"])
    question = st.chat_input("问点什么，比如：你的 RAG 系统怎么评估效果？")
    if question:
        st.session_state["twin_chat"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant", avatar=av):
            try:
                with st.spinner("数字分身正在按他的画像回答…"):
                    ans = _twin_answer(profile, question)
            except Exception as e:
                ans = f"（回答问题失败：{e}）"
            st.markdown(ans)
        st.session_state["twin_chat"].append({"role": "assistant", "content": ans})

    # ── ③ 我是谁 / 项目证据 ────────────────────────────────
    tab_who, tab_proof = st.tabs(["我是谁", "项目证据"])
    with tab_who:
        cols = st.columns(4, vertical_alignment="top")
        for col, (k, v) in zip(cols, [
                ("学历", "南京邮电大学\n网络工程 · 本科"),
                ("届别", "2027 届\n2026.09 下旬起可实习"),
                ("求职方向", "AI 应用开发\nAgent 开发 / 大模型评测"),
                ("坐标", "南京优先\n可远程 · 4-5 天/周")]):
            col.markdown(f"**{k}**\n\n{v}")
        st.space("small")
        with st.container(border=True):
            st.markdown("**技术栈**")
            st.markdown("Python · RAG（向量检索 + TF-IDF 重排）· Agent 工具调用（JSON 协议 + "
                        "参数合同校验）· Chroma · bge-small-zh-v1.5 · FastAPI · Streamlit · Git")
        with st.expander("详情（技能、项目、求职约束原文）"):
            body = me
            for mark in ["## 硬约束", "## 我想找什么岗位"]:
                i = body.find(mark)
                if i > 0:
                    body = body[:i]
            st.markdown(body or profile)
        st.caption(f"联系方式：{CONTACT_EMAIL}")

    with tab_proof:
        st.caption("每个链接都能点开验证；所有数字来自他自己的评估集，可以现场跑给你看。")
        with st.container(border=True):
            st.markdown("**RAG 知识库问答系统 · 已上线**")
            with st.container(horizontal=True):
                st.badge("254 块向量库", color="blue")
                st.badge("top-5 命中 92%", color="green")
                st.badge("带引用溯源", color="gray")
            st.caption("11 篇资料 → 300 字/块切分（重叠 50）→ bge 向量化 → Chroma → top-k 召回 "
                       "→ TF-IDF 重排 → DeepSeek 生成。自建 12 条评估集，量化 top-1/3/5 = "
                       "75% / 83% / 92%。")
            st.link_button("打开应用", RAG_APP_URL, icon=":material/open_in_new:")
        with st.container(border=True):
            st.markdown("**Agent 工具调用（工程化细节）**")
            with st.container(horizontal=True):
                st.badge("5 类坏输出拦截", color="orange")
                st.badge("错误回填自纠错", color="gray")
            st.caption("JSON 协议工具调用 + 参数合同校验：未知工具 / 缺参 / 类型错 / 非对象 / "
                       "非法 JSON 五类坏调用都挡在模型外面，失败时把错误回填给模型自纠错。")
        with st.container(border=True):
            st.markdown("**OfferAgent 求职智能体 · 这张名片就是它的一部分**")
            with st.container(horizontal=True):
                st.badge("自我蒸馏 → 岗位匹配 → 投递 → 复盘", color="violet")
            st.caption("求职工作台：自我蒸馏 15 题生成画像、岗位匹配与 ATS 覆盖检查、"
                       "投递话术（禁模板腔自动校验）、面试拷问、复盘进化。"
                       "工具体系里最花心思的一条：生成归工具，发送归人。")
        with st.container(border=True):
            st.markdown("**代码与简历**")
            with st.container(horizontal=True):
                st.link_button("GitHub 仓库", GITHUB_URL, icon=":material/code:")
                if pdf:
                    st.download_button("下载简历 PDF", pdf.read_bytes(),
                                       file_name=pdf.name, mime="application/pdf",
                                       key="twin_pdf_body", icon=":material/download:")
                else:
                    st.caption("（简历可邮件索取）")

    st.caption("以上内容由 AI 基于余剑的真实素材生成，可能存在错漏，正式信息以本人沟通为准。"
               "你的提问只用于当场回答，不写入他的数据文件。")


# ============================================================
# 页面：数字分身（合规版：替你准备，真人上场）
# ============================================================
def twin_practice_section(profile: str):
    """分身陪练：拿画像当记忆，练参考话术、准备自我介绍和反问清单。"""
    hero("分身陪练", "它用你的画像当记忆，替你先答一版；真人上场的是你")
    if not profile.strip():
        st.warning("先去「🧬 我的 → 自我蒸馏」生成画像，分身才有记忆。")
        if st.button("现在去蒸馏", key="to_distill"):
            goto_page("distill")
        return
    with st.expander("📄 分身当前记忆（画像全文）", expanded=False):
        st.markdown(profile)
    st.markdown("##### 让分身替你答一版")
    st.caption("这是参考话术，不是替考。你本人上场时用自己的话说会更自然。")
    q = st.text_area("你的问题（面试里卡住的问题也可以扔给它）", key="twin_q",
                     placeholder="例：你的 RAG 系统如果检索出来全是错的，怎么办？")
    if st.button("让分身回答", type="primary", key="twin_go"):
        with st.spinner("分身思考中…"):
            try:
                st.session_state["twin_a"] = digital_twin.twin_answer(
                    profile, q.strip(), lambda p: ask_chat(p))
            except Exception as e:
                st.error(str(e))
    a = st.session_state.get("twin_a", "")
    if a:
        st.markdown(f'<div class="oa-card">💬 分身：{a}</div>', unsafe_allow_html=True)
        st.caption("对照你自己的答法：它哪里更具体？哪句你没想到？")

    st.markdown("---")
    st.markdown("##### 投前定制（自我介绍 / 反问清单）")
    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    if jobs:
        iname = st.selectbox("选择岗位", [j[0] for j in jobs], key="twin_job")
        icomp = dict((j[0], j[1].get("company") or j[0]) for j in jobs)[iname]
        ijd = read_text(JDS_DIR / f"{iname}.txt")
        c1, c2 = st.columns(2)
        if c1.button("生成自我介绍（30s/60s/90s）", key="intro_go"):
            with st.spinner("定制中…"):
                try:
                    st.session_state["intro_out"] = digital_twin.make_intro(
                        profile, icomp, ijd, lambda p: ask_chat(p))
                except Exception as e:
                    st.error(str(e))
        if c2.button("生成反问清单（10 问）", key="askback_go"):
            with st.spinner("生成中…"):
                try:
                    st.session_state["askback_out"] = digital_twin.questions_to_ask(
                        profile, ijd, lambda p: ask_chat(p))
                except Exception as e:
                    st.error(str(e))
        if st.session_state.get("intro_out"):
            st.markdown(st.session_state["intro_out"])
        if st.session_state.get("askback_out"):
            st.markdown(st.session_state["askback_out"])
    else:
        st.caption("先到「🎯 找工作 → 岗位库」添加岗位，才能按目标公司定制。")


def twin_review_section(profile: str):
    """复盘入库：面试后记下来，提炼成画像更新建议，让分身越用越准。"""
    hero("复盘入库", "每场面试后花 2 分钟记下来，分身提炼画像更新建议")
    if not profile.strip():
        st.warning("先去「🧬 我的 → 自我蒸馏」生成画像。")
        return
    rjobs = [(n, m) for n, m, _ in list_jobs() if m["status"] != "排除"]
    rname = st.selectbox("复盘哪个岗位", [n for n, _ in rjobs] if rjobs else [""],
                         key="rev_job")
    rcomp = dict(rjobs).get(rname, "")
    rtext = st.text_area("复盘内容（问了什么 / 哪里卡住 / 对方反应 / 你答得怎么样）",
                         key="rev_text", height=140)
    if st.button("保存复盘 + 提炼画像更新", type="primary", key="rev_save"):
        if not rtext.strip():
            st.warning("先写复盘内容")
        else:
            digital_twin.save_review(rname, rcomp, rtext)
            with st.spinner("提炼画像更新建议…"):
                try:
                    st.session_state["rev_adv"] = digital_twin.evolve_profile(
                        profile, rtext, lambda p: ask_chat(p))
                    st.session_state["rev_done"] = True
                except Exception as e:
                    st.error(str(e))
    if st.session_state.get("rev_done"):
        st.success(f"已保存复盘：{rname}")
    if st.session_state.get("rev_adv"):
        st.markdown(st.session_state["rev_adv"])
        st.caption("（更新建议由你确认后再手动写进画像/简历，分身不会自动改你的画像）")
    reviews = digital_twin.load_reviews()
    if reviews:
        with st.expander(f"📚 历史复盘（{len(reviews)} 条）"):
            for r in reviews[:20]:
                st.markdown(f"**{r['company'] or r['job']}** · {r['date']}")
                st.caption((r["review"] or "")[:200])
    st.markdown("---")
    st.markdown("##### 📡 反向岗位雷达")
    st.caption("从你的画像反推「哪些岗位类型最适合你、搜什么关键词、去哪投」。")
    if st.button("从画像反推适合我的岗位类型", key="radar_go"):
        with st.spinner("分析中…"):
            try:
                st.session_state["radar_out"] = digital_twin.job_radar(
                    profile, lambda p: ask_chat(p))
            except Exception as e:
                st.error(str(e))
    if st.session_state.get("radar_out"):
        st.markdown(st.session_state["radar_out"])


def page_show():
    """对外展示：HR 会看到的都在这一页（名片链接、简历 PDF、素材自检）。"""
    hero("对外展示", "HR 会看到的都在这一页：公开名片、简历 PDF、分享链接")
    base = public_base_url()
    twin_url = base + "/?twin=1"
    av = find_avatar()
    pdf = _resume_pdf_path()

    with st.container(border=True):
        st.markdown("#### 对外素材自检")
        items = [
            ("个人照片", bool(av), "简历和名片都用这一张"),
            ("个人画像", PROFILE_PATH.exists(), "生成过一次就行"),
            ("我的简历", MY_RESUME_PATH.exists(), "保存过就算就绪"),
            ("简历 PDF", bool(pdf), "HR 下载的就是这份"),
        ]
        cols = st.columns(4)
        for col, (label, ok, hint) in zip(cols, items):
            col.markdown(f"**{label}**\n\n" + ("✅ 已就绪" if ok else "❌ 还没有"))
            col.caption(hint)
        if not all(ok for _, ok, _ in items):
            if st.button("去补齐（照片 / 简历 / 模板）", key="show_fix"):
                goto_page("resume")

    with st.container(border=True):
        st.markdown("#### 公开数字名片（免密）")
        st.caption("发给 HR、同学或群里，对方打开就是你自己的 AI 名片页，不需要密码。"
                   "右边有复制按钮。")
        st.code(twin_url, language=None)
        with st.container(horizontal=True):
            st.link_button("打开看看 HR 看到的样子", twin_url,
                           icon=":material/open_in_new:")
            if pdf:
                st.download_button("下载简历 PDF", pdf.read_bytes(),
                                   file_name=pdf.name, mime="application/pdf",
                                   key="show_pdf", icon=":material/download:")

    with st.container(border=True):
        st.markdown("#### 简历 PDF")
        if pdf:
            st.caption(f"当前对外的是：{pdf.name}（三种模板都在「找工作 → 简历」里切换，"
                       "换完用 make_resume_pdf.py 重新导出）")
        else:
            st.caption("还没有导出过 PDF。")
        if st.button("去换模板 / 重新导出", key="show_tpl"):
            goto_page("resume")

    with st.container(border=True):
        st.markdown("#### 你自己的工作台（要密码）")
        st.code(base + "/", language=None)
        st.caption("这条是主链接，有密码保护。对外只发上面那条带 `?twin=1` 的。")
```

## ===== offeragent/pages_agent.py（199 行）=====

```python
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
```

## ===== offeragent/pages_match.py（209 行）=====

```python
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
```
