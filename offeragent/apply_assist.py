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
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
LOG_PATH = DATA_DIR / "applications.jsonl"


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
        "company": meta.get("company", ""),
        "city": meta.get("city", ""),
        "score": meta.get("match_score"),
        "url": meta.get("source_url", ""),
        "talk": talk,
        "note": note,
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
