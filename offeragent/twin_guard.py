# -*- coding: utf-8 -*-
"""公开数字名片的额度守卫：防"一个链接被刷光当天模型额度"。

背景（真实风险）：`?twin=1` 名片页是免密的，面试官点开就能提问，而每次提问都会
用我的 DeepSeek Key 调模型。原先只有 llm.py 的**全局每日 200 次**上限——
意味着任何人拿到链接就能把当天额度一次性刷光，我和 HR 当天都用不了（成本不大，但属于典型的低成本 DoS）。

两道闸：
  1. 按访问者（IP）每日上限，默认 8 次——正常面试官问不出第 9 个问题；
  2. 名片页**总**每日上限，默认 60 次——就算有人换 IP 刷，也把整体消耗压在小范围内。

可调：环境变量 / Streamlit Secrets 里的 `TWIN_PER_IP_LIMIT`、`TWIN_DAILY_LIMIT`。
计数落在 `offeragent/data/twin_quota.json`（本地文件，云端随容器生命周期，重建即清零——够用且零依赖）。
"""
import json
import os
import time
from pathlib import Path

HERE = Path(__file__).parent
QUOTA_PATH = HERE / "data" / "twin_quota.json"

DEFAULT_PER_IP = 8
DEFAULT_DAILY = 60


def _cfg(name, default):
    raw = ""
    try:                                   # Streamlit Secrets 优先（云端部署时用）
        import streamlit as st
        raw = st.secrets.get(name, "")
    except Exception:
        raw = ""
    raw = str(raw or os.environ.get(name, "")).strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def per_ip_limit() -> int:
    return _cfg("TWIN_PER_IP_LIMIT", DEFAULT_PER_IP)


def daily_limit() -> int:
    return _cfg("TWIN_DAILY_LIMIT", DEFAULT_DAILY)


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def _load() -> dict:
    try:
        with open(QUOTA_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data: dict):
    try:
        QUOTA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(QUOTA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def visitor_ip(headers=None) -> str:
    """取访问者标识。Streamlit Cloud 会把真实 IP 放在 X-Forwarded-For 里。

    拿不到就退化成 "unknown"——**退化时仍然受限**（等同于全体共享一份额度），
    宁可整体保守，也不能因为取不到 IP 就放开。
    """
    try:
        if headers is None:
            import streamlit as st
            headers = dict(st.context.headers)
        xff = headers.get("X-Forwarded-For") or headers.get("x-forwarded-for") or ""
        if xff:
            return xff.split(",")[0].strip()
    except Exception:
        pass
    return "unknown"


def check(ip: str, per_ip: int = None, daily: int = None):
    """判断是否允许这次提问，并**在允许时立即计数**（调用前计数，避免并发超发）。

    返回 (是否允许, 拒绝原因, 该访问者剩余次数)。
    """
    per_ip = per_ip_limit() if per_ip is None else per_ip
    daily = daily_limit() if daily is None else daily
    today = _today()
    data = _load()
    ips = data.get("ips") or {}
    days = data.get("days") or {}
    # 换天就清空历史，文件不会无限增长
    if data.get("date") != today:
        ips, days = {}, {}
    used_ip = int(ips.get(ip, 0))
    used_day = int(days.get(today, 0))

    if per_ip > 0 and used_ip >= per_ip:
        return False, "这个公开问答每个访问者每天最多 %d 个问题" % per_ip, 0
    if daily > 0 and used_day >= daily:
        return False, "今天公开问答的额度已经用完了", 0

    ips[ip] = used_ip + 1
    days[today] = used_day + 1
    _save({"date": today, "ips": ips, "days": days})
    left = per_ip - (used_ip + 1) if per_ip > 0 else -1
    return True, "", left
