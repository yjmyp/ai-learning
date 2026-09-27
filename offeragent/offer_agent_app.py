# -*- coding: utf-8 -*-
"""
OfferAgent · 求职智能体 Web 应用（v2 · 联网版）
================================================
余剑 2027 届 ｜ 南京邮电大学 · 网络工程
v2 升级：① 岗位库支持 URL 一键联网抓取 JD（jd_fetcher）② 话术自然口语化（双版本）
         ③ 匹配报告结构化卡片渲染 + 视觉升级

本地运行：  streamlit run offer_agent_app.py
部署：      Streamlit Cloud，API Key 放 Secrets（DEEPSEEK_API_KEY）
"""
import json
import os
import re
import time
from pathlib import Path

import requests
import streamlit as st

import plotly.graph_objects as go

try:
    from jd_fetcher import fetch_jd
    FETCHER_OK = True
except Exception:
    FETCHER_OK = False

# ============================================================
# 常量与路径
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
JDS_DIR = DATA_DIR / "jds"
MATCH_DIR = DATA_DIR / "match_results"
PROFILE_PATH = DATA_DIR / "profile.md"
ME_PATH = BASE_DIR / "me.txt"
CONFIG_PATH = DATA_DIR / "config.json"
TALKQ_PATH = DATA_DIR / "talk_queue.json"
META_SUFFIX = ".meta.json"
MY_RESUME_PATH = BASE_DIR.parent / "简历" / "我的简历.md"

API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
MODEL_OPTIONS = ["deepseek-chat", "deepseek-v4-flash"]

# ============================================================
# 提示词（2026-09-27 起抽到 prompts.py 统一管理）
# ============================================================
from prompts import (  # noqa: E402
    BANNED_PHRASES,
    PROMPT_ADVICE,
    PROMPT_HIGHLIGHT,
    PROMPT_MATCH,
    PROMPT_PROFILE,
    TALK_VARIANTS,
    build_talk_prompt,
    check_talk,
    generate_talk,
)

import distill  # noqa: E402  自我蒸馏模块（4 轮问答 → 4 份档案）
import apply_assist  # noqa: E402  投递辅助（打开页面 / 写剪贴板 / 记录投递）
import job_sources  # noqa: E402  联网搜岗（牛客 / 实习僧 / BOSS）
import distill_chat  # noqa: E402  问答式自我蒸馏（对话形态）
import theme  # noqa: E402  界面样式（v4 专业版）
import job_quality  # noqa: E402  岗位质量检查（假岗/僵尸岗识别）
import resume_tailor  # noqa: E402  简历定制 + ATS 覆盖检查
import interview_drill  # noqa: E402  面试拷问
import pipeline  # noqa: E402  投递漏斗 / 跟进提醒 / 被拒归因
import inbox_parse  # noqa: E402  邮件/消息 → 状态识别
import v41  # noqa: E402  v4.1 增强（批量匹配/链接检测/漏斗图/三件套/面试提醒/密码门）
import digital_twin  # noqa: E402  数字分身（自我介绍/反问/扮演我/复盘进化/岗位雷达）
import company_lookup  # noqa: E402  公司速查
import job_detail  # noqa: E402  岗位档案与筛选依据
import doc_io  # noqa: E402  文档/图片读取（PDF / Word / 图片 OCR）
import resume_builder  # noqa: E402  问答式生成简历

REPORTS_DIR = DATA_DIR / "reports"


# ============================================================
# 页面：今日行动（行动导向首屏）
# ============================================================
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
                     "📋 我的资料", "进「自我蒸馏」花 10 分钟答完 15 题就有"))
    jobs = list_jobs()
    if not jobs:
        todo.append(("岗位库是空的", "🔎 岗位", "给关键词搜一次岗，勾选入库"))
    elif not any(m.get("match_score") is not None for _, m, _ in jobs):
        todo.append(("岗位还没有匹配度", "🔎 岗位", "去「匹配分析」跑一次"))
    if not any(m.get("status") in ("已投", "面试中", "已拒", "Offer")
               for _, m, _ in jobs):
        todo.append(("还没投出去过", "✉️ 投递", "先把简历准备好，再生成话术"))

    if not todo:
        return
    st.markdown("### 🚩 还差这几步就能投递")
    for text, target, hint in todo:
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"- **{text}**　<span style='color:#93A1AF;font-size:12.5px'>{hint}</span>",
                    unsafe_allow_html=True)
        if c2.button("去处理", key=f"ob_{target}"):
            # 注意：不能直接写 st.session_state["nav"]（widget 已实例化会报错），
            # 走「待跳转」标记，在 main() 渲染导航条之前再设置。
            st.session_state["_go_nav"] = target
            st.rerun()
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
    with st.expander("调整每日目标 / 看连续投递天数"):
        new_target = st.number_input("每天投几家", min_value=1, max_value=20,
                                     value=target, key="target_in")
        if st.button("保存目标", key="target_save"):
            _c["daily_target"] = int(new_target)
            write_text(CONFIG_PATH, json.dumps(_c, ensure_ascii=False, indent=2))
            st.success("已保存")
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
            if b1.button("✍️ 生成/刷新话术", key=f"g_{name}"):
                with st.spinner("写话术中…"):
                    try:
                        talk, hits = generate_talk(
                            lambda p, *m: ask_chat(p, *m), "boss", profile, jd)
                        st.session_state[key] = talk
                        st.session_state[key + "_hits"] = hits
                    except Exception as e:
                        st.error(str(e))
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

# ============================================================
# 文件工具
# ============================================================
def ensure_dirs():
    for d in (DATA_DIR, JDS_DIR, MATCH_DIR):
        d.mkdir(parents=True, exist_ok=True)


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default


def write_text(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def load_my_resume() -> str:
    """读「我的简历」：优先读 简历/我的简历.md，没有就退回仓库里已有的简历。"""
    if MY_RESUME_PATH.exists():
        return read_text(MY_RESUME_PATH)
    for cand in [BASE_DIR.parent / "简历" / "余剑-简历-AI应用开发实习.md",
                 BASE_DIR.parent / "简历" / "余剑-简历-AI应用开发实习-v2.md"]:
        if cand.exists():
            return read_text(cand)
    return ""


def save_my_resume(text: str):
    MY_RESUME_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_text(MY_RESUME_PATH, (text or "").strip() + "\n")


NEXT_HINTS = {
    "saved_job": "下一步：去「匹配分析」跑一次匹配，看这个岗位值不值得投。",
    "matched": "下一步：在同一个岗位卡片里点「ATS 检查」，看简历关键词覆盖够不够。",
    "ats_done": "下一步：生成投递话术，复制后去招聘平台发送。",
    "talk_done": "下一步：把话术发出去，然后回来点「标记已投」；7 天后没动静会自动进跟进提醒。",
    "applied": "下一步：等消息。有回信就粘到「投递记录 → 邮件识别」里判断怎么改状态。",
    "profile_done": "下一步：去「岗位」搜一次岗，勾选入库后跑匹配。",
    "resume_saved": "下一步：去「投递 → 简历定制」，选一个目标岗位做 ATS 覆盖检查。",
}


def next_step(key: str, extra: str = "", defer: bool = False):
    """每个动作完成后，明确告诉用户下一步做什么。

    defer=True 用于「紧接着就 st.rerun()」的场景：提示先存起来，重跑完在页面底部显示，
    否则提示会被 rerun 冲掉，用户看不到。
    """
    hint = NEXT_HINTS.get(key)
    if not hint:
        return
    text = hint + (("　" + extra) if extra else "")
    if defer:
        st.session_state["_pending_hint"] = text
    else:
        st.info(text)


def load_meta(name: str) -> dict:
    p = JDS_DIR / (name + META_SUFFIX)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_meta(name: str, meta: dict):
    (JDS_DIR / (name + META_SUFFIX)).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_jobs() -> list:
    """返回 [(name, meta, jd_text)]，按状态排序：待投 → 已投 → 排除"""
    jobs = []
    for p in sorted(JDS_DIR.glob("*.txt")):
        name = p.stem
        meta = load_meta(name)
        meta.setdefault("name", name)
        meta.setdefault("company", "")
        meta.setdefault("city", "")
        meta.setdefault("status", "待投")
        meta.setdefault("match_score", None)
        meta.setdefault("excluded_reason", "")
        meta.setdefault("created_at", "")
        meta.setdefault("source_url", "")
        jobs.append((name, meta, read_text(p)))
    order = {"待投": 0, "已投": 1, "排除": 2}
    jobs.sort(key=lambda x: (order.get(x[1]["status"], 9), -(x[1]["match_score"] or 0)))
    return jobs


def get_api_key() -> str:
    try:
        k = st.secrets.get("DEEPSEEK_API_KEY", "")
        if k:
            return k
    except Exception:
        pass
    k = os.environ.get("DEEPSEEK_API_KEY", "")
    if k:
        return k
    cfg = read_text(CONFIG_PATH, "{}")
    try:
        return json.loads(cfg).get("api_key", "")
    except Exception:
        return ""


def get_model() -> str:
    cfg = read_text(CONFIG_PATH, "{}")
    try:
        return json.loads(cfg).get("model", DEFAULT_MODEL)
    except Exception:
        return DEFAULT_MODEL


# ============================================================
# AI 调用
# ============================================================
def ask_model(messages: list, model: str = None) -> str:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("未配置 API Key：请到「设置」页填入 DeepSeek API Key")
    model = model or get_model()
    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages},
        timeout=120,
    )
    if resp.status_code != 200:
        try:
            err = resp.json().get("error", {}).get("message", resp.text[:200])
        except Exception:
            err = resp.text[:200]
        raise RuntimeError(f"API 错误（{resp.status_code}）：{err}")
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"响应解析失败：{str(data)[:200]}")


def ask_chat(prompt: str, *materials: str, model: str = None) -> str:
    messages = [{"role": "user", "content": prompt}]
    for m in materials:
        if m and m.strip():
            messages.append({"role": "user", "content": m})
    return ask_model(messages, model)


def extract_score(report: str) -> int:
    m = re.search(r"匹配度[:：]?\s*(\d{1,3})\s*%", report)
    if m:
        return min(100, max(0, int(m.group(1))))
    return None


def parse_report(report: str) -> dict:
    """把匹配报告解析成结构化小节：{'匹配点': [...], '差距': [...], ...}"""
    sections = {}
    current = None
    for line in report.splitlines():
        m = re.match(r"^#+\s*(匹配点|差距|短板与风险|短板|结论|同类岗位对比建议|维度评分)",
                     line.strip())
        if m:
            current = m.group(1)
            sections[current] = []
            continue
        if current and line.strip():
            items = sections[current]
            if line.strip().startswith(("-", "•", "*")):
                items.append(line.strip().lstrip("-•* ").strip())
            else:
                if items:
                    items[-1] = items[-1] + " " + line.strip()
                else:
                    items.append(line.strip())
    return sections


def render_section_cards(sections: dict):
    """把解析后的报告渲染成彩色卡片组（比 markdown 好看）"""
    style_map = {
        "匹配点": ("✅ 匹配点", "#0F766E", "#D1FAE5"),
        "差距": ("📌 差距", "#1D4ED8", "#DBEAFE"),
        "短板与风险": ("⚠️ 短板与风险", "#B45309", "#FEF3C7"),
        "结论": ("🎯 结论", "#1E293B", "#E2E8F0"),
    }
    for key in ("匹配点", "差距", "短板与风险", "结论"):
        items = sections.get(key) or sections.get("短板") or []
        if not items:
            continue
        label, color, bg = style_map.get(key, (key, "#334155", "#F1F5F9"))
        lis = "".join(
            f'<div style="padding:4px 0;font-size:14px;line-height:1.6">{"• " + it}</div>'
            for it in items if it
        )
        st.markdown(
            f'<div style="background:{bg};border:1px solid {color}33;'
            f'border-radius:12px;padding:12px 16px;margin-bottom:10px">'
            f'<div style="color:{color};font-weight:700;font-size:14px;margin-bottom:4px">{label}</div>'
            f'{lis}</div>',
            unsafe_allow_html=True,
        )


def extract_dim_scores(report: str) -> dict:
    """从「维度评分」小节提取五维分数 {维度: 分数}"""
    m = re.search(r"##\s*维度评分\s*\n(.*)", report)
    if not m:
        return {}
    line = m.group(1).strip().splitlines()[0] if m.group(1).strip() else ""
    dims = {}
    for part in line.replace("，", " ").replace(",", " ").split():
        part = part.strip()
        mm = re.match(r"([\u4e00-\u9fa5A-Za-z]+)\s*[:：]\s*(\d{1,3})", part)
        if mm:
            dims[mm.group(1)] = min(100, max(0, int(mm.group(2))))
    return dims


# ============================================================
# 岗位管理 & 排除规则
# ============================================================
def detect_network_exclude(jd_text: str):
    """检测 JD 是否「专门点名要求网络工程专业」。
    返回 (原因, 命中原文)；没命中返回 (None, "")。"""
    patterns = [
        r"专业要求[^\n]*网络工程",
        r"专业[：:][^\n]*网络工程",
        r"网络工程[^\n]*等相关专业",
        r"计算机、软件工程、网络工程",
        r"（?网络工程）?[、，]?人工智能等相关专业",
    ]
    for pat in patterns:
        m = re.search(pat, jd_text)
        if m:
            evidence = m.group(0).strip()
            return ("JD 专业要求点名「网络工程」，非纯 AI 应用岗方向，自动排除",
                    evidence[:80])
    return None, ""


def save_new_job(name: str, city: str, jd_text: str, source_url: str = "",
                 extra: dict = None) -> str:
    """新增/更新岗位；返回提示信息"""
    name = re.sub(r"[\\/:*?\"<>|]", "_", name.strip())
    if not name:
        return "岗位名不能为空"
    ensure_dirs()
    write_text(JDS_DIR / f"{name}.txt", jd_text.strip())
    meta = load_meta(name)
    meta["name"] = name
    meta["city"] = city.strip()
    meta.setdefault("status", "待投")
    meta.setdefault("match_score", None)
    meta.setdefault("created_at", time.strftime("%Y-%m-%d"))
    if source_url:
        meta["source_url"] = source_url
    if extra:
        meta.update(extra)
    reason, evidence = detect_network_exclude(jd_text)
    if reason:
        meta["status"] = "排除"
        meta["excluded_reason"] = reason
        meta["excluded_evidence"] = evidence
    elif meta.get("excluded_reason") and meta["status"] == "排除":
        meta["status"] = "待投"
        meta["excluded_reason"] = ""
        meta["excluded_evidence"] = ""
    save_meta(name, meta)
    return f"已保存：{name}（{'自动排除：' + reason if reason else '待投'}）"


# ============================================================
# 可视化
# ============================================================
def score_color(score):
    if score >= 75:
        return "#0F766E"
    if score >= 60:
        return "#2563EB"
    if score >= 45:
        return "#D97706"
    return "#B91C1C"


def score_gauge(score: int):
    color = score_color(score)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "%", "font": {"size": 44, "color": color, "family": "Arial Black"}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#CBD5E1"},
                "bar": {"color": color, "thickness": 0.28},
                "bgcolor": "#F1F5F9",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 45], "color": "#FEE2E2"},
                    {"range": [45, 60], "color": "#FEF3C7"},
                    {"range": [60, 75], "color": "#DBEAFE"},
                    {"range": [75, 100], "color": "#D1FAE5"},
                ],
            },
        )
    )
    fig.update_layout(height=240, margin=dict(l=20, r=20, t=10, b=10))
    return fig


def dim_radar(dims: dict):
    names = list(dims.keys())
    values = list(dims.values())
    fig = go.Figure(
        go.Scatterpolar(
            r=values + values[:1],
            theta=names + names[:1],
            fill="toself",
            line=dict(color="#2563EB", width=2),
            fillcolor="rgba(37,99,235,0.25)",
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10))),
        height=280,
        margin=dict(l=30, r=30, t=10, b=10),
        showlegend=False,
    )
    return fig


def rank_bar(jobs):
    rows = [(m["name"], m["match_score"] or 0) for _, m, _ in jobs
            if m["status"] != "排除" and m["match_score"] is not None]
    if not rows:
        return None
    rows.sort(key=lambda x: x[1])
    names = [r[0] for r in rows]
    scores = [r[1] for r in rows]
    colors = [score_color(s) for s in scores]
    fig = go.Figure(go.Bar(
        x=scores, y=names, orientation="h",
        marker=dict(color=colors),
        text=[f"{s}%" for s in scores], textposition="outside",
    ))
    fig.update_layout(
        xaxis=dict(range=[0, 105], title="匹配度", tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=12)),
        height=max(220, len(names) * 42),
        margin=dict(l=10, r=50, t=10, b=10),
        bargap=0.35,
    )
    return fig


# ============================================================
# 全局样式（v2 · 视觉升级）
# ============================================================
def inject_css(variant: str = None):
    """样式统一在 theme.py 维护。三套主题：A 默认 / B Linear / C Stripe。"""
    st.markdown(theme.get_css(variant), unsafe_allow_html=True)


def _legacy_css_unused():
    # 旧版样式保留备查，不再使用
    st.markdown("""
<style>
:root {
  --brand: #0F766E;
  --brand2: #2563EB;
  --ink: #0F172A;
  --muted: #64748B;
  --bg: #F6F8FB;
  --card: #FFFFFF;
  --line: #E2E8F0;
}
.stApp { background: var(--bg); }
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0B1220 0%, #134E4A 100%);
  border-right: 0;
}
[data-testid="stSidebar"] * { color: #E2E8F0; }
[data-testid="stSidebar"] .stRadio label {
  font-size: 15px; padding: 8px 12px; border-radius: 10px; margin-bottom: 2px;
}
[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.10); }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 { color: #F8FAFC; }
h1, h2, h3 { color: var(--ink); letter-spacing: -0.01em; }
div[data-testid="stMetric"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 16px; padding: 14px 16px;
  box-shadow: 0 1px 3px rgba(15,23,42,0.06);
  transition: transform .15s ease, box-shadow .15s ease;
}
div[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(15,23,42,0.10); }
div[data-testid="stMetric"] label { color: var(--muted); }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: var(--ink); font-weight: 700; }
.stButton > button {
  border-radius: 10px; border: 1px solid var(--line);
  background: var(--card); color: var(--ink); font-weight: 600;
}
.stButton > button:hover { border-color: var(--brand); color: var(--brand); }
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #0F766E, #0D9488);
  border: none; color: #fff;
}
.stButton > button[kind="primary"]:hover { opacity: .92; color: #fff; }
textarea, .stTextInput input, [data-baseweb="select"] > div {
  border-radius: 12px !important;
}
div[data-testid="stExpander"] {
  background: var(--card); border: 1px solid var(--line); border-radius: 14px;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 6px; }
[data-testid="stTabs"] button[role="tab"] { border-radius: 10px 10px 0 0; }
[data-testid="stStatusWidget"] { display: none; }
.oa-hero {
  background: linear-gradient(135deg, #0F172A 0%, #134E4A 55%, #1D4ED8 135%);
  border-radius: 18px; padding: 28px 32px; margin-bottom: 20px; color: #F8FAFC;
  position: relative; overflow: hidden;
}
.oa-hero::after {
  content: ""; position: absolute; right: -60px; top: -60px;
  width: 220px; height: 220px; border-radius: 50%;
  background: radial-gradient(circle, rgba(255,255,255,.14), transparent 65%);
}
.oa-hero h1 { color: #F8FAFC; font-size: 27px; margin-bottom: 6px; }
.oa-hero p { color: #CBD5E1; margin: 0; font-size: 14px; }
.oa-hero .oa-sub { color: #7C93B0; font-size: 12px; margin-top: 10px; }
.oa-card {
  background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  padding: 16px 18px; margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(15,23,42,0.05);
}
.oa-tag {
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 12px; font-weight: 600; margin-right: 6px;
}
.oa-tag-blue   { background: #DBEAFE; color: #1D4ED8; }
.oa-tag-green  { background: #D1FAE5; color: #065F46; }
.oa-tag-amber  { background: #FEF3C7; color: #92400E; }
.oa-tag-red    { background: #FEE2E2; color: #991B1B; }
.stCodeBlock pre { border-radius: 12px; }

/* ---------- v3 细节打磨 ---------- */
[data-testid="stChatMessage"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 16px; padding: 14px 16px; margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(15,23,42,0.05);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: #EFF6FF; border-color: #BFDBFE;
}
[data-testid="stChatMessage"] p { margin-bottom: 6px; }
[data-testid="stProgress"] div[role="progressbar"] > div { border-radius: 999px; }
[data-testid="stProgress"] div[role="progressbar"] > div > div {
  background: linear-gradient(90deg, #0F766E, #2563EB); border-radius: 999px;
}
[data-testid="stPlotlyChart"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 16px; padding: 10px;
  box-shadow: 0 1px 3px rgba(15,23,42,0.05);
}
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; }
[data-testid="stAlert"] { border-radius: 12px; }
hr { border-color: var(--line); margin: 18px 0; }
textarea:focus, .stTextInput input:focus, .stChatInput textarea:focus {
  border-color: var(--brand) !important;
  box-shadow: 0 0 0 3px rgba(15,118,110,.12) !important;
}
[data-testid="stChatInput"] {
  border-radius: 14px; border: 1px solid var(--line); background: var(--card);
}
div[data-testid="stExpander"] summary { font-weight: 600; }
@media (max-width: 640px) {
  .oa-hero { padding: 20px 18px; border-radius: 14px; }
  .oa-hero h1 { font-size: 22px; }
  main .block-container { padding-left: 12px; padding-right: 12px; }
}
</style>
""", unsafe_allow_html=True)


def hero(title, subtitle, sub2=""):
    """紧凑页头：标题 + 一行说明。不再用大块渐变，保持求职场合的克制。"""
    sub = subtitle or ""
    if sub2:
        sub = f"{sub}　|　{sub2}" if sub else sub2
    st.markdown(
        f'<div class="oa-head"><div class="oa-head-title">{title}</div>'
        f'<div class="oa-head-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def status_tag(status: str):
    m = {"待投": ("oa-tag-blue", "待投"), "已投": ("oa-tag-green", "已投"),
         "排除": ("oa-tag-red", "排除")}
    cls, label = m.get(status, ("oa-tag-amber", status))
    return f'<span class="oa-tag {cls}">{label}</span>'


def render_job_detail(name: str, meta: dict, jd: str):
    """岗位档案：为什么在列表里 + 为什么保留/排除 + 这个岗位要什么人。"""
    head = f"**{meta.get('company') or name}** · {meta.get('city') or '城市未填'}"
    if meta.get("salary"):
        head += f" · 薪资 {meta['salary']}"
    st.markdown(head)

    st.markdown("**① 它是怎么进到列表里的**")
    for r in job_detail.entry_reasons(meta):
        st.markdown(f"- {r['label']}：{r['detail']}")

    st.markdown("**② 为什么保留 / 为什么排除**")
    for r in job_detail.keep_or_drop(meta):
        icon = "✅" if r.get("ok") else ("❔" if r.get("ok") is None else "⛔")
        st.markdown(f"- {icon} {r['label']}：{r['detail']}")

    parts = job_detail.split_jd(jd)
    st.markdown("**③ 这个岗位要什么人**")
    if parts["duty"]:
        st.markdown("岗位职责：")
        st.markdown(parts["duty"][:1200])
    if parts["req"]:
        st.markdown("任职要求：")
        st.markdown(parts["req"][:1200])
    if not parts["duty"] and not parts["req"]:
        st.caption("这份 JD 没有明显的「职责 / 要求」分段，下面是原文：")
        st.text((parts["other"] or jd)[:1200])
    elif parts["other"].strip():
        with st.expander("其他信息 / 原文剩余部分"):
            st.text(parts["other"][:1200])

    report = read_text(MATCH_DIR / f"match_{name}.md")
    if report:
        m = re.search(r"## 结论\s*\n+(.+)", report)
        if m:
            st.markdown("**④ 匹配结论**")
            st.markdown(m.group(1).strip())

    if not isinstance(meta.get("quality"), dict):
        st.caption("这个岗位还没有质量检查结果（早期入库的岗位没有这项）")
    if st.button("🔄 跑一次质量检查并保存", key=f"qc_{name}"):
        meta["quality"] = job_quality.assess({
            "jd": jd, "company": meta.get("company", ""),
            "city": meta.get("city", ""), "salary": meta.get("salary", ""),
            "url": meta.get("source_url", ""),
        })
        save_meta(name, meta)
        st.success("质量检查已保存，刷新后能在上面看到逐项依据")
        st.rerun()


# ============================================================
# 页面：仪表盘
# ============================================================
def page_dashboard():
    hero("OfferAgent", "画像 → 岗位 → 匹配 → 话术 → 投递，一条龙", "余剑 · 南邮网络工程 2027 届 · v2 联网版")
    jobs = list_jobs()
    active = [j for j in jobs if j[1]["status"] != "排除"]
    done = [j for j in jobs if j[1]["status"] == "已投"]
    scored = [j for j in active if j[1]["match_score"] is not None]
    avg = round(sum(j[1]["match_score"] for j in scored) / len(scored)) if scored else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("岗位总数", len(jobs))
    c2.metric("待投", len([j for j in active if j[1]["status"] == "待投"]))
    c3.metric("已投", len(done))
    c4.metric("平均匹配度", f"{avg}%" if scored else "—")

    if not jobs:
        st.info("岗位库为空：去「岗位库」页粘贴第一份 JD 或粘贴招聘页 URL 开始。")
        return
    fig = rank_bar(active)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 🏆 最高匹配岗位")
    top = sorted([j for j in active if j[1]["match_score"]],
                 key=lambda x: -(x[1]["match_score"] or 0))[:3]
    for name, meta, _ in top:
        st.markdown(
            f'<div class="oa-card">'
            f'<b>{meta["name"]}</b> {status_tag(meta["status"])} '
            f'<span class="oa-tag oa-tag-green">{meta["match_score"]}%</span> '
            f'<span style="color:#64748B;font-size:13px">{meta["city"]}</span>'
            f'<br><span style="color:#64748B;font-size:13px">{meta.get("created_at", "")}</span>'
            f'</div>', unsafe_allow_html=True)


# ============================================================
# 页面：我的画像
# ============================================================
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


# ============================================================
# 页面：岗位库（v2 · 支持 URL 一键导入）
# ============================================================
def page_jobs():
    hero("岗位库", "关键词一键搜岗 / 粘 URL 抓 JD / 手动粘贴；自动识别排除规则")
    ensure_dirs()
    tab_search, tab1, tab2 = st.tabs(["🔎 关键词搜岗（联网）", "🔗 URL 导入", "✍️ 手动粘贴"])

    # ---- 关键词搜岗 ----
    with tab_search:
        st.caption("给关键词和城市，程序自己去多个招聘站搜岗位并合并去重，勾选后一键入库。"
                   "默认走「全部平台」，一次把牛客＋实习僧＋BOSS 的结果全捞回来。")
        c1, c2, c3 = st.columns([2, 2, 2])
        kw = c1.text_input("关键词", value="AI", key="src_kw",
                           placeholder="AI / Agent / 大模型 / RAG")
        city = c2.text_input("城市", value="南京", key="src_city")
        src = c3.selectbox("来源", [job_sources.ALL_SOURCES] + job_sources.SOURCES,
                           key="src_name")
        st.caption("牛客最快最稳；实习僧是实验性；BOSS 需要先在调试窗口登录一次"
                   "（终端跑 python -m browser_fetch --setup）。")
        if st.button("🔍 开始搜岗", type="primary", key="do_search"):
            with st.spinner(f"正在搜「{kw}」…（多平台要等十几秒）"):
                try:
                    if src == job_sources.ALL_SOURCES:
                        res = job_sources.search_all(
                            kw.strip(), city.strip(),
                            ask_model=lambda p: ask_chat(p))
                        st.session_state["src_results"] = res["jobs"]
                        st.session_state["src_stats"] = res["by_source"]
                        st.session_state["src_errors"] = res["errors"]
                    else:
                        found = job_sources.search(
                            src, kw.strip(), city.strip(),
                            ask_model=lambda p: ask_chat(p))
                        st.session_state["src_results"] = found
                        st.session_state["src_stats"] = {src: len(found)}
                        st.session_state["src_errors"] = {}
                except Exception as e:
                    st.session_state["src_results"] = []
                    st.error(str(e))
        stats = st.session_state.get("src_stats") or {}
        errors = st.session_state.get("src_errors") or {}
        if stats:
            st.caption("各平台结果：" + "　".join(f"{k} {v} 条" for k, v in stats.items()))
        for k, v in errors.items():
            st.warning(f"{k} 没成功：{v}")
        results = st.session_state.get("src_results", [])
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
        elif results == [] and st.session_state.get("do_search_done"):
            st.warning("没搜到结果。换个关键词或来源试试；BOSS 记得先登录。")
        st.session_state["do_search_done"] = bool(results) or st.session_state.get("do_search_done")

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
            st.warning("先到「我的资料 → 自我蒸馏」生成画像")
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
                            st.warning("先到「我的资料 → 自我蒸馏」生成画像")
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
                                st.warning("先到「我的资料 → 我的简历」准备一份简历")
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
                        if st.button("③ 生成话术", key=f"f3_{name}"):
                            with st.spinner("写话术中…"):
                                try:
                                    ftalk, fhits = generate_talk(
                                        lambda p, *m: ask_chat(p, *m), "boss", fprof, jd)
                                    st.session_state[f"flow_talk_{name}"] = ftalk
                                    st.session_state[f"flow_talkhits_{name}"] = fhits
                                except Exception as e:
                                    st.error(str(e))
                        ftalk = st.session_state.get(f"flow_talk_{name}")
                        if ftalk:
                            st.code(ftalk, language="text")
                            fhits = st.session_state.get(f"flow_talkhits_{name}") or []
                            if fhits:
                                st.warning(f"仍含可疑用语：{fhits}，建议手动改一版")
                        st.markdown("**④ 标记已投**")
                        st.caption("发送由你自己按；这里只负责记录状态，之后 7 天没动静会自动进跟进提醒。")
                        if st.button("④ 我发出去了，标记已投", key=f"f4_{name}"):
                            meta["status"] = "已投"
                            meta["applied_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                            save_meta(name, meta)
                            apply_assist.log_application(name, meta, ftalk or "")
                            st.session_state["flow_done"] = name
                            next_step("applied", defer=True)
                            st.rerun()
                    if st.session_state.get("flow_msg"):
                        st.success(st.session_state.pop("flow_msg"))
                    if st.session_state.get("flow_done") == name:
                        st.caption("已标记已投（见页面底部提示）")
        with cols[1]:
            if not excl and st.button("🔍 匹配", key=f"m_{name}"):
                st.session_state["match_target"] = name
                st.session_state["_go_nav"] = "🔎 岗位"
                st.session_state["_jobs_focus"] = "match"
                st.rerun()
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
def page_talk():
    hero("投递话术", "三个场景按真人说话的方式写；生成后自动检查禁用词并重写")
    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    if not jobs:
        st.info("先到「岗位库」添加岗位")
        return
    name = st.selectbox("选择岗位", [j[0] for j in jobs], key="talk_pick")
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
    variant = list(TALK_VARIANTS.keys())[labels.index(
        st.radio("场景", labels, horizontal=True))]

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
    resume = st.text_area("简历全文（默认读取 v2，可粘贴覆盖）", default_resume,
                          height=300, key="resume_area")
    if st.button("📝 生成简历建议", type="primary"):
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


def resume_source_panel(prefix: str) -> str:
    """简历来源统一面板（导入文件 / 问答生成 / 手动编辑）。返回当前简历全文。

    prefix 用来隔离不同页面的控件 key，避免重复元素 ID。
    """
    key = f"{prefix}_text"
    if key not in st.session_state:
        st.session_state[key] = load_my_resume()

    src = st.radio("简历从哪来",
                   ["📎 导入文件（PDF / Word / 图片 / 文本）",
                    "💬 问答式生成一份", "✍️ 手动编辑"],
                   horizontal=True, key=f"{prefix}_src")

    if "导入" in src:
        st.caption("支持 PDF、Word(.docx)、txt/md，以及简历截图（离线 OCR 识别，约 5-15 秒）。")
        up = st.file_uploader("选择简历文件",
                              type=["pdf", "docx", "txt", "md", "png", "jpg",
                                    "jpeg", "webp", "bmp"],
                              key=f"{prefix}_up")
        if up is not None and st.button("读取这个文件", key=f"{prefix}_read"):
            with st.spinner("读取中…"):
                try:
                    out = doc_io.read_any(up.getvalue(), up.name)
                except Exception as e:
                    out = {"text": "", "method": "失败", "warning": str(e)}
            if out["text"]:
                st.session_state[key] = out["text"]
                st.success(f"读取成功：{out['method']}，{len(out['text'])} 字")
            if out.get("warning"):
                st.warning(out["warning"])
            if not out["text"]:
                st.error("没读到文字。可以改用截图上传，或手动粘贴。")
            st.rerun()
    elif "问答" in src:
        rb = resume_builder.load()
        done, total = resume_builder.progress(rb)
        st.progress(done / total,
                    text=(f"第 {done + 1} / {total} 题" if done < total else "全部答完"))
        q = resume_builder.current(rb)
        if q:
            st.markdown(f"**{q['q']}**")
            st.caption("为什么问这个 / 怎么答有用：" + q["why"])
            val = st.text_area("你的回答", rb["answers"].get(q["k"], ""),
                               key=f"{prefix}_rb_{q['k']}", height=100)
            c1, c2, c3 = st.columns(3)
            if c1.button("提交，下一题", type="primary", key=f"{prefix}_rb_next"):
                resume_builder.answer(rb, val)
                st.rerun()
            if c2.button("跳过这题", key=f"{prefix}_rb_skip"):
                resume_builder.answer(rb, "")
                st.rerun()
            if c3.button("重新开始", key=f"{prefix}_rb_reset"):
                resume_builder.reset()
                st.rerun()
        else:
            st.caption("答完了。生成草稿后，空着的字段会明确列出来，不会替你编。")
            if st.button("📝 生成简历草稿（调用 DeepSeek）", type="primary",
                         key=f"{prefix}_rb_build"):
                with st.spinner("整理中…"):
                    try:
                        draft = resume_builder.build(rb, lambda p: ask_chat(p))
                        (DATA_DIR / "resume_draft.md").write_text(draft, encoding="utf-8")
                        st.session_state[key] = draft
                        st.session_state[f"{prefix}_draft"] = draft
                    except Exception as e:
                        st.error(str(e))
            if st.session_state.get(f"{prefix}_draft"):
                with st.expander("看生成的草稿", expanded=True):
                    st.markdown(st.session_state[f"{prefix}_draft"])

    return st.text_area("简历全文（可编辑）", height=280, key=key)


def page_my_resume():
    """我的简历：管理简历内容本身（不针对具体岗位）。"""
    hero("我的简历", "导入 / 问答生成 / 手动编辑。保存后用于 ATS 覆盖检查和面试准备")
    saved = MY_RESUME_PATH.exists()
    if saved:
        st.success(f"已保存到 {MY_RESUME_PATH.name}（{len(read_text(MY_RESUME_PATH))} 字）")
    else:
        st.info("还没保存过。下面是仓库里已有的简历，改完点保存就会变成「我的简历」。")
    text = resume_source_panel("my")
    c1, c2 = st.columns([1, 3])
    if c1.button("💾 保存为我的简历", type="primary", key="my_save"):
        save_my_resume(text)
        st.success(f"已保存（{len(text)} 字）")
        next_step("resume_saved")
    c2.caption("保存位置：简历/我的简历.md　·　投递里的「简历定制」默认读这份")


def page_resume_tailor():
    """按 JD 定制简历 + ATS 关键词覆盖检查。"""
    hero("简历定制", "按目标岗位检查关键词覆盖，并给重排与改写建议（只重排已有经历，不编）")
    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    if not jobs:
        st.info("先到「岗位」添加岗位")
        return
    name = st.selectbox("目标岗位", [j[0] for j in jobs], key="tailor_pick")
    jd = read_text(JDS_DIR / f"{name}.txt")
    st.caption("简历内容在「我的资料 → 我的简历」里管理；这里默认读你保存的那份。")
    resume = resume_source_panel("tailor")

    if st.button("🔬 检查覆盖 + 给建议（调用 DeepSeek）", type="primary", key="tailor_run"):
        if not resume.strip():
            st.warning("简历内容为空")
            return
        with st.spinner("抽取 JD 关键词 + 本地比对 + 生成建议…"):
            try:
                out = resume_tailor.tailor(resume, jd, lambda p: ask_chat(p))
                st.session_state["tailor_out"] = out
                next_step("ats_done")
            except Exception as e:
                st.error(str(e))

    out = st.session_state.get("tailor_out")
    if not out:
        return
    st.metric("关键词覆盖率", f"{out['rate']}%",
              help="已覆盖算 1 分、部分覆盖算 0.5 分。这是本地字符串比对的结果，不是模型判断。")
    miss = [r for r in out["coverage"] if r["status"] == "缺失"]
    part = [r for r in out["coverage"] if r["status"] == "部分覆盖"]
    c1, c2 = st.columns(2)
    c1.metric("缺失关键词", len(miss))
    c2.metric("部分覆盖", len(part))
    with st.expander("看完整覆盖表（关键词 / 状态 / 类别）", expanded=True):
        for r in out["coverage"]:
            tag = {"已覆盖": "oa-tag-green", "部分覆盖": "oa-tag-amber",
                   "缺失": "oa-tag-red"}.get(r["status"], "oa-tag-blue")
            st.markdown(f'<span class="oa-tag {tag}">{r["status"]}</span> '
                        f'**{r["keyword"]}**　<span style="color:#94A3B8">{r["category"]}</span>',
                        unsafe_allow_html=True)
    if miss:
        st.warning("缺失的关键词：" + "、".join(r["keyword"] for r in miss)
                   + "　→ 简历里没有的不要硬写，先确认你是不是真的做过")
    for key, title in [("reorder.md", "重排建议"), ("bullets.md", "改写建议")]:
        if out["advice"].get(key):
            st.markdown(f"### {title}")
            st.markdown(out["advice"][key])


def page_drill():
    """面试拷问：AI 当面试官，逐题点评。"""
    hero("面试拷问", "AI 当面试官追问你；每答一题给三段反馈。可中断续答")
    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    if not jobs:
        st.info("先到「岗位」添加岗位")
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


def page_applications():
    """投递记录 + 漏斗 + 跟进提醒 + 被拒归因。"""
    hero("投递记录", "漏斗统计、该跟进的、被拒归因，以及每条投递用的话术")
    rows = apply_assist.load_applications()
    all_jobs = list_jobs()
    applied_jobs = [j for j in all_jobs if j[1]["status"] in ("已投", "面试中", "已拒", "Offer")]

    fn = pipeline.funnel(all_jobs)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("已投出去", fn["submitted"])
    c2.metric("有回应（面试中/已拒/Offer）", fn["interviewed"])
    c3.metric("Offer", fn["offers"])
    c4.metric("今天投递", apply_assist.applied_today())
    st.caption(f"回应率 {fn['reply_rate']}%　·　Offer 率 {fn['offer_rate']}%"
               f"　·　统计口径：岗位库里状态为「已投/面试中/已拒/Offer」的岗位")
    g1, g2 = st.columns(2)
    with g1:
        st.markdown("##### 投递转化漏斗")
        if fn["submitted"] > 0:
            st.plotly_chart(v41.funnel_fig(fn["submitted"], fn["interviewed"], fn["offers"]),
                            use_container_width=True)
        else:
            st.caption("还没有投递记录，投几份后这里会出现转化漏斗。")
    with g2:
        st.markdown("##### 近 14 天投递趋势")
        if rows:
            st.plotly_chart(v41.weekly_fig(rows), use_container_width=True)
        else:
            st.caption("还没有投递记录。")

    # 跟进提醒
    follow = pipeline.needs_followup(all_jobs, days=7)
    if follow:
        st.markdown("### ⏰ 该跟进了（投出去超过 7 天没更新状态）")
        for f in follow[:8]:
            st.markdown(f"- **{f['meta'].get('company') or f['name']}** · {f['name']}"
                        f" · 已投 {f['days']} 天")
        st.caption("跟进话术可以去「投递话术」页用「内推消息」或「BOSS 打招呼」模板改写。")
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


def group_today():
    t1, t2, t3 = st.tabs(["今日行动", "求职日报", "数据概览"])
    with t1:
        page_today()
    with t2:
        page_report()
    with t3:
        page_dashboard()


def group_jobs():
    if st.session_state.get("_jobs_focus") == "match":
        if st.button("← 回岗位库列表", key="back_jobs"):
            st.session_state.pop("_jobs_focus", None)
            st.rerun()
        page_match()
        return
    t1, t2, t3, t4 = st.tabs(["岗位库 / 关键词搜岗", "匹配分析", "岗位对比", "公司速查"])
    with t1:
        page_jobs()
    with t2:
        page_match()
    with t3:
        page_compare()
    with t4:
        page_company()



# ============================================================
# 页面：批量投递台（半自动——话术/链接/三件套全备好，发送那一下留给你）
# ============================================================
def page_batch_apply():
    hero("批量投递", "全部待投岗位：批量生成话术 → 逐条确认 → 复制 / 打开 / 标记已投。"
                    "发送那一下永远留给你（自动群发会被平台风控封号）")
    jobs = [j for j in list_jobs() if j[1]["status"] == "待投"]
    if not jobs:
        st.info("当前没有待投岗位。去「🔎 岗位」把岗位状态设为「待投」。")
        return
    st.markdown(f"待投 **{len(jobs)}** 家　·　今日已投 **{apply_assist.applied_today()}** 家")

    c1, c2 = st.columns([1, 3])
    if c1.button("⚡ 批量生成全部话术", type="primary", key="bg_gen"):
        fprof = read_text(PROFILE_PATH) or read_text(ME_PATH)
        if not fprof.strip():
            st.warning("先到「我的资料 → 自我蒸馏」生成画像")
        else:
            queue = {}
            with st.spinner(f"为 {len(jobs)} 家生成 BOSS 话术…（每家几秒）"):
                for n, m, jd in jobs:
                    try:
                        t, h = generate_talk(lambda p, *mm: ask_chat(p, *mm),
                                             "boss", fprof, jd or "")
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
                ok = apply_assist.open_url(m.get("source_url", ""))
                st.toast("已在浏览器打开" if ok else "该岗位没有链接", icon="✅" if ok else "⚠️")
            if cc[2].button("✏️ 保存修改", key=f"bs_{n}"):
                queue[n] = {"talk": talk, "hits": q.get("hits", [])}
                write_text(TALKQ_PATH, json.dumps(queue, ensure_ascii=False, indent=2))
                st.toast("已保存", icon="✅")
            if cc[3].button("✅ 发出去了，标记已投", type="primary", key=f"bm_{n}"):
                m["status"] = "已投"
                m["applied_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                save_meta(n, m)
                apply_assist.log_application(n, m, talk or q.get("talk", ""))
                st.session_state["_pending_hint"] = f"已标记投递：{comp}"
                st.rerun()



def group_apply():
    t1, t2, t3, t4, t5 = st.tabs(
        ["投递话术", "简历定制 / ATS", "面试拷问", "投递记录", "⚡ 批量投递"])
    with t1:
        page_talk()
    with t2:
        page_resume_tailor()
    with t3:
        page_drill()
    with t4:
        page_applications()
    with t5:
        page_batch_apply()


def group_distill():
    # 注意：问答式用了 st.chat_input，必须放在页面级（不能塞进 tab），所以这里用 radio 切
    mode = st.radio("模式", ["💬 问答式（推荐）", "📋 填表式"],
                    horizontal=True, key="distill_mode")
    if "问答" in mode:
        page_distill_chat()
    else:
        page_profile()




# ============================================================
# 公开数字人名片页（?twin=1）：考官/HR 知情访问
# 合规说明：AI 分身基于真实画像回答，不冒充本人，最终以真人沟通为准。
# ============================================================
def page_twin_portal():
    profile = read_text(PROFILE_PATH) or read_text(ME_PATH)
    me = read_text(ME_PATH)
    if not profile.strip():
        st.warning("画像未生成，先去「我的资料 → 自我蒸馏」。")
        return

    # ---- 名片头 ----
    st.markdown(
        '<div style="padding:14px 20px;border-radius:14px;'
        'background:linear-gradient(135deg,#10131a,#1b2a4a);color:#fff;'
        'display:flex;align-items:center;gap:16px;flex-wrap:wrap;">'
        '<div style="font-size:34px;">🧑\u200d💻</div>'
        '<div><div style="font-size:22px;font-weight:700;">余剑 · AI 应用开发实习生</div>'
        '<div style="opacity:.82;font-size:13px;">南京邮电大学 · 网络工程 2027 届 · 南京优先，可远程 · LLM / RAG / Agent</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "🪞 这是余剑的 **AI 数字分身**——基于他的真实项目与画像实时回答，"
        "用于提前了解候选人。最终以本人沟通为准。")

    tabs = st.tabs(["🧑\u200d💻 我是谁", "🚀 项目证据", "💬 问数字人"])

    # ---- 我是谁 ----
    with tabs[0]:
        st.markdown("#### 基本信息")
        base = [
            ("学历", "南京邮电大学 · 网络工程 · 本科 · 2027 届"),
            ("坐标", "南京（南京 onsite 优先，可远程）"),
            ("求职方向", "AI 应用开发 / Agent 开发实习；次选大模型评测"),
            ("到岗", "2026.09 下旬起 · 4–5 天/周 · 可 3–6 个月"),
            ("邮箱", "yj2994762833@gmail.com"),
        ]
        for k, v in base:
            st.markdown(f"**{k}**　{v}")
        st.markdown("---")
        st.markdown("#### 技能与项目（数字人记忆）")
        if me:
            # 只取 me.txt 里给"人看"的部分
            body = me
            for mark in ["## 硬约束", "## 我想找什么岗位"]:
                i = body.find(mark)
                if i > 0:
                    body = body[:i]
            st.markdown(body)
        else:
            with st.expander("查看画像全文", expanded=False):
                st.markdown(profile)

    # ---- 项目证据 ----
    with tabs[1]:
        st.markdown("#### 可点开验证的项目")
        st.markdown(
            '<div style="padding:14px 18px;border:1px solid #e4e3dd;border-radius:12px;margin-bottom:10px;">'
            '<div style="font-weight:700;">🌐 上线项目 · RAG 知识库问答系统</div>'
            '<div style="font-size:13px;color:#5f6670;">11 篇资料 → 254 块向量库 · top-1/3/5 命中率 75% / 83% / 92% · 带引用溯源 · 公开可访问</div>'
            '<a href="https://ai-learning-fphncazxmg3pnesntwchz6.streamlit.app/" style="font-size:13px;">打开应用 →</a>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="padding:14px 18px;border:1px solid #e4e3dd;border-radius:12px;margin-bottom:10px;">'
            '<div style="font-weight:700;">📦 GitHub 代码仓库</div>'
            '<div style="font-size:13px;color:#5f6670;">RAG 全链路 + Agent 工具调用 + OfferAgent 求职智能体（本名片就是它的功能之一）</div>'
            '<a href="https://github.com/yjmyp/ai-learning" style="font-size:13px;">github.com/yjmyp/ai-learning →</a>'
            '</div>',
            unsafe_allow_html=True,
        )
        pdf_path = Path(__file__).resolve().parent.parent / "简历" / "余剑-应聘AI应用开发实习-本科.pdf"
        if pdf_path.exists():
            try:
                st.download_button("📄 下载简历 PDF", data=pdf_path.read_bytes(),
                                   file_name="余剑-应聘AI应用开发实习-本科.pdf",
                                   mime="application/pdf", key="dl_pdf")
            except Exception:
                st.caption("（简历 PDF 暂不可用，可邮件索取）")
        else:
            st.caption("（简历 PDF 待上传）")
        st.markdown("---")
        st.markdown("#### 想知道更深入的？")
        st.caption("在「💬 问数字人」里问它：项目怎么做、踩过什么坑、网络工程背景怎么结合 AI……")

    # ---- 问数字人 ----
    with tabs[2]:
        st.markdown("#### 问他任何问题")
        st.caption("回答由 AI 基于他的真实画像实时生成；若画像里没有，它会直接说没有。")
        preset = st.selectbox(
            "预设问题（先试试这些）",
            ["", "介绍下你的 RAG 项目，做了什么、做到什么程度",
             "你做过 Agent 相关的东西吗？",
             "你的网络工程背景对做 AI 应用有什么帮助？",
             "你最大的短板是什么？",
             "为什么想投 AI 应用开发实习？",
             "你怎么评估你的 RAG 系统效果？"],
            key="portal_preset")
        q = st.text_area("或输入你自己的问题", key="portal_q", height=80,
                         placeholder="例：你的 RAG 系统如果检索出来全是错的，怎么办？")
        ask_what = (q.strip() or preset).strip()
        if st.button("让数字人回答", type="primary", key="portal_go"):
            if not ask_what:
                st.warning("先选预设问题或输入问题")
            else:
                with st.spinner("数字分身思考中…"):
                    try:
                        st.session_state["portal_last"] = (
                            ask_what,
                            digital_twin.twin_answer(profile, ask_what,
                                                     lambda p: ask_chat(p)),
                        )
                    except Exception as e:
                        st.error(str(e))
        last = st.session_state.get("portal_last")
        if last:
            st.markdown(f"**问：** {last[0]}")
            st.markdown(
                f'<div class="oa-card" style="margin-top:6px;">💬 数字人：{last[1]}</div>',
                unsafe_allow_html=True,
            )
            st.caption("提示：以上回答基于公开画像生成。正式沟通请直接联系本人。")


# ============================================================
# 页面：数字分身（合规版：替你准备，真人上场）
# ============================================================
def page_twin():
    hero("数字分身", "你的画像 + 简历 + 复盘 = 分身。它替你准备，真人上场的是你")
    profile = read_text(PROFILE_PATH) or read_text(ME_PATH)
    if not profile.strip():
        st.warning("先到「🧬 自我蒸馏」生成画像，分身才有「记忆」。")
        return
    t1, t2, t3 = st.tabs(["🪞 分身档案", "🎤 面试陪练", "🧠 复盘与进化"])

    with t1:
        st.markdown("### 分身是什么")
        st.caption("分身 = 你的画像（事实）+ 你的简历（证明）+ 你的复盘（记忆）。"
                   "它可以陪你练面试、替你定制话术、帮你复盘进化，"
                   "但**不会替你本人去面试，也不会替你按下发送**。")
        with st.expander("📄 分身当前记忆（画像全文）", expanded=False):
            st.markdown(profile)

    with t2:
        mode = st.radio("陪练模式",
                        ["🪞 扮演我（你出题，分身用你的事实回答，学参考话术）",
                         "🎤 模拟面试官（AI 出 10 题逐题拷问）"],
                        horizontal=True)
        if "扮演我" in mode:
            st.caption("这是参考回答，不是替考。你本人上场时，用自己的话说会更真实。")
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
        else:
            st.info("模拟面试官（10 题拷问 + 逐题点评 + 总评）在「✉️ 投递 → 面试拷问」。"
                    "建议流程：先陪练扮演我学话术 → 再上拷问模式被虐 → 复盘写回画像。")
        st.markdown("---")
        st.markdown("##### 📝 投前定制（自我介绍 / 反问清单）")
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
            io = st.session_state.get("intro_out", "")
            if io:
                st.markdown(io)
            ao = st.session_state.get("askback_out", "")
            if ao:
                st.markdown(ao)
        else:
            st.caption("先到「岗位库」添加岗位，才能按目标公司定制。")

    with t3:
        st.markdown("##### 🧠 面试复盘入库（让分身记住你）")
        st.caption("每场面试后花 2 分钟记下来，分身提炼「被认可/被挑战」，画像越用越准。")
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
        ra = st.session_state.get("rev_adv", "")
        if ra:
            st.markdown(ra)
            st.caption("（更新建议由你确认后再手动写进画像/简历，分身不自动改你的画像）")
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
        ro = st.session_state.get("radar_out", "")
        if ro:
            st.markdown(ro)




def group_me():
    """我的资料：简历本身 + 自我蒸馏（画像 / 数字分身）。"""
    mode = st.radio("内容", ["📄 我的简历", "🧬 自我蒸馏", "🪞 数字分身"],
                    horizontal=True, key="me_mode")
    if "简历" in mode:
        page_my_resume()
    elif "数字分身" in mode:
        page_twin()
    else:
        group_distill()


def pipeline_bar():
    """顶部流程进度条：找岗 → 匹配 → 已投 → 有回应。看清自己卡在哪一步。"""
    jobs = list_jobs()
    total = len(jobs)
    matched = sum(1 for _, m, _ in jobs if m.get("match_score") is not None)
    applied = sum(1 for _, m, _ in jobs
                  if m["status"] in ("已投", "面试中", "已拒", "Offer"))
    replied = sum(1 for _, m, _ in jobs
                  if m["status"] in ("面试中", "已拒", "Offer"))
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("① 找岗（入库）", total)
    c2.metric("② 跑过匹配", matched)
    c3.metric("③ 已投出去", applied)
    c4.metric("④ 有回应", replied)
    try:
        tgt = int(json.loads(read_text(CONFIG_PATH, "{}")).get("daily_target", 3) or 3)
    except Exception:
        tgt = 3
    today = apply_assist.applied_today()
    if today >= tgt:
        st.success(f"今天的投递目标已完成：{today} / {tgt} 家")
    else:
        st.info(f"今天投递 {today} / {tgt} 家，还差 {tgt - today} 家。"
                "投递是唯一能把上面这些数字变成「有回应」的动作。")


def check_auth():
    """L1 密码门：配置了密码才启用；未配置 = 本地开发免登录。"""
    pw = ""
    try:
        pw = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        pass
    if not pw:
        pw = os.environ.get("APP_PASSWORD", "")
    pw_hash = ""
    if not pw:
        try:
            _c = json.loads(read_text(CONFIG_PATH, "{}"))
            pw_hash = _c.get("app_password_hash", "") or ""
        except Exception:
            pass
    if not pw and not pw_hash:
        return
    if st.session_state.get("auth_ok"):
        return
    st.title("🔒 OfferAgent")
    st.caption("这个应用设置了访问密码（部署时在 Secrets 填 APP_PASSWORD，"
               "或在本机「设置」页设置）。")
    guess = st.text_input("访问密码", type="password", key="auth_pw")
    if st.button("进入", type="primary", key="auth_go"):
        ok = False
        if pw and guess == pw:
            ok = True
        elif pw_hash and v41.hash_password(guess) == pw_hash:
            ok = True
        if ok:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("密码不对")
    st.stop()


def main():
    _twin = "1" in str(st.query_params.get("twin", ""))
    st.set_page_config(
        page_title="余剑 · AI 求职数字名片" if _twin else "OfferAgent · 求职智能体",
        page_icon="🪞" if _twin else "🎯",
        layout="wide", initial_sidebar_state="expanded")
    if _twin:
        page_twin_portal()
        return
    check_auth()
    # 主题：存在 data/config.json 的 theme 字段里
    try:
        _cfg = json.loads(read_text(CONFIG_PATH, "{}"))
    except Exception:
        _cfg = {}
    theme_names = list(theme.THEMES.keys())
    theme_now = _cfg.get("theme") or theme_names[0]
    if theme_now not in theme_names:
        theme_now = theme_names[0]
    inject_css(theme_now)
    ensure_dirs()

    with st.sidebar:
        st.markdown("## 🎯 OfferAgent")
        st.caption("求职工作台 · v4")
        picked_theme = st.selectbox("界面风格（可切换对比）", theme_names,
                                    index=theme_names.index(theme_now),
                                    key="theme_pick")
        if picked_theme != theme_now:
            _cfg["theme"] = picked_theme
            write_text(CONFIG_PATH, json.dumps(_cfg, ensure_ascii=False, indent=2))
            st.rerun()
        st.divider()
        # 待跳转的导航（在 widget 创建前设置才合法）
        _go = st.session_state.pop("_go_nav", None)
        if _go:
            st.session_state["nav"] = _go
        nav = st.radio("导航",
                       ["🚀 今日", "📋 我的资料", "🔎 岗位", "✉️ 投递", "⚙️ 设置"],
                       key="nav")
        st.divider()
        jobs_all = list_jobs()
        pending_n = sum(1 for _, m, _ in jobs_all if m["status"] == "待投")
        applied_n = sum(1 for _, m, _ in jobs_all if m["status"] == "已投")
        st.markdown(
            f'<div class="oa-side-stat">待投 <b>{pending_n}</b>　已投 <b>{applied_n}</b>'
            f'<br>今天已投 <b>{apply_assist.applied_today()}</b></div>',
            unsafe_allow_html=True,
        )
        st.divider()
        st.caption("搜岗 → 匹配 → 话术 → 投递 → 复盘")

    pages = {
        "🚀 今日": group_today,
        "📋 我的资料": group_me,
        "🔎 岗位": group_jobs,
        "✉️ 投递": group_apply,
        "⚙️ 设置": page_settings,
    }
    if nav != "⚙️ 设置":
        pipeline_bar()
        st.divider()
    pages.get(nav, group_today)()
    pending = st.session_state.pop("_pending_hint", "")
    if pending:
        st.success("✅ " + pending)


if __name__ == "__main__":
    main()
