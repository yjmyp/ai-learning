# -*- coding: utf-8 -*-
"""
逐页巡检：把 5 个导航页都点一遍，检查有没有报错，并给每页存一张截图。

跑法：python offeragent\test_app_pages.py
输出：offeragent/data/shots/page_*.png
"""
import base64
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
# Windows 控制台默认 GBK，直接 print emoji 会 UnicodeEncodeError，这里强制 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import browser_fetch as bf  # noqa: E402
from job_sources import html_to_text  # noqa: E402

OUT_DIR = HERE / "data" / "shots"
NAV = ["今天", "找工作", "🧬 我的", "展示", "设置"]
ERR_KWS = ["Traceback", "StreamlitDuplicateElementId", "KeyError",
           "AttributeError", "NameError", "TypeError", "ValueError",
           "ModuleNotFoundError", "st.error"]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not bf.launch(headless=True):
        raise SystemExit("Edge 启动失败")
    ws = bf._new_tab("http://localhost:8501")
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    cdp.call("Emulation.setDeviceMetricsOverride", {
        "width": 1500, "height": 1000, "deviceScaleFactor": 1, "mobile": False})
    time.sleep(10)  # 等首屏加载

    def evaljs(expr):
        r = cdp.call("Runtime.evaluate",
                     {"expression": expr, "returnByValue": True}, timeout=60)
        return r.get("result", {}).get("value")

    results = []
    for i, label in enumerate(NAV):
        click = (
            "(() => {const ls=[...document.querySelectorAll('label')];"
            f"const el=ls.find(e=>e.innerText.trim().includes('{label}'));"
            "if(!el) return 'not-found'; el.click(); return 'clicked';})()"
        )
        clicked = evaljs(click)
        time.sleep(7)
        text = html_to_text(evaljs("document.documentElement.outerHTML") or "")
        bad = [k for k in ERR_KWS if k in text]
        shot = OUT_DIR / f"page_{i + 1}_{label}.png"
        res = cdp.call("Page.captureScreenshot",
                       {"format": "png", "captureBeyondViewport": True}, timeout=60)
        shot.write_bytes(base64.b64decode(res.get("data", "")))
        results.append((label, clicked, bad, len(text), shot.name))
        print(f"{label:<8} 点击={clicked:<10} 报错={bad if bad else '无'}"
              f" | 文本 {len(text)} 字 | {shot.name}")

    cdp.close()
    print(f"\n截图目录：{OUT_DIR}")
    bad_total = [r for r in results if r[2]]
    print("结论：", "✅ 5 个页面都没有报错" if not bad_total
          else f"❌ 有 {len(bad_total)} 个页面报错")


if __name__ == "__main__":
    main()
