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
import privacy_tools
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

    # ---------------- 隐私与数据（上线给陌生人用之前的合规要求） ----------------
    st.markdown("---")
    st.markdown("##### 🔐 隐私与数据（你的数据在哪、怎么带走、怎么删）")
    st.caption("你在本应用里输入的一切（简历、画像、岗位库、投递记录、复盘）都只存在**运行这个应用的机器**上的 "
               "`offeragent/data/` 目录，不会上传到开发者服务器；只有调用模型时，相关文本会发给 DeepSeek API。"
               "不想用了就一键带走或一键清空。")
    try:
        _sum = privacy_tools.data_summary()
        st.caption(f"当前数据：**{_sum['files']} 个文件 / {_sum['mb']} MB**　"
                   f"（{_sum['dir']}）")
    except Exception as _e:
        st.caption(f"数据目录读取失败：{_e}")

    _c1, _c2 = st.columns(2)
    with _c1:
        if st.button("📦 打包我的全部数据", key="priv_export"):
            try:
                st.session_state["_priv_blob"] = privacy_tools.export_bytes()
            except Exception as _e:
                st.error(f"导出失败：{_e}")
        if st.session_state.get("_priv_blob"):
            st.download_button("⬇️ 下载 zip 备份", st.session_state["_priv_blob"],
                               file_name=privacy_tools.export_filename(),
                               mime="application/zip", key="priv_dl")
    with _c2:
        _confirm = st.text_input('要清空全部数据，请先输入「删除」两个字',
                                 key="priv_confirm")
        if st.button("🗑️ 删除我的全部数据", key="priv_del"):
            if _confirm.strip() == "删除":
                try:
                    _nf, _nd = privacy_tools.purge()
                    st.session_state.pop("_priv_blob", None)
                    st.success(f"已清空：删除 {_nf} 个文件 / {_nd} 个子目录。刷新页面即从空数据开始。")
                except Exception as _e:
                    st.error(f"清空失败：{_e}")
            else:
                st.warning("没执行：确认框里要输入「删除」两个字。")
    st.caption("提示：清空会删掉简历、画像、岗位库、投递记录等全部个人数据，"
               "但保留本机配置（API Key / 主题 / 每日目标）。"
               "数据目录在 `offeragent/data/`，也可以直接在文件管理器里删。")


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
