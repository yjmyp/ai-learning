# -*- coding: utf-8 -*-
"""公开数字名片页验收（?twin=1）：照片位、分享链接、问数字人、两个信息页签。

跑法：python offeragent\test_twin_portal.py（需要 localhost:8501 已在跑）
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import browser_fetch as bf  # noqa: E402
from job_sources import html_to_text  # noqa: E402

def main():
    if not bf.launch(headless=True):
        raise SystemExit("Edge 启动失败")
    ws = bf._new_tab("http://localhost:8501/?twin=1")
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    time.sleep(15)
    html = cdp.call("Runtime.evaluate", {
        "expression": "document.documentElement.outerHTML",
        "returnByValue": True}, timeout=60).get("result", {}).get("value") or ""
    text = html_to_text(html)
    cdp.close()

    checks = [
        ("名片头有姓名", "余剑" in text),
        ("有职位定位", "AI 应用开发实习生" in text),
        ("有学校 / 届别标签", "南京邮电大学" in text and "2027" in text),
        ("照片位存在（图或占位字）", "余" in text),
        ("有分享/转载入口", ("分享" in text) or ("转载" in text)),
        ("有「问数字人」主入口", "有问题直接问他" in text),
        ("宣传语含 AI 可能有误声明", "以本人沟通为准" in text),
        ("有「我是谁」页签", "我是谁" in text),
        ("有「项目证据」页签", "项目证据" in text),
        ("提到 RAG 项目", "RAG" in text),
        ("没有 Traceback", "Traceback" not in text),
    ]
    ok = 0
    for cname, good in checks:
        print(("✅ " if good else "❌ ") + cname)
        ok += 1 if good else 0
    print(f"\n{ok}/{len(checks)} 通过")


if __name__ == "__main__":
    main()
