# -*- coding: utf-8 -*-
"""抓某个页面的报错原文。"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import browser_fetch as bf  # noqa: E402
from job_sources import html_to_text  # noqa: E402


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "岗位"
    if not bf.launch(headless=True):
        raise SystemExit("edge fail")
    ws = bf._new_tab("http://localhost:8501")
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    time.sleep(11)
    click = ("(function(){var ls=[].slice.call(document.querySelectorAll('label'));"
             f"var el=ls.filter(function(e){{return e.innerText.trim().indexOf('{label}')>=0;}})"
             ".filter(function(e){return e.innerText.trim().length<8;})[0];"
             "if(!el) return 'not-found'; el.click(); return 'clicked';})()")
    cdp.call("Runtime.evaluate", {"expression": click, "returnByValue": True}, timeout=40)
    time.sleep(8)
    html = cdp.call("Runtime.evaluate", {
        "expression": "document.documentElement.outerHTML",
        "returnByValue": True}, timeout=40).get("result", {}).get("value") or ""
    text = html_to_text(html)
    i = text.find("Traceback")
    print(text[max(0, i - 200): i + 1500] if i >= 0 else "没找到 Traceback")
    cdp.close()


if __name__ == "__main__":
    main()
