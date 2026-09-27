# -*- coding: utf-8 -*-
"""用无头浏览器打开本地应用，检查页面是否渲染正常、有没有报错。"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import browser_fetch as bf  # noqa: E402
from job_sources import html_to_text  # noqa: E402


def check(url: str, label: str):
    html = bf.fetch_html(url, wait=8)
    text = html_to_text(html)
    print(f"--- {label} ---")
    print(f"  HTML {len(html)} 字节 | 文本 {len(text)} 字符")
    bad = []
    for kw in ["Traceback", "KeyError", "AttributeError", "NameError",
               "TypeError", "ValueError", "ModuleNotFound"]:
        if kw in text:
            bad.append(kw)
    print("  报错关键词：", bad if bad else "无")
    # 看看关键标题在不在
    for kw in ["今日行动", "导航", "OfferAgent", "待投"]:
        print(f"  含「{kw}」：{kw in text}")
    return not bad


if __name__ == "__main__":
    ok = check("http://localhost:8501", "首页渲染检查")
    print("\n结论：", "✅ 渲染正常" if ok else "❌ 页面里有报错，需要修")
