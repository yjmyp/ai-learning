# -*- coding: utf-8 -*-
"""rag2/quota.py —— 公开服务的每日调用配额（防陌生人刷 API 成本）。

策略：服务入口（app.py / api.py）在调 ask_deepseek 前先 check()，
超限直接拒绝；离线脚本 / 本地开发设环境变量 RAG_DAILY_LIMIT=0 关闭。
"""
import json
import os
import pathlib
import time

USAGE_PATH = pathlib.Path(__file__).resolve().parent / "data" / "usage.json"
DEFAULT_LIMIT = 300  # 300 次/天 ≈ 0.09 元，面试官体验无感，批量刷的人会被挡


def daily_limit() -> int:
    raw = os.environ.get("RAG_DAILY_LIMIT", "")
    try:
        n = int(raw)
        return n if n >= 0 else DEFAULT_LIMIT
    except Exception:
        return DEFAULT_LIMIT


def _today() -> dict:
    today = time.strftime("%Y-%m-%d")
    try:
        u = json.loads(USAGE_PATH.read_text(encoding="utf-8"))
    except Exception:
        u = {}
    if not isinstance(u, dict) or u.get("date") != today:
        u = {"date": today, "calls": 0}
    return u


def _save(u: dict) -> None:
    try:
        USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        USAGE_PATH.write_text(json.dumps(u, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def remaining() -> tuple:
    """返回 (剩余次数, 上限)；上限 0 表示不限。"""
    lim = daily_limit()
    used = int(_today().get("calls", 0))
    if lim <= 0:
        return (-1, 0)
    return (max(lim - used, 0), lim)


def check() -> None:
    """调用前检查并计数；超限抛 RuntimeError。"""
    lim = daily_limit()
    if lim <= 0:
        return
    used = int(_today().get("calls", 0))
    if used >= lim:
        raise RuntimeError(f"今日演示额度已用完（{lim} 次/天），明天再来体验～")
    u = _today()
    u["calls"] = used + 1
    _save(u)
