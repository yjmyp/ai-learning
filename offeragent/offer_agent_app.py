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
USAGE_PATH = DATA_DIR / "usage.json"
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
import resume_clean  # noqa: E402  简历文本清洗（剔除本地路径 / 编码乱码）
import resume_templates  # noqa: E402  简历排版模板（classic / sidebar / compact）

REPORTS_DIR = DATA_DIR / "reports"

# ============================================================
# 页面域模块（2026-09-29 拆分，减小单文件体积）
# ============================================================
from pages_home import *
from agent_trace_view import page_agent_trace
from pages_work import *
from pages_match import *
from pages_more import *
from pages_resume import *
from pages_agent import *
from pages_apply import *
from pages_twin import *

# ============================================================
# 分层重构（2026-09-29）：数据层 store / AI 层 llm / 渲染层 ui_kit
# ============================================================
from store import (ensure_dirs, read_text, write_text, load_my_resume, save_my_resume,
                   load_meta, save_meta, list_jobs, save_new_job, detect_network_exclude,
                   read_logs, audit_scores, check_apply_allowed, mark_applied)
from llm import (get_api_key, get_model, daily_limit, usage_left, ask_model, ask_chat,
                 extract_score, parse_report, extract_dim_scores)
from ui_kit import (NEXT_HINTS, next_step, score_color, score_gauge, dim_radar, rank_bar,
                    inject_css, hero, status_tag, render_section_cards, render_job_detail)

# 云端持久化（Streamlit Cloud 无持久磁盘）：有 GITHUB_PAT 且岗位库为空 → 启动时自动拉取
if os.environ.get("GITHUB_PAT") and not (DATA_DIR / "jds").exists():
    try:
        from sync_data import pull
        pull()
        st.caption("已从私有仓库恢复岗位数据")
    except Exception as _e:
        st.warning(f"数据同步跳过：{_e}")


# ============================================================
# 页面：今日行动（行动导向首屏）
# ============================================================
def page_today_hub():
    """今天：要做什么 + 做得怎么样。统计放进同一页的第二个页签，口径只有这一处。"""
    t1, t2, t3 = st.tabs(["行动清单", "数据与日志", "Agent 运行记录"])
    with t1:
        page_today()
    with t2:
        page_data_log()
    with t3:
        page_agent_trace()


def page_interview():
    """面试：被拷问 → 让分身陪练 → 复盘写回画像。三件事一个闭环。"""
    t1, t2, t3 = st.tabs(["面试拷问", "分身陪练", "复盘入库"])
    profile = read_text(PROFILE_PATH) or read_text(ME_PATH)
    with t1:
        page_drill()
    with t2:
        twin_practice_section(profile)
    with t3:
        twin_review_section(profile)


def build_pages():
    """注册所有页面（侧边栏按分区显示）。返回 dict 给 st.navigation。

    注意：Streamlit 侧边栏最多直接显示 10 个页面，多的会被折叠成「View more」。
    核心 10 页 + 第 11 页「Agent 流程」（引擎接入）——折叠进 View more 不影响使用。
    """
    profile = read_text(PROFILE_PATH) or read_text(ME_PATH)
    spec = [
        ("主线", [
            ("today", "今天（行动 + 数据）", "🚀", page_today_hub, True),
        ]),
        ("找工作", [
            ("jobs", "岗位库", "🔎", page_jobs, False),
            ("match", "匹配分析", "🎯", page_match, False),
            ("resume", "简历（模板 / 照片 / 覆盖）", "📄", page_resume, False),
            ("apply", "投递台", "✉️", page_apply_desk, False),
            ("records", "投递记录", "📋", page_applications, False),
            ("agent", "Agent 流程（引擎演示）", "🤖", page_agent, False),
        ]),
        ("我的", [
            ("distill", "自我蒸馏", "🧬", distill_section, False),
            ("interview", "面试准备（拷问 / 陪练 / 复盘）", "🎤", page_interview, False),
        ]),
        ("对外", [
            ("show", "名片与分享", "📇", page_show, False),
        ]),
        ("其它", [
            ("settings", "设置", "⚙️", page_settings, False),
        ]),
    ]
    sections, flat = {}, {}
    for section, items in spec:
        pages = []
        for key, title, icon, fn, is_default in items:
            pg = st.Page(fn, title=title, icon=icon,
                         url_path=key, default=is_default)
            pages.append(pg)
            flat[key] = pg
        sections[section] = pages
    PAGES.clear()
    PAGES.update(flat)
    return sections


def page_resume():
    """简历：一个页面装两件事——内容/模板/照片 + 按岗位的覆盖检查。"""
    t1, t2 = st.tabs(["简历内容 / 模板 / 照片", "按岗位检查覆盖（ATS）"])
    with t1:
        page_my_resume()
    with t2:
        page_resume_tailor(embedded=True)

# ============================================================
# 页面：Agent 流程（引擎接入 —— 模型自主规划工具链）
# ============================================================
def pipeline_bar():
    """顶部流程条：一行看完自己在哪一步（不抢统计页的活）。"""
    jobs = list_jobs()
    total = len(jobs)
    matched = sum(1 for _, m, _ in jobs if m.get("match_score") is not None)
    applied = sum(1 for _, m, _ in jobs
                  if m["status"] in ("已投", "面试中", "已拒", "Offer"))
    replied = sum(1 for _, m, _ in jobs
                  if m["status"] in ("面试中", "已拒", "Offer"))
    try:
        tgt = int(json.loads(read_text(CONFIG_PATH, "{}")).get("daily_target", 3) or 3)
    except Exception:
        tgt = 3
    today = apply_assist.applied_today()
    st.markdown(
        f'<div class="oa-flow">'
        f'<span class="oa-flow-step">① 找岗 <b>{total}</b></span>'
        f'<span class="oa-flow-arrow">→</span>'
        f'<span class="oa-flow-step">② 跑过匹配 <b>{matched}</b></span>'
        f'<span class="oa-flow-arrow">→</span>'
        f'<span class="oa-flow-step">③ 已投 <b>{applied}</b></span>'
        f'<span class="oa-flow-arrow">→</span>'
        f'<span class="oa-flow-step">④ 有回应 <b>{replied}</b></span>'
        f'<span class="oa-flow-today">今天 {today} / {tgt}'
        f'{"　✅ 达标" if today >= tgt else "　还差 " + str(tgt - today) + " 家"}</span>'
        f'</div>', unsafe_allow_html=True)


def _is_cloud() -> bool:
    """粗判是否跑在 Streamlit Community Cloud（云端仓库挂在 /mount/src 下）。"""
    try:
        return str(BASE_DIR).replace("\\", "/").startswith("/mount/src")
    except Exception:
        return False


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
        if _is_cloud():
            st.error("⚠️ 这个应用跑在公网，但没有设置访问密码。任何拿到链接的人都能用你的 "
                     "DeepSeek Key 花钱。请到 Manage app → Settings → Secrets 加一行：\n\n"
                     "```toml\nAPP_PASSWORD = \"你自己的密码\"\n```\n\n"
                     "保存后应用会自动重启，刷新本页就会出现密码框。")
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
    theme_names = list(theme.THEMES.keys())
    st.set_page_config(
        page_title="余剑 · AI 求职数字名片" if _twin else "OfferAgent · 求职智能体",
        page_icon="🪞" if _twin else "🎯",
        layout="wide", initial_sidebar_state="expanded")
    if _twin:
        # 名片页也要套主题样式，否则会是 Streamlit 默认长相
        try:
            _tcfg = json.loads(read_text(CONFIG_PATH, "{}"))
        except Exception:
            _tcfg = {}
        _tn = _tcfg.get("theme") or theme_names[0]
        inject_css(_tn if _tn in theme_names else theme_names[0])
        ensure_dirs()
        page_twin_portal()
        return
    check_auth()
    # 主题：存在 data/config.json 的 theme 字段里
    try:
        _cfg = json.loads(read_text(CONFIG_PATH, "{}"))
    except Exception:
        _cfg = {}
    theme_now = _cfg.get("theme") or theme_names[0]
    if theme_now not in theme_names:
        theme_now = theme_names[0]
    inject_css(theme_now)
    ensure_dirs()

    # 原生多页导航：侧边栏自动生成「分区 + 页」两级结构，每页有真实 URL
    pg = st.navigation(build_pages(), position="sidebar")

    with st.sidebar:
        st.divider()
        picked_theme = st.selectbox("界面风格（可切换对比）", theme_names,
                                    index=theme_names.index(theme_now),
                                    key="theme_pick")
        if picked_theme != theme_now:
            _cfg["theme"] = picked_theme
            write_text(CONFIG_PATH, json.dumps(_cfg, ensure_ascii=False, indent=2))
            st.rerun()
        jobs_all = list_jobs()
        pending_n = sum(1 for _, m, _ in jobs_all if m["status"] == "待投")
        applied_n = sum(1 for _, m, _ in jobs_all if m["status"] == "已投")
        st.markdown(
            f'<div class="oa-side-stat">待投 <b>{pending_n}</b>　已投 <b>{applied_n}</b>'
            f'<br>今天已投 <b>{apply_assist.applied_today()}</b></div>',
            unsafe_allow_html=True,
        )
        _left, _lim = usage_left()
        st.caption("今天模型调用：**不限**" if _lim <= 0
                   else f"今天模型调用：**{_lim - _left} / {_lim}** 次")

    # 流程条贴在每个页面上方；设置页不需要
    if pg.url_path != "settings":
        pipeline_bar()
        st.divider()
    pg.run()
    pending = st.session_state.pop("_pending_hint", "")
    if pending:
        st.success("✅ " + pending)


if __name__ == "__main__":
    main()
