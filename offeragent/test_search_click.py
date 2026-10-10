# -*- coding: utf-8 -*-
"""浏览器验收：真的去点「🔍 开始搜岗」，确认不崩、能出结果。

为什么要单独写这个：2026-10-10 出过一次事故——`src_cities` 这个 key 既当城市多选框的
控件 key、又当"各来源城市分布"的结果 key，一点「开始搜岗」就整页报错
（"cannot be modified after the widget ... is instantiated" → 下一轮
AttributeError: 'list' object has no attribute 'items'）。**页面巡检只看渲染，看不到**，
只有真的点那个按钮才会暴露。所以这里把"点一次搜岗"固化成验收步骤。

前提：本地 app 跑在 http://localhost:8501（本机 Edge 可用）。
跑法：python offeragent/test_search_click.py
会被 run_tests.py 默认跳过（需 --browser），因为它要起浏览器 + 真联网。
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import browser_fetch as bf  # noqa: E402

Q = chr(39)          # 单引号：JS 里用，避开 shell/双引号
ERR_KWS = ("Traceback", "AttributeError", "cannot be modified after the widget",
           "StreamlitAPIException", "KeyError", "TypeError", "NameError")


def click_js(text: str) -> str:
    """点一个 innerText 含 text 的 <button>。"""
    return ("(function(){var bs=Array.prototype.slice.call(document.querySelectorAll("
            + Q + "button" + Q + "));"
            + "var b=bs.filter(function(x){return x.innerText.indexOf(" + Q + text + Q + ")>=0})[0];"
            + "if(b){b.click();return " + Q + "clicked" + Q + "}"
            + "return " + Q + "notfound:" + Q + "+bs.map(function(x){return x.innerText})"
            + ".join(" + Q + "|" + Q + ").slice(0,300)})()")


def label_js(text: str) -> str:
    """点一个 innerText 含 text 的 <label>（用来关掉「用缓存」开关）。"""
    return ("(function(){var ls=Array.prototype.slice.call(document.querySelectorAll("
            + Q + "label" + Q + "));"
            + "var l=ls.filter(function(x){return x.innerText.indexOf(" + Q + text + Q + ")>=0})[0];"
            + "if(l){l.click();return " + Q + "clicked" + Q + "}"
            + "return " + Q + "notfound" + Q + "})()")


def main():
    checks = []
    if not bf.launch(headless=True):
        raise SystemExit("Edge 启动失败（本机测试需要 Edge）")
    ws = bf._new_tab("http://localhost:8501/jobs")
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    cdp.call("Emulation.setDeviceMetricsOverride",
             {"width": 1500, "height": 1400, "deviceScaleFactor": 1, "mobile": False})
    time.sleep(12)          # 等 Streamlit 首屏

    def js(expr, timeout=120):
        r = cdp.call("Runtime.evaluate",
                     {"expression": expr, "returnByValue": True}, timeout=timeout)
        return r.get("result", {}).get("value")

    checks.append(("搜岗页打开了（「开始搜岗」按钮在）",
                   "开始搜岗" in (js("document.body.innerText") or "")))

    cleared = js(click_js("清空搜索缓存"))
    checks.append(("点了「清空搜索缓存」（返回 %s）" % cleared, cleared == "clicked"))
    time.sleep(6)
    js(label_js("用缓存"))          # 关掉缓存开关，让这次点击真的走联网
    time.sleep(3)

    clicked = js(click_js("开始搜岗"))
    checks.append(("点了「开始搜岗」（返回 %s）" % clicked, clicked == "clicked"))
    text, waited = "", 0
    while waited < 90:              # 真实搜岗会随网络波动，最多等 90 秒
        time.sleep(6)
        waited += 6
        text = js("document.body.innerText") or ""
        if "合并后共" in text or any(k in text for k in ERR_KWS):
            break
    errs = [k for k in ERR_KWS if k in text]
    checks.append(("页面上没有报错关键词%s" % ("" if not errs else "：%s" % errs), not errs))
    checks.append(("搜岗真的跑完了（出现「合并后共 N 条」，等了 %ds）" % waited,
                   "合并后共" in text))
    checks.append(("显示「本次耗时」（说明结果确实写进了 session_state）", "本次耗时" in text))

    ok_n = sum(1 for _, v in checks if v)
    for name, good in checks:
        print(("✅ " if good else "❌ ") + name)
    print("\n%d/%d 通过" % (ok_n, len(checks)))
    if ok_n != len(checks):
        print("\n--- 页面文本尾部（排查用） ---")
        print((text or "")[-1500:])
    return 0 if ok_n == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
