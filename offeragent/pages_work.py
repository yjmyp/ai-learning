# -*- coding: utf-8 -*-
"""画像与岗位库 —— OfferAgent 页面域模块（2026-09-29 从 offer_agent_app.py 拆出）"""
import json
import os
import re
import time
from pathlib import Path

import streamlit as st

# 分层公共层 + 业务子模块（宽 import 兜底，页面函数保持原名调用）
from store import *
from prompts import PROMPT_PROFILE, PROMPT_MATCH
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

def page_profile():
    hero("我的画像", "Self-Distill：先认识自己，再做匹配")
    ensure_dirs()
    me_text = read_text(ME_PATH)
    tab_distill, tab1, tab2 = st.tabs(["🧬 自我蒸馏（推荐）", "✏️ 编辑素材", "⚡ 直接生成画像"])

    with tab_distill:
        st.caption("分 5 轮 15 题，用提问的方式把你蒸馏成 6 份档案："
                   "画像 / 亮点库 / 面试答案 / 差距清单 / **工作与学习模式说明书** / **数字分身说明书**。"
                   "可以随时中断，关了页面下次接着填。")
        state = distill.load_state()
        done, total, pct = distill.progress(state)
        st.progress(pct / 100, text=f"已填 {done}/{total} 题（{pct}%）")

        for i, (round_name, hint, qs) in enumerate(distill.ROUNDS):
            answered = sum(1 for k, _ in qs if state["answers"].get(k, "").strip())
            with st.expander(f"第 {i + 1} 轮 · {round_name}（{answered}/{len(qs)}）",
                             expanded=(answered < len(qs))):
                st.caption(hint)
                for key, q in qs:
                    val = st.text_area(q, state["answers"].get(key, ""), key=f"da_{key}", height=90)
                    if val != state["answers"].get(key, ""):
                        state["answers"][key] = val
                        distill.save_state(state)

                if st.button(f"🤔 让我追问一句（第 {i + 1} 轮）", key=f"fu_{i}"):
                    with st.spinner("看看哪句最含糊…"):
                        fu = distill.make_followup(state, i, lambda p: ask_chat(p))
                    if fu and "够了" not in fu:
                        st.session_state[f"fu_text_{i}"] = fu
                    else:
                        st.session_state[f"fu_text_{i}"] = ""
                if st.session_state.get(f"fu_text_{i}"):
                    st.info("追问：" + st.session_state[f"fu_text_{i}"])
                    reply = st.text_area("回答这个追问", key=f"fur_{i}", height=80)
                    if reply.strip() and st.button("💾 存下这条补充", key=f"fus_{i}"):
                        state.setdefault("followups", {})[f"第{i + 1}轮"] = reply.strip()
                        distill.save_state(state)
                        st.success("已存下")

        st.divider()
        if pct < 100:
            st.warning(f"还有 {total - done} 题没填。填完再生成，档案质量差很多；"
                       "实在写不出可以先跳过，但生成时那部分会是空的。")
        if st.button("🧬 生成 6 份档案（调用 DeepSeek）", type="primary"):
            with st.spinner("蒸馏中…"):
                try:
                    outputs = distill.distill(state, lambda p: ask_chat(p))
                    st.success("已生成：" + "、".join(outputs.keys()))
                    for name, content in outputs.items():
                        with st.expander(f"看 {name}"):
                            st.markdown(content)
                except Exception as e:
                    st.error(str(e))
        if (DATA_DIR / "profile.md").exists():
            st.caption("生成后的 profile.md 会自动被「匹配分析」使用；"
                       "highlights.md 会被「投递话术」参考；"
                       "clone_brief.md 是数字分身说明书（面试讲 Self-Distill 时直接用这个）。")

    with tab1:
        st.caption("维护你的原始素材（me.txt）：会什么、做过什么、硬约束。每次改动自动保存。")
        new_text = st.text_area("me.txt 原始素材", me_text, height=420, key="me_editor")
        if st.button("💾 保存素材", type="primary"):
            write_text(ME_PATH, new_text)
            st.success("素材已保存")
    with tab2:
        st.caption("基于素材生成结构化画像 profile.md（匹配分析的输入）。")
        if st.button("🧬 生成画像（调用 DeepSeek）", type="primary"):
            with st.spinner("生成中…"):
                try:
                    profile = ask_chat(PROMPT_PROFILE, new_text or me_text)
                    write_text(PROFILE_PATH, profile)
                    st.success("画像已生成并保存")
                    st.markdown(profile)
                except Exception as e:
                    st.error(str(e))
        current = read_text(PROFILE_PATH)
        if current:
            with st.expander("查看当前 profile.md"):
                st.markdown(current)


def _as_dict(value) -> dict:
    """把 session_state 里读出来的值当 dict 用之前先验一下类型。

    为什么需要：session_state 是跨多次运行留着的，一旦某次写进去的
    **不是 dict**（写错类型、或 key 撞上控件导致存进去的是控件值），
    下一轮渲染就会炸成 `AttributeError: 'list' object has no attribute 'items'` ——
    而这种错整页都会挂。宁可少显示一块，也不要整页报错。
    """
    return value if isinstance(value, dict) else {}


# ============================================================
# 页面：岗位库（v2 · 支持 URL 一键导入）
# ============================================================
def page_jobs():
    hero("岗位库", "关键词一键搜岗 / 粘 URL 抓 JD / 手动粘贴；自动识别排除规则")
    ensure_dirs()
    tab_search, tab1, tab2 = st.tabs(["🔎 关键词搜岗（联网）", "🔗 URL 导入", "✍️ 手动粘贴"])

    # ---- 关键词搜岗 ----
    with tab_search:
        st.caption("填关键词 + 选城市，点一次就搜完所有来源并合并去重。"
                   "默认只搜**不用登录**的来源（云端也能跑）。")
        c1, c2 = st.columns([2, 3])
        kw = c1.text_input("关键词（可写多个，用空格或逗号分开）", value="AI",
                           key="wq_kw", placeholder="AI 大模型 Agent,RAG")
        cities = c2.multiselect("城市（可多选；远程=海外 remote 岗位）", job_sources.COMMON_CITIES,
                                default=["南京"], accept_new_options=True, key="wq_cities",
                                help="也能直接输入表里没有的城市（回车确认）。留空 = 全国。")
        c3, c4 = st.columns([3, 2])
        picked_sources = c3.multiselect(
            "来源", job_sources.SOURCES, default=job_sources.NO_LOGIN_SOURCES,
            key="wq_sources",
            help="默认三个是国内的公开接口（免登录、云端可用）。"
                 "海外那组（Remotive/RemoteOK/Arbeitnow/WWR/HN/Greenhouse）都是公开 API/RSS，"
                 "本机需要代理、云端直连即可；实习僧要本机浏览器；BOSS 要本机登录。")
        strict_city = c4.toggle("只要命中城市的岗位", value=True, key="wq_strict",
                                help="打开：城市不匹配的直接不显示（推荐）。"
                                     "如果所有来源都没有该城市的岗位，会自动放宽并提示。")
        depth = st.slider("每个来源最多抓多少条（越大越慢）", min_value=40, max_value=500,
                          value=200, step=20, key="wq_depth",
                          help="实测网易同一关键词有 1011 条、牛客 302 条、HN 招聘贴 782 条；"
                               "以前每个来源只翻 1-2 页（40-100 条），所以你觉得岗位太少。"
                               "现在按这个数决定翻几页。")
        c5, c6 = st.columns([3, 2])
        use_cache = c5.toggle("用缓存（同关键词 + 城市，10 分钟内秒回）", value=True,
                              key="wq_usecache",
                              help="抓一次多平台要十几秒，几乎全是等网络。同一条件 10 分钟内再搜"
                                   "就直接复用上次结果（0 秒，也不打站点）；想拿最新岗位就关掉它。")
        cs = job_sources.cache_stats()
        c6.caption(f"缓存：{cs['entries']} 条 · {cs['size_kb']} KB · 有效 {cs['ttl_min']} 分钟")
        if c6.button("🧹 清空搜索缓存", key="wq_clear_cache"):
            _n = job_sources.cache_clear()
            st.success(f"已清空 {_n} 条搜索缓存（下次搜岗会重新联网抓）")
        with st.expander("➕ 自定义来源（填任意公开 RSS / JSON 列表地址，程序自己抽岗位）"):
            custom_url = st.text_input(
                "RSS / Atom / JSON 地址", value="", key="wq_custom_url",
                placeholder="例如学校就业网 RSS、公司招聘 JSON、社区汇总贴 API")
            st.caption("只读公开内容、不绕登录。填了就在本次搜索里一起抓，来源标为「自定义来源」。")
        city = " ".join(cities)
        if st.button("🔍 开始搜岗", type="primary", key="wq_search"):
            if not picked_sources:
                st.warning("至少选一个来源")
            else:
                with st.spinner(f"正在搜「{kw}」…（多平台十几秒）"):
                    try:
                        _t0 = time.perf_counter()
                        res = job_sources.search_all(
                            kw.strip(), city.strip(), ask_model=lambda p: ask_chat(p),
                            sources=list(picked_sources), strict_city=bool(strict_city),
                            custom_url=custom_url.strip(), max_per_source=int(depth),
                            use_cache=bool(use_cache))
                        # 结果统一用 sr_ 前缀（widget 一律 wq_ 前缀）——两套命名空间分开，
                        # 否则"同名 key 既当控件又当结果"会触发 Streamlit 的
                        # "cannot be modified after the widget is instantiated"。
                        st.session_state["sr_elapsed"] = time.perf_counter() - _t0
                        st.session_state["sr_cache_hits"] = int(res.get("cache_hits") or 0)
                        st.session_state["sr_results"] = res["jobs"]
                        st.session_state["sr_stats"] = res["by_source"]
                        st.session_state["sr_errors"] = res["errors"]
                        st.session_state["sr_diag"] = res.get("diag", {})
                        st.session_state["sr_city_dist"] = res.get("cities", {})
                        st.session_state["sr_relaxed"] = res.get("relaxed", {})
                        st.session_state["sr_city_miss"] = res.get("city_miss", {})
                        st.session_state["sr_relaxed_all"] = res.get("relaxed_all", False)
                        st.session_state["sr_wants"] = res.get("wants", [])
                    except Exception as e:
                        st.session_state["sr_results"] = []
                        st.error(str(e))
        stats = _as_dict(st.session_state.get("sr_stats"))
        errors = _as_dict(st.session_state.get("sr_errors"))
        wants = st.session_state.get("sr_wants") or []
        if stats:
            st.markdown("**各来源命中：**" + "　".join(
                f"{k} **{v}** 条" for k, v in stats.items()))
            _el = st.session_state.get("sr_elapsed")
            if _el is not None:
                _ch = int(st.session_state.get("sr_cache_hits") or 0)
                st.caption(
                    f"⏱️ 本次耗时 {_el:.1f} 秒"
                    + (f"（其中 {_ch} 个来源命中缓存、没有联网）" if _ch else "")
                    + "　·　同一关键词+城市在 10 分钟内再搜会直接复用缓存")
            if wants:
                st.caption("城市条件：" + "、".join(wants)
                           + ("（严格：不匹配的不显示）" if strict_city else ""))
            if st.session_state.get("sr_relaxed_all"):
                st.warning("⚠️ 这次**所有来源都没有**你选的城市岗位，已自动放宽为「全国结果」——"
                           "下面的岗位都不是你选的城市，注意看城市列。")
            miss = _as_dict(st.session_state.get("sr_city_miss"))
            if miss:
                detail = "；".join(f"{k} {v} 条全被过滤" for k, v in miss.items())
                st.info("这些来源这次没有你选的城市岗位：" + detail
                        + "　（它们的岗位城市见下面「抓取诊断」）")
            cdist = _as_dict(st.session_state.get("sr_city_dist"))
            if cdist:
                with st.expander("📍 各来源这次捞回来的城市分布（解释为什么结果少）"):
                    for s, rows in cdist.items():
                        st.markdown(f"- **{s}**：" + "、".join(f"{c} {n}" for c, n in rows))
        _diag = _as_dict(st.session_state.get("sr_diag"))
        if _diag:
            with st.expander("🔬 抓取诊断（岗位为什么只有这些？）"):
                st.caption("这里是每个平台「页面里有多少条 → 抽出来多少条」。"
                           "数量少通常是下面几个原因，不是程序坏了：")
                for _s, _d in _diag.items():
                    if not isinstance(_d, dict):
                        continue
                    bits = []
                    if _d.get("cache"):
                        bits.append(str(_d["cache"]))
                    if _d.get("api_total"):
                        bits.append(f"站点接口共 {_d['api_total']} 条，"
                                    f"抓了 {_d.get('api_pages')} 页")
                    if _d.get("site_total"):
                        bits.append(f"站点共 {_d['site_total']} 条")
                    if _d.get("raw") is not None:
                        bits.append(f"抓到 {_d['raw']} 条")
                    if _d.get("source_api"):
                        bits.append(str(_d["source_api"]))
                    if _d.get("note"):
                        bits.append(str(_d["note"])[:40])
                    if _d.get("text_len"):
                        bits.append(f"页面文本 {_d['text_len']} 字，分 {_d.get('chunks')} 块抽取")
                    if _d.get("keywords"):
                        bits.append("关键词 " + "、".join(_d["keywords"]))
                    if _d.get("kept") is not None:
                        bits.append(f"最终保留 {_d['kept']} 条")
                    if _d.get("api_error"):
                        bits.append("接口没通：" + str(_d["api_error"])[:60])
                    if _d.get("api_skipped"):
                        bits.append("没走接口：" + str(_d["api_skipped"])[:60])
                    st.markdown(f"- **{_s}**：" + "；".join(bits) if bits
                                else f"- **{_s}**：没有诊断数据")
                st.markdown(
                    "**想让结果更多，按这个顺序试：**\n"
                    "1. **换 BOSS 直聘**——岗位量最大，但要先在本机登录一次"
                    "（上面那个一键登录按钮），云端用不了；\n"
                    "2. **关键词写多个**：`AI 大模型 算法 数据` 这样，命中的都算；\n"
                    "3. **城市放宽**：`南京 上海 远程`，或者干脆留空搜全国；\n"
                    "4. **牛客是校招实习社区**，本身岗位就比 BOSS 少一个量级，"
                    "它的作用是稳、快、数据干净；\n"
                    "5. 单个岗位想看得更细，用「🔗 URL 导入」把链接粘进来单独抓。")
        for k, v in errors.items():
            st.warning(f"{k} 没成功：{v}")
        results = st.session_state.get("sr_results", [])
        if results:
            st.success(f"合并后共 {len(results)} 条（已去重）。勾选要入库的，然后点下面的按钮。")
            picked = []
            for i, j in enumerate(results):
                q = job_quality.assess(j)
                label = (f"[{j['source']}] {j['title']} · {j['company']} · {j['city']}"
                         f"{' · ' + j['salary'] if j['salary'] else ''}"
                         f" · {job_quality.summarize(q)}")
                if st.checkbox(label, key=f"pick_{i}"):
                    picked.append(j)
                if q["flags"]:
                    with st.expander(f"　└ 质量明细：{j['title'][:24]}"):
                        for f in q["flags"]:
                            st.markdown(f"- **{f['problem']}**：{f['evidence']}"
                                        f"（-{f['penalty']} 分）")
            if picked and st.button(f"📥 把选中的 {len(picked)} 条加入岗位库",
                                    type="primary", key="save_src"):
                added = 0
                bar = st.progress(0.0, text="准备入库…")
                for idx, j in enumerate(picked):
                    name = re.sub(r"[^\w\u4e00-\u9fa5]+", "_",
                                  f"{j['source']}_{j['company']}_{j['title']}")[:60]
                    if (JDS_DIR / f"{name}.txt").exists():
                        bar.progress((idx + 1) / len(picked),
                                     text=f"跳过已存在的 {j['title']}")
                        continue
                    head = (f"岗位：{j['title']}\n公司：{j['company']}\n"
                            f"城市：{j['city']}\n薪资：{j['salary']}\n"
                            f"来源：{j['source']}\n链接：{j['url']}\n")
                    if j.get("extra"):
                        head += f"其他：{j['extra']}\n"
                    body = (j.get("jd") or "").strip()
                    if not body and j.get("url"):
                        bar.progress((idx + 0.5) / len(picked),
                                     text=f"抓取 JD：{j['title']}")
                        try:
                            body = job_sources.fetch_job_detail(
                                j["url"], ask_model=lambda p: ask_chat(p))
                        except Exception:
                            body = ""
                    if not body:
                        body = "（没抓到 JD 原文。可打开链接手动补，或直接跑匹配试试）"
                    jd_text = head + "\n" + body
                    save_new_job(name, j["city"], jd_text, j["url"], extra={
                        "source": j.get("source", ""),
                        "title": j.get("title", ""),
                        "company": j.get("company", ""),
                        "salary": j.get("salary", ""),
                        "skills": j.get("extra", ""),
                        "search_query": kw.strip(),
                        "quality": job_quality.assess(j),
                    })
                    added += 1
                    bar.progress((idx + 1) / len(picked), text=f"已入库 {j['title']}")
                bar.progress(1.0, text="完成")
                st.success(f"入库 {added} 条（含 JD 原文，重复的已跳过）。"
                           "去「匹配分析」跑一下就能看到匹配度。")
                if added:
                    next_step("saved_job")
        elif results == [] and st.session_state.get("sr_search_done"):
            st.warning("没搜到结果。换个关键词或来源试试；BOSS 记得先登录。")
        st.session_state["sr_search_done"] = bool(results) or st.session_state.get("sr_search_done")

    # ---- URL 导入 ----
    with tab1:
        if not FETCHER_OK:
            st.error("jd_fetcher 模块未加载，URL 导入不可用")
        else:
            st.caption("把 BOSS直聘 / 猎聘 / 智联 / 官网的岗位链接粘贴进来，自动抓取 JD 并提取。")
            url = st.text_input("岗位 URL", key="fetch_url",
                                placeholder="https://www.zhipin.com/job_detail/… 或 https://www.liepin.com/job/…")
            if st.button("🌐 抓取并预览", key="do_fetch"):
                if not url.strip():
                    st.warning("请先粘贴岗位 URL")
                else:
                    with st.spinner("正在抓取页面…（约 5-30 秒）"):
                        try:
                            fetched = fetch_jd(url.strip())
                            st.session_state["fetched"] = fetched
                        except Exception as e:
                            st.error(str(e))
            fetched = st.session_state.get("fetched")
            if fetched:
                st.success(f"抓取成功：识别到岗位「{fetched['name']}」，JD {len(fetched['jd'])} 字")
                c1, c2, c3 = st.columns([2, 1, 1])
                fname = c1.text_input("岗位名（可改）", value=fetched["name"], key="fetched_name")
                fcity = c2.text_input("城市", key="fetched_city", placeholder="南京")
                fcomp = c3.text_input("公司", key="fetched_company", placeholder="选填")
                fjd = st.text_area("提取的 JD（可编辑后保存）", fetched["jd"], height=300, key="fetched_jd")
                if st.button("💾 保存入库", type="primary", key="save_fetched"):
                    msg = save_new_job(fname, fcity, fjd, source_url=url.strip(),
                                       extra={"company": fcomp.strip(),
                                              "source": "url_import"})
                    st.success(msg)
                    st.session_state.pop("fetched", None)
                    st.rerun()

    # ---- 手动粘贴 ----
    with tab2:
        c1, c2 = st.columns([2, 1])
        name = c1.text_input("岗位名（保存为文件名，如 weilan_ai）", key="job_name")
        city = c2.text_input("城市", key="job_city", placeholder="南京")
        jd_text = st.text_area("JD 全文（粘贴）", height=280, key="job_jd")
        if st.button("保存岗位", type="primary"):
            if not name:
                st.warning("请填写岗位名")
            elif len(jd_text.strip()) < 50:
                st.warning("JD 内容太短（至少 50 字），请粘贴完整 JD")
            else:
                st.success(save_new_job(name, city, jd_text))
                st.rerun()

    # ---- 岗位列表 ----
    jobs = list_jobs()
    if not jobs:
        st.info("暂无岗位")
        return
    _bm = st.session_state.pop("batch_msg", "")
    if _bm:
        st.success(_bm)
    _lm = st.session_state.pop("link_msg", None)
    if _lm:
        _kind, _text = _lm
        if _kind == "gone":
            st.error(_text)
        elif _kind == "warn":
            st.warning(_text)
        else:
            st.success(_text)
    st.markdown(f"#### 共 {len(jobs)} 个岗位")
    # ---- 批量操作（v4.1）----
    unmatched = [j for j in jobs if j[1]["status"] == "待投" and j[1].get("match_score") is None]
    bc1, bc2 = st.columns([2, 2])
    if bc1.button(f"⚡ 批量匹配（还有 {len(unmatched)} 个未评）",
                  type="primary", disabled=not unmatched, key="batch_match"):
        fprof = read_text(PROFILE_PATH) or read_text(ME_PATH)
        if not fprof.strip():
                                st.warning("先到「🧬 我的 → 自我蒸馏」生成画像")
        else:
            with st.spinner("批量匹配中…（每个岗位 20-60 秒）"):
                bar = st.progress(0.0, text="准备…")
                done = v41.batch_match(
                    PROMPT_MATCH, lambda p, *m: ask_chat(p, *m),
                    jobs, fprof, progress=bar)
                st.session_state["batch_msg"] = "批量匹配完成：" + "；".join(
                    f"{n} {s}%" if s is not None else f"{n} 失败" for n, s in done)
            st.rerun()
    if bc2.button("🔗 检查全部链接是否失效", key="batch_check_link"):
        with st.spinner("正在重访岗位链接…（每家最多 6 秒）"):
            res = v41.check_links(jobs)
        gone = [r for r in res if r[3] == "gone"]
        unreach = [r for r in res if r[3] == "unreachable"]
        nourl = [r for r in res if r[3] == "no_url"]
        msgs = []
        if gone:
            msgs.append(("gone", "以下岗位链接已失效（404/410），投递前请先确认：\n" +
                         "\n".join(f"- {c}（{n}）：{u}" for n, c, u, _ in gone)))
        if unreach:
            msgs.append(("warn", "以下岗位暂时连不上（网络/超时/反爬），建议投前人工确认：\n" +
                         "\n".join(f"- {c}（{n}）" for n, c, _, _ in unreach)))
        if nourl:
            msgs.append(("warn", f"{len(nourl)} 个岗位没保存链接（v1 手动粘贴的），无法自动检测。"))
        if not gone and not unreach and not nourl:
            msgs.append(("ok", f"链接检测完成：{len(res)} 个岗位链接全部可访问"))
        st.session_state["link_msg"] = msgs[0] if msgs else ("ok", "链接检测完成，无异常")
        st.rerun()
    for name, meta, jd in jobs:
        excl = meta["status"] == "排除"
        cols = st.columns([3, 1.2, 1.2, 1.2, 1])
        with cols[0]:
            st.markdown(f"**{meta['name']}**　<span style='color:#64748B;font-size:12px'>{meta['city']}</span>"
                        f"　{status_tag(meta['status'])}", unsafe_allow_html=True)
            if excl and meta.get("excluded_reason"):
                st.caption(f"⚠️ {meta['excluded_reason']}")
            if meta.get("match_score") is not None and not excl:
                st.caption(f"匹配度 {meta['match_score']}%")
            if meta.get("source_url"):
                st.caption(f"🔗 {meta['source_url'][:60]}")
            q = meta.get("quality")
            if isinstance(q, dict):
                tag = ("oa-tag-green" if q.get("verdict") == "正常"
                       else ("oa-tag-amber" if q.get("verdict") == "存疑" else "oa-tag-red"))
                st.markdown(f'<span class="oa-tag {tag}">岗位质量 {q.get("score")} · '
                            f'{q.get("verdict")}</span>', unsafe_allow_html=True)
            with st.expander("📄 岗位档案（为什么它在列表里 + 岗位要求）"):
                render_job_detail(name, meta, jd)
            with st.expander("⚡ 一站式：匹配 → ATS → 话术 → 已投（不用换页）"):
                if excl:
                    st.caption("这个岗位已被排除，流程停用。要恢复就在右边点回「待投」。")
                else:
                    fprof = read_text(PROFILE_PATH) or read_text(ME_PATH)
                    fsc = meta.get("match_score")
                    st.markdown("**① 匹配分析**　"
                                + (f"已完成：{fsc}%" if fsc is not None else "未做"))
                    if st.button("① 运行匹配", key=f"f1_{name}"):
                        if not fprof.strip():
                            st.warning("先到「🧬 我的 → 自我蒸馏」生成画像")
                        else:
                            with st.spinner("匹配中…（约 20-60 秒）"):
                                try:
                                    rep = ask_chat(PROMPT_MATCH, fprof, jd)
                                    write_text(MATCH_DIR / f"match_{name}.md", rep)
                                    s2 = extract_score(rep)
                                    if s2 is not None:
                                        meta["match_score"] = s2
                                        save_meta(name, meta)
                                    st.session_state["flow_msg"] = f"匹配完成：{s2}%"
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))
                    if fsc is not None:
                        st.markdown("**② ATS 简历覆盖**")
                        if st.button("② 检查简历覆盖", key=f"f2_{name}"):
                            fres = load_my_resume()
                            if not fres.strip():
                                st.warning("先到「🎯 找工作 → 简历」准备一份简历")
                            else:
                                with st.spinner("本地比对中…"):
                                    try:
                                        st.session_state[f"flow_ats_{name}"] = \
                                            resume_tailor.tailor(fres, jd,
                                                                 lambda p: ask_chat(p))
                                    except Exception as e:
                                        st.error(str(e))
                        fout = st.session_state.get(f"flow_ats_{name}")
                        if fout:
                            fmiss = [r for r in fout["coverage"] if r["status"] == "缺失"]
                            st.caption(f"关键词覆盖率 {fout['rate']}%　·　"
                                       f"缺失 {len(fmiss)} 个")
                            if fmiss:
                                st.caption("缺失：" + "、".join(r["keyword"] for r in fmiss[:12]))
                        st.markdown("**③ 投递话术**")
                        st.caption("话术统一在「投递台」生成（避免两套代码）。"
                                   "这里点一下会跳过去，并已经帮你选中这家。")
                        if st.button("③ 去投递台写话术", key=f"f3_{name}"):
                            goto_page("apply", talk_pick=name)
                        st.markdown("**④ 标记已投**")
                        st.caption("发送由你自己按；这里只负责记录状态，之后 7 天没动静会自动进跟进提醒。")
                        if st.button("④ 我发出去了，标记已投", key=f"f4_{name}"):
                            meta["status"] = "已投"
                            meta["applied_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                            save_meta(name, meta)
                            apply_assist.log_application(
                                name, meta,
                                st.session_state.get(f"talk_{name}_boss", ""))
                            st.session_state["flow_done"] = name
                            next_step("applied", defer=True)
                            st.rerun()
                    if st.session_state.get("flow_msg"):
                        st.success(st.session_state.pop("flow_msg"))
                    if st.session_state.get("flow_done") == name:
                        st.caption("已标记已投（见页面底部提示）")
        with cols[1]:
            if not excl and st.button("🔍 匹配", key=f"m_{name}"):
                goto_page("match", match_pick=name)
        with cols[2]:
            if not excl and st.button("✅ 已投", key=f"d_{name}"):
                meta["status"] = "已投"
                save_meta(name, meta)
                st.rerun()
        with cols[3]:
            if not excl and st.button("🚫 排除", key=f"x_{name}"):
                meta["status"] = "排除"
                meta["excluded_reason"] = meta.get("excluded_reason") or "手动排除"
                save_meta(name, meta)
                st.rerun()
        with cols[4]:
            if st.button("🗑", key=f"del_{name}"):
                (JDS_DIR / f"{name}.txt").unlink(missing_ok=True)
                (JDS_DIR / (name + META_SUFFIX)).unlink(missing_ok=True)
                for f in MATCH_DIR.glob(f"match_{name}.md"):
                    f.unlink(missing_ok=True)
                st.rerun()
        st.divider()


# ============================================================
# 页面：匹配分析（v2 · URL 直配 + 卡片渲染）
# ============================================================
