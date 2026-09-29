# -*- coding: utf-8 -*-
"""
llm.py —— OfferAgent AI 调用层（2026-09-29 从 offer_agent_app.py 抽出）
============================================================================
API Key 解析、每日额度保护、模型调用、匹配报告解析。不依赖页面。
"""
import json
import os
import re
import time

import requests
import streamlit as st

from store import CONFIG_PATH, USAGE_PATH, read_text, write_text

API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
MODEL_OPTIONS = ["deepseek-chat", "deepseek-v4-flash"]


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


def daily_limit() -> int:
    """每天允许的模型调用次数上限（防公开链接被人刷费用）。
    优先级：Secrets 的 DAILY_CALL_LIMIT > 环境变量 > 本地 config.json > 默认 200。"""
    raw = ""
    try:
        raw = st.secrets.get("DAILY_CALL_LIMIT", "")
    except Exception:
        raw = ""
    if not raw:
        raw = os.environ.get("DAILY_CALL_LIMIT", "")
    if not raw:
        try:
            raw = json.loads(read_text(CONFIG_PATH, "{}")).get("daily_call_limit", "")
        except Exception:
            raw = ""
    try:
        n = int(raw)
        return n if n > 0 else 0        # 0 = 不限（明确设 0 才关闭保护）
    except Exception:
        return 200


def _usage_today() -> dict:
    """今天的调用计数，按日期自动归零。"""
    today = time.strftime("%Y-%m-%d")
    try:
        u = json.loads(read_text(USAGE_PATH, "{}"))
    except Exception:
        u = {}
    if not isinstance(u, dict) or u.get("date") != today:
        u = {"date": today, "calls": 0}
    return u


def _bump_usage() -> int:
    u = _usage_today()
    u["calls"] = int(u.get("calls", 0)) + 1
    try:
        USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        write_text(USAGE_PATH, json.dumps(u, ensure_ascii=False))
    except Exception:
        pass
    return u["calls"]


def usage_left() -> tuple:
    """返回 (今天剩余次数, 上限)。上限为 0 表示不限。"""
    lim = daily_limit()
    used = int(_usage_today().get("calls", 0))
    if lim <= 0:
        return (-1, 0)
    return (max(lim - used, 0), lim)


def ask_model(messages: list, model: str = None) -> str:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("未配置 API Key：请到「设置」页填入 DeepSeek API Key")
    lim = daily_limit()
    used = int(_usage_today().get("calls", 0))
    if used >= lim:
        raise RuntimeError(
            f"今天的模型调用额度已用完（上限 {lim} 次）。这是防止公开链接被人刷费用的保护。"
            f"要放宽就把 Secrets / 设置里的 DAILY_CALL_LIMIT 调大，或者明天再用。")
    _bump_usage()
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
