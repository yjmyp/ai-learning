# -*- coding: utf-8 -*-
"""全量巡检：把每一个一级分区的**每一个二级子页**都点一遍。

为什么需要：线上白屏那次，浏览器脚本只点了一级导航（默认子页），
「投递记录」这个子页里的 NameError 就没被发现。这个脚本按子页巡。

跑法：python offeragent\test_all_pages_sweep.py（需要 localhost:8501 已在跑）
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

# 原生多页导航后每页都有真实 URL，直接按 URL 巡，比点元素稳
PLAN = [
    ("今天（行动 + 数据）", "/"),
    ("岗位库", "/jobs"),
    ("匹配分析", "/match"),
    ("简历（模板/照片/覆盖）", "/resume"),
    ("投递台", "/apply"),
    ("投递记录", "/records"),
    ("自我蒸馏", "/distill"),
    ("面试准备（拷问/陪练/复盘）", "/interview"),
    ("名片与分享", "/show"),
    ("设置", "/settings"),
]
ERR_KWS = ["Traceback", "NameError", "KeyError", "AttributeError", "TypeError",
           "ValueError", "ModuleNotFoundError", "StreamlitDuplicateElementId",
           "UnboundLocalError", "IndexError"]


def main():
    if not bf.launch(headless=True):
        raise SystemExit("Edge 启动失败")
    ws = bf._new_tab("http://localhost:8501")
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    time.sleep(12)

    def text_now():
        html = cdp.call("Runtime.evaluate", {
            "expression": "document.documentElement.outerHTML",
            "returnByValue": True}, timeout=60).get("result", {}).get("value") or ""
        return html_to_text(html)

    def go(path):
        cdp.call("Page.navigate", {"url": "http://localhost:8501" + path}, timeout=60)
        time.sleep(6)

    bad = []
    for name, path in PLAN:
        go(path)
        t = text_now()
        hits = [k for k in ERR_KWS if k in t]
        flag = "❌" if hits else "✅"
        print(f"{flag} {name:<18} {path:<10} 报错={hits if hits else '无'} | {len(t)} 字")
        if hits:
            bad.append((name, path, hits))
    cdp.close()
    print()
    if bad:
        print(f"❌ {len(bad)} 个页面有报错：")
        for name, path, h in bad:
            print("   ", name, path, h)
    else:
        print("✅ 所有页面都没有报错")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
