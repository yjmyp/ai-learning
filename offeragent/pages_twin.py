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
import twin_guard
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
    """名片页问答入口：**先过额度守卫**，再调模型。

    为什么必须挡一道：名片页是免密公开的，每次提问都花我的 DeepSeek 额度；
    原先只有全局每日 200 次上限，一个人拿到链接就能把当天额度刷光（低成本 DoS）。
    守卫按「访问者 IP 每天 8 次 + 名片页每天 60 次」双层限额。
    """
    ok, why, left = twin_guard.check(twin_guard.visitor_ip())
    if not ok:
        return (f"（{why}。这个公开问答的额度是为了防止被刷掉，"
                "如果还需要了解什么，可以直接邮件联系我：yj2994762833@gmail.com）")
    ans = digital_twin.twin_answer(profile, question, lambda p: ask_chat(p))
    if left >= 0:
        st.session_state["twin_left"] = left
    return ans


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
    # 公开问答有额度（防刷），把剩余次数显示出来，免得面试官以为是坏了
    _left = st.session_state.get("twin_left")
    if isinstance(_left, int) and _left >= 0:
        st.caption(f"本次访问还可以问 {_left} 个问题（公开问答设了每日额度，避免被刷掉）。")

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


