# -*- coding: utf-8 -*-
"""
store.py —— OfferAgent 数据层（2026-09-29 从 offer_agent_app.py 抽出）
============================================================================
纯 Python 逻辑，不依赖 streamlit，可独立测试：
  岗位库读写（meta 权威源）、简历读写、日志读取、分数对账（单一权威源）、投递防抖。
"""
import json
import os
import re
import time
from pathlib import Path

import resume_clean

try:
    from jd_fetcher import fetch_jd
    FETCHER_OK = True
except Exception:
    FETCHER_OK = False

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
REPORTS_DIR = DATA_DIR / "reports"


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
        return resume_clean.clean(read_text(MY_RESUME_PATH))[0]
    for cand in [BASE_DIR.parent / "简历" / "余剑-简历-AI应用开发实习.md",
                 BASE_DIR.parent / "简历" / "余剑-简历-AI应用开发实习-v2.md"]:
        if cand.exists():
            return resume_clean.clean(read_text(cand))[0]
    return ""


def save_my_resume(text: str) -> tuple:
    """保存「我的简历」。顺手清掉本地路径乱码，返回 (干净文本, 清洗报告)。"""
    cleaned, report = resume_clean.clean((text or "").strip())
    MY_RESUME_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_text(MY_RESUME_PATH, cleaned + "\n")
    return cleaned, report


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


def detect_network_exclude(jd_text: str):
    """检测 JD 是否「专门点名要求网络工程专业」。返回 (原因, 命中原文)。"""
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
# 日志与单一权威源（2026-09-29 新增）
# ============================================================
def read_logs() -> list:
    """读 Agent 运行日志（事件流，append-only）。"""
    p = DATA_DIR / "agent_logs.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").strip().splitlines():
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out


def audit_scores() -> list:
    """单一权威源对账：meta（权威）vs 日志（历史事件）。
    返回 [(公司, meta分数, 日志最新分数, 一致?, 说明)]。
    规则：岗位库 meta.match_score 是唯一权威；日志只记事件，历史分数是快照，不覆盖岗位库。
    """
    logs = read_logs()
    latest = {}
    for l in logs:
        comp = l.get("company") or l.get("job")
        if comp and l.get("match_score") is not None:
            latest[comp] = l["match_score"]      # 文件有序，最后一条 = 最新事件
    rows = []
    for name, meta, _jd in list_jobs():
        comp = meta.get("company") or name
        m = meta.get("match_score")
        lg = latest.get(comp) or latest.get(name)
        if m is None and lg is None:
            rows.append((comp, None, None, True, "未匹配（两者皆无）"))
        elif m is None:
            rows.append((comp, None, lg, False, "日志有事件分但岗位库未回填——以岗位库为准，重跑批量匹配可修复"))
        elif lg is None:
            rows.append((comp, m, None, True, "岗位库有分，日志无事件（正常，日志只记事件）"))
        elif m == lg:
            rows.append((comp, m, lg, True, "一致"))
        else:
            rows.append((comp, m, lg, False, "不一致：岗位库为权威（重跑匹配更新），日志为历史快照"))
    return rows


# ============================================================
# 投递防抖（2026-09-29 新增：P3-⑪ 批量连发保护）
# ============================================================
def check_apply_allowed(name: str, meta: dict) -> dict:
    """投递防抖：已投 / 24 小时内投过 → 拦截。返回 {"allowed": bool, "reason": str}。"""
    if meta.get("status") == "已投":
        return {"allowed": False, "reason": f"{name} 已标记「已投」，禁止重复投递"}
    t = meta.get("last_apply_time", "")
    if t:
        try:
            last = time.mktime(time.strptime(t[:19], "%Y-%m-%d %H:%M:%S"))
            if time.time() - last < 86400:
                return {"allowed": False,
                        "reason": f"{name} 24 小时内已发起过投递（{t}），防重复连发"}
        except Exception:
            pass
    return {"allowed": True, "reason": ""}


def mark_applied(name: str, meta: dict) -> dict:
    """标记已投：写 status + last_apply_time（防抖依据）。"""
    meta["status"] = "已投"
    meta["applied_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    meta["last_apply_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_meta(name, meta)
    return meta
