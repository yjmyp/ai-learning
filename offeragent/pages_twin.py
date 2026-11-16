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
import twin_core
import twin_avatar
import twin_stage
import twin_voice
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
    """当前部署的公开**根**地址（生成「分享/转载」链接用）。

    注意：必须只保留 scheme://host[:port] —— 之前保留了页面路径，
    在 /show 页会生成 `.../show/?twin=1` 这种带多余路径的分享链接。
    """
    try:
        u = str(getattr(st.context, "url", "") or "")
        if u.startswith("http"):
            from urllib.parse import urlsplit
            sp = urlsplit(u)
            if sp.scheme and sp.netloc:
                return f"{sp.scheme}://{sp.netloc}"
    except Exception:
        pass
    return "https://ai-learning-c62pgpcfp7us6rztelatpj.streamlit.app"


GITHUB_URL = "https://github.com/yjmyp/ai-learning"
CONTACT_EMAIL = "yj2994762833@gmail.com"
PRESET_QUESTIONS = [
    "介绍下你的 RAG 项目，做了什么、做到什么程度？",
    "你做过 Agent 相关的东西吗？",
    "你的网络工程背景对做 AI 应用有什么帮助？",
    "你怎么评估你的 RAG 系统效果？",
    "你最大的短板是什么？",
    "为什么应聘 AI/Agent 系统交付方向？",
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
    """名片页下载按钮用的 PDF：优先 2027 校招版，其次保留的旧版。"""
    for fn in ("余剑-简历-AI应用开发-2027校招.pdf",
               "余剑-简历-AI应用开发实习-v3.pdf",
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
            _portal_avatar = st.session_state.get("twin_avatar_file") or twin_stage.DEFAULT_AVATAR
            twin_stage.stage("idle", name="余剑", caption="AI/Agent 系统交付 · 2027 届",
                             avatar=_portal_avatar, height=280, key="twin_portal_stage")
        with c2:
            st.markdown("## 余剑 · AI/Agent 系统交付")
            with st.container(horizontal=True):
                st.badge("南京邮电大学", icon=":material/school:", color="blue")
                st.badge("网络工程 · 2027 届", icon=":material/badge:", color="gray")
                st.badge("南京优先 · 城市可沟通", icon=":material/location_on:", color="green")
                st.badge("2027 届校招 · 可尽快到岗", icon=":material/event_available:", color="violet")
            st.caption("AI/Agent 系统交付 · RAG 检索 · Python 后端。"
                       "对外数字来自可复现的评估报告，不用未经验证的宣传口径。")
            with st.container(horizontal=True):
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
                ("届别", "2027 届\n本科校招 · 可尽快到岗"),
                ("求职方向", "AI/Agent 系统交付\nPython 后端 / 智能运维"),
                ("坐标", "南京优先\n城市可沟通")]):
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
            st.markdown("**RAG 检索问答服务 · 本地可复现**")
            with st.container(horizontal=True):
                st.badge("33 篇 / 740 块", color="blue")
                st.badge("240 条评估集", color="orange")
                st.badge("R@5 95%", color="green")
                st.badge("带引用溯源", color="gray")
            st.caption("33 篇资料 / 740 块 → bge 向量化 + BM25 混合召回 → 多特征重排 → "
                       "带引用生成；240 条评估集上 R@5 95%、MRR 0.856，P95 88ms。"
                       "代码、评估集与报告在 GitHub 仓库中可复现。")
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
    """数字人：虚拟人形象 + 多轮对话，人格底座来自整套蒸馏档案。"""
    hero("数字分身", "它读你的整套档案（画像 / 亮点 / 表达风格 / 硬边界）替你先答一版；上场的是你本人")
    st.markdown(
        "<style>"
        ".st-key-oa_twin_chat{height:100%!important;}"
        "div[data-testid='stLayoutWrapper']:has(>.st-key-oa_twin_chat){"
        "height:clamp(320px,calc(100vh - 370px),640px)!important;"
        "flex-basis:clamp(320px,calc(100vh - 370px),640px)!important;}"
        "</style>",
        unsafe_allow_html=True)
    ready = twin_core.readiness()
    if ready["score"] == 0:
        st.warning("一份档案都没有。先去「🧬 我的 → 自我蒸馏」答完题生成档案，分身才有记忆。")
        if st.button("现在去蒸馏", key="to_distill"):
            goto_page("distill")
        return

    state = twin_core.load_chat()

    # 两趟式：本趟先把形象渲染成「思考中」，再真的去问模型，
    # 这样等待期间浏览器上看到的是会转的思考环，而不是一片空白。
    pending = st.session_state.pop("_twin_pending", None)
    spoke_at = float(st.session_state.get("twin_spoke_at") or 0)
    if pending:
        avatar_state = "thinking"
    elif time.time() - spoke_at < 6:
        avatar_state = "speaking"
    else:
        avatar_state = "idle"

    _last_ans = next((m["content"] for m in reversed(state["messages"])
                      if m["role"] == "assistant" and (m.get("content") or "").strip()), "")

    left, right = st.columns([1, 2.5], gap="large")

    with left:
        _avs = twin_stage.available_avatars()
        _names = [n for n, _ in _avs]
        _labels = [lab for _, lab in _avs]
        _cur = st.session_state.get("twin_avatar_file") or twin_stage.DEFAULT_AVATAR
        if _cur not in _names:
            _cur = twin_stage.DEFAULT_AVATAR
        twin_stage.stage(
            avatar_state, name="余剑",
            caption=f"数字分身 · 人格底座 {ready['score']}/{ready['total']}",
            avatar=_cur, height=270, key="twin_stage_" + _cur)
        if _last_ans:
            st.caption("🔊 最新回答")
            twin_voice.player(_last_ans, compact=True, height=68,
                              voice=st.session_state.get("twin_voice_name", ""),
                              rate=int(st.session_state.get("twin_voice_rate") or 0),
                              autoplay=bool(st.session_state.get("twin_voice_auto")))
        with st.container(border=True):
            _spoken = twin_voice.listen(key="twin_mic")
            _vtxt = str((_spoken or {}).get("text") or "").strip()
            _vts = str((_spoken or {}).get("ts") or "")
            if _vtxt and _vts and _vts != st.session_state.get("twin_voice_ts"):
                st.session_state["twin_voice_ts"] = _vts
                st.session_state["_twin_pending"] = _vtxt
                st.rerun()
        with st.expander("🎭 换个形象 / 上传自己的 VRM", expanded=False):
            _pick = st.selectbox("内置形象（CC0 素材）", _labels,
                                 index=_labels.index(dict(_avs)[_cur]) if _cur in dict(_avs) else 0,
                                 key="twin_avatar_pick")
            _sel = _names[_labels.index(_pick)]
            if _sel != _cur:
                st.session_state["twin_avatar_file"] = _sel
                st.rerun()
            _up = st.file_uploader("上传 .vrm（VRoid Studio 等导出的都行）",
                                   type=["vrm"], key="twin_vrm_up")
            if _up is not None:
                try:
                    _fn = twin_stage.save_upload(_up.getvalue(), _up.name)
                    st.session_state["twin_avatar_file"] = _fn
                    st.success("已载入 " + _fn)
                    st.rerun()
                except Exception as _e:
                    st.error("上传失败：" + str(_e))
            st.caption("形象只在本地渲染，不上传到任何服务器。")
        with st.expander("🎙 语音与口型", expanded=False):
            _vs = list(twin_voice.voices())
            if _vs:
                st.selectbox("音色（本机 Windows 语音）", _vs, key="twin_voice_name",
                             help="Huihui / Yaoyao / Kangkang 都是离线中文语音；"
                                  "不同系统装的音色可能不一样。")
            else:
                st.caption("没找到中文语音。Windows 设置 → 时间和语言 → 语音 里装一个中文语音包。")
            st.slider("语速", -3, 3, 0, key="twin_voice_rate",
                      help="0 是正常语速；负数更慢，正数更快。")
            st.checkbox("新回答自动播放", value=False, key="twin_voice_auto",
                        help="浏览器可能仍然拦截自动播放；被拦时点播放器即可。")
            st.caption("左侧播放器播放时，3D 形象会同步张嘴。")
            if st.button("试听当前音色", key="twin_voice_demo"):
                twin_voice.player(
                    "你好，我是余剑的数字分身。这段话用来试听当前音色。",
                    label="试听", voice=st.session_state.get("twin_voice_name", ""),
                    rate=int(st.session_state.get("twin_voice_rate") or 0))
        st.caption("已装载：" + "、".join(ready["have_labels"]))
        if ready["missing"]:
            with st.expander(f"还缺 {len(ready['missing'])} 份", expanded=False):
                st.markdown("\n".join(f"- {x}" for x in ready["missing"]))
        with st.expander("🎯 纠偏 / 记忆", expanded=False):
            c = st.text_input("它哪句话不像你？写「以后别说 XX」", key="twin_corr")
            if st.button("记住这条", key="twin_corr_go"):
                if twin_core.add_correction(state, c):
                    st.success("记住了，下次起生效")
                    st.rerun()
                else:
                    st.caption("没有新内容可记")
            if state.get("corrections"):
                st.markdown("**已生效：**\n" +
                            "\n".join(f"- {x}" for x in state["corrections"]))
            if st.button("🗑 清空对话（保留纠偏）", key="twin_clear"):
                keep = state.get("corrections", [])
                twin_core.reset_chat()
                s2 = twin_core.load_chat()
                s2["corrections"] = keep
                twin_core.save_chat(s2)
                st.rerun()
            with st.expander("看人格底座全文", expanded=False):
                for nm, txt in twin_core.load_persona().items():
                    st.markdown(f"**{nm}**")
                    st.markdown(txt)

    with right:
        _chat = st.container(height=410, border=True, key="oa_twin_chat")
        with _chat:
            for m in state["messages"]:
                with st.chat_message("assistant" if m["role"] == "assistant" else "user"):
                    st.markdown(m["content"])
            if not state["messages"] and not pending:
                st.caption("试一句：你的 RAG 系统检索出来全是错的，你怎么办？")

            if pending:
                with st.chat_message("assistant"):
                    with st.spinner("分身思考中…"):
                        try:
                            twin_core.reply(state, pending, lambda p: ask_chat(p))
                        except Exception as e:
                            st.error(str(e))
                st.session_state["twin_spoke_at"] = time.time()
                st.rerun()

        q = st.chat_input("问分身一个问题（面试里卡住的也可以扔给它）", key="twin_chat_in")
        if q:
            st.session_state["_twin_pending"] = q
            st.rerun()

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


def page_twin_digital():
    """数字分身（独立页）：虚拟人形象 + 多轮对话，第一眼就看得出是个“虚拟人”。"""
    profile = read_text(PROFILE_PATH) or read_text(ME_PATH)
    twin_practice_section(profile)


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
            badge = ('<span class="oa-tag oa-tag-green">已就绪</span>' if ok
                     else '<span class="oa-tag oa-tag-red">还没有</span>')
            col.markdown(
                f'<div class="oa-card" style="padding:12px 14px;text-align:center">'
                f'<div style="font-size:13px;font-weight:650;color:var(--slate-800)">{label}</div>'
                f'<div style="margin:7px 0 5px">{badge}</div>'
                f'<div style="font-size:11.5px;color:var(--slate-500)">{hint}</div></div>',
                unsafe_allow_html=True)
        ready = sum(1 for _, ok, _ in items if ok)
        st.caption(f"对外就绪度：**{ready} / {len(items)}**　·　"
                   "四项齐了再发链接，HR 打开就是完整的名片页。")
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


