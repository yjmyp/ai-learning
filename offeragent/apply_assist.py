# -*- coding: utf-8 -*-
"""
apply_assist · 投递辅助
=======================
两种模式，由用户自己选：

  手动模式：只把话术给你，你自己复制、自己发送（零风险）
  半自动模式：程序帮你打开岗位页 + 把话术写进系统剪贴板，你粘贴后自己按发送

**不做全自动投递。** 发送前那一眼和那一下，永远由人来做。
所有投递记录写进 data/applications.jsonl，一行一条。
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
LOG_PATH = DATA_DIR / "applications.jsonl"


# 这些查询参数只是来源追踪，不参与岗位身份判断
_TRACKING_KEYS = {
    "from", "source", "spm", "track", "traceid", "share_token",
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
}
_TITLE_SUFFIXES = ("实习生", "实习", "可转正", "校招", "应届", "急招", "长期", "岗位")
_COMPANY_SUFFIXES = ("股份有限公司", "有限责任公司", "有限公司", "集团")


def _norm_text(value: str) -> str:
    """去掉空白、大小写和标点，只保留可比较的文字。"""
    text = re.sub(r"\s+", "", (value or "").strip().lower())
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", text)


def _norm_title(value: str) -> str:
    """岗位名归一化：去掉括号补充语和常见招聘后缀。"""
    text = re.sub(r"[（(【\[].*?[）)】\]]", "", (value or "").strip())
    text = _norm_text(text)
    changed = True
    while changed:
        changed = False
        for suffix in _TITLE_SUFFIXES:
            if text.endswith(suffix) and len(text) > len(suffix):
                text = text[:-len(suffix)]
                changed = True
                break
    return text


def _norm_company(value: str) -> str:
    """公司名归一化：去掉常见的法律实体后缀。"""
    text = _norm_text(value)
    for suffix in _COMPANY_SUFFIXES:
        if text.endswith(suffix) and len(text) > len(suffix):
            text = text[:-len(suffix)]
            break
    return text


def canonical_url(url: str) -> str:
    """去掉 URL 里的 fragment 和常见追踪参数，保留岗位定位部分。"""
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
        if not parts.scheme or not parts.netloc:
            return _norm_text(raw)
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if k.lower() not in _TRACKING_KEYS]
        path = re.sub(r"/+", "/", parts.path).rstrip("/")
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                           path, urlencode(query), ""))
    except Exception:
        return _norm_text(raw)


def identity_keys(name: str, meta: dict) -> set:
    """一个岗位的投递指纹：URL 优先，再用公司+岗位+城市兜底。

    只靠岗位文件名防重不够：同一个岗位换个来源、标题多「实习/可转正」，
    就会变成一个新文件。这组键会在新文件入库和真正投递前再查一次历史。
    """
    meta = meta or {}
    keys = set()
    url = canonical_url(meta.get("source_url") or meta.get("url") or "")
    if url:
        keys.add("url:" + url)
    company = _norm_company(meta.get("company") or "")
    title = _norm_title(meta.get("title") or meta.get("job") or name or "")
    city = _norm_text(meta.get("city") or "")
    if company and title and city:
        keys.add(f"role:{company}|{title}|{city}")
    if name:
        keys.add("name:" + _norm_text(name))
    return keys


def find_duplicate_application(name: str, meta: dict) -> dict | None:
    """在历史投递记录里找同岗位；找到就返回那条记录，否则返回 None。"""
    target = identity_keys(name, meta)
    if not target:
        return None
    for row in load_applications():
        row_meta = {
            "company": row.get("company", ""),
            "city": row.get("city", ""),
            "source_url": row.get("url", ""),
            "title": row.get("title", ""),
        }
        row_keys = set(row.get("identity") or [])
        row_keys |= identity_keys(row.get("job", ""), row_meta)
        if target & row_keys:
            return row
    return None


def copy_to_clipboard(text: str) -> bool:
    """把文本写进系统剪贴板。成功返回 True。"""
    try:  # 方案 1：tkinter（标准库自带）
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        pass
    try:  # 方案 2：pyperclip（如果装了）
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        pass
    try:  # 方案 3：Windows 的 clip 命令（UTF-16 避免中文乱码）
        if sys.platform == "win32":
            subprocess.run("clip", input=text.encode("utf-16le"),
                           shell=True, check=True, timeout=10)
            return True
    except Exception:
        pass
    return False


def open_url(url: str) -> bool:
    """用系统默认浏览器打开链接。"""
    if not url:
        return False
    try:
        if sys.platform == "win32":
            subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
        else:
            import webbrowser
            webbrowser.open(url)
        return True
    except Exception:
        return False


def log_application(name: str, meta: dict, talk: str = "", note: str = ""):
    """记录一次投递。一行一条 JSON，方便统计和复盘。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "date": time.strftime("%Y-%m-%d"),
        "job": name,
        "title": meta.get("title", ""),
        "company": meta.get("company", ""),
        "city": meta.get("city", ""),
        "score": meta.get("match_score"),
        "url": meta.get("source_url", ""),
        "talk": talk,
        "note": note,
        "identity": sorted(identity_keys(name, meta)),
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def load_applications() -> list:
    """读回全部投递记录（新到旧）。"""
    if not LOG_PATH.exists():
        return []
    rows = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return list(reversed(rows))


def applied_today() -> int:
    today = time.strftime("%Y-%m-%d")
    return sum(1 for r in load_applications() if r.get("date") == today)
