# -*- coding: utf-8 -*-
"""
v41 · OfferAgent v4.1 增强模块
==============================
batch_match          批量匹配（待投且未匹配的岗位一次跑完，自动写报告+回填分数）
check_links          岗位链接有效性检测（投递前重访 URL，提示"链接已失效"）
funnel_fig           投递漏斗图（已投 → 面试 → Offer）
weekly_fig           投递周趋势线（近 14 天每天投递数）
talk_attachments     投递三件套（简历 PDF + 上线项目 + GitHub）
interview_reminders  面试日历提醒（状态"面试中"的岗位倒计时）
hash_password        密码哈希（L1 密码门用）
"""
import datetime
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go
import requests

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
JDS_DIR = DATA_DIR / "jds"
MATCH_DIR = DATA_DIR / "match_results"
LOG_PATH = DATA_DIR / "applications.jsonl"

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# ---------- 文件小工具（不依赖 app，独立可用） ----------

def read_text(p):
    try:
        return Path(p).read_text(encoding="utf-8")
    except Exception:
        return ""


def write_text(p, s):
    try:
        Path(p).write_text(s, encoding="utf-8")
        return True
    except Exception:
        return False


def load_meta(name):
    p = JDS_DIR / f"{name}.meta.json"
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def save_meta(name, meta):
    try:
        (JDS_DIR / f"{name}.meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def extract_score(text):
    """从匹配报告第一行提匹配度（# 匹配度：82%）。"""
    m = re.search(r"匹配度[:：]?\s*(\d{1,3})\s*%", text or "")
    if m:
        return min(100, max(0, int(m.group(1))))
    return None


# ---------- 1. 批量匹配 ----------

def batch_match(prompt, ask, jobs, profile, progress=None):
    """对全部「待投且未匹配」岗位跑匹配。

    ask: fn(prompt, *materials) -> str
    progress: st.progress 对象（可选）
    返回 [(name, score)]
    """
    todo = [(n, m, j) for n, m, j in jobs
            if m["status"] == "待投" and m.get("match_score") is None]
    if not todo:
        return []
    done = []
    total = len(todo)
    for i, (name, meta, jd) in enumerate(todo):
        try:
            rep = ask(prompt, profile, jd)
            MATCH_DIR.mkdir(parents=True, exist_ok=True)
            write_text(MATCH_DIR / f"match_{name}.md", rep)
            score = extract_score(rep)
            if score is not None:
                meta["match_score"] = score
                save_meta(name, meta)
            done.append((name, score))
            if progress is not None:
                progress.progress((i + 1) / total,
                                  text=f"已匹配 {name}：{score if score is not None else '失败'}%")
        except Exception as e:
            done.append((name, None))
            if progress is not None:
                progress.progress((i + 1) / total, text=f"{name} 出错：{str(e)[:40]}")
    return done


# ---------- 2. 链接有效性检测 ----------

def check_links(jobs):
    """投递前重访岗位链接。

    返回 [(name, company, url, status)]，status ∈ ok / gone / unreachable / no_url
    - gone: 404/410（明确失效，别投了）
    - unreachable: 连不上（网络/超时/反爬 5xx，需人工确认）
    - ok: 可访问（含 403/405 等反爬响应，不代表失效）
    """
    out = []
    for name, meta, _ in jobs:
        url = (meta.get("source_url") or "").strip()
        if not url:
            out.append((name, meta.get("company", "") or name, "", "no_url"))
            continue
        try:
            r = requests.head(url, timeout=6, allow_redirects=True, headers=UA)
            code = r.status_code
            if code in (404, 410):
                status = "gone"
            elif code in (401, 403, 405, 429):
                status = "ok"  # 反爬/需要登录，不代表岗位下架
            elif code < 500:
                status = "ok"
            else:
                status = "unreachable"
        except Exception:
            status = "unreachable"
        out.append((name, meta.get("company", "") or name, url, status))
    return out


# ---------- 3. 投递漏斗图 ----------

def funnel_fig(submitted, interviewed, offers):
    """已投 → 面试 → Offer 转化漏斗。"""
    fig = go.Figure(go.Funnel(
        y=["已投", "面试", "Offer"],
        x=[submitted, interviewed, offers],
        textinfo="value+percent initial",
        marker=dict(color=["#2563EB", "#0EA5E9", "#10B981"]),
        textfont=dict(size=13),
    ))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10),
                      showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
    return fig


# ---------- 4. 投递周趋势 ----------

def weekly_fig(rows, days=14):
    """近 days 天每天投递数折线。rows = applications.jsonl 读出的记录列表。"""
    by_date = defaultdict(int)
    for r in rows:
        d = r.get("date")
        if d:
            by_date[d] += 1
    today = datetime.date.today()
    xs, ys = [], []
    for i in range(days - 1, -1, -1):
        d = (today - datetime.timedelta(days=i)).isoformat()
        xs.append(d[5:])
        ys.append(by_date.get(d, 0))
    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="lines+markers",
        line=dict(color="#2563EB", width=2),
        marker=dict(size=6, color="#1D4ED8"),
        fill="tozeroy",
        fillcolor="rgba(37,99,235,0.08)",
    ))
    fig.update_layout(
        height=260, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="日期", tickfont=dict(size=11)),
        yaxis=dict(title="投递数", dtick=1, tickfont=dict(size=11)),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ---------- 5. 投递三件套 ----------

RESUME_PDF = HERE.parent / "简历" / "余剑-应聘AI应用开发实习-本科.pdf"
LIVE_URL = "https://ai-learning-fphncazxmg3pnesntwchz6.streamlit.app/"
GITHUB_URL = "https://github.com/yjmyp/ai-learning"


def talk_attachments() -> str:
    """话术尾部自动附的投递三件套。"""
    parts = []
    if RESUME_PDF.exists():
        parts.append(f"简历 PDF：{RESUME_PDF}")
    parts.append(f"上线项目：{LIVE_URL}")
    parts.append(f"GitHub：{GITHUB_URL}")
    return "\n".join(parts)


# ---------- 6. 面试日历提醒 ----------

def interview_reminders(jobs):
    """返回 [(name, company, date, days_left)]，按剩余天数升序。

    days_left < 0 表示已过日期（提示补状态）。
    """
    out = []
    today = datetime.date.today()
    for name, meta, _ in jobs:
        d = (meta.get("interview_date") or "").strip()
        if meta["status"] != "面试中" or not d:
            continue
        try:
            dt = datetime.date.fromisoformat(d)
            days = (dt - today).days
            out.append((name, meta.get("company", "") or name, d, days))
        except Exception:
            continue
    out.sort(key=lambda x: x[3])
    return out


# ---------- 7. 密码哈希 ----------

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()
