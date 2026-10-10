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
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import requests  # noqa: E402

import browser_fetch as bf  # noqa: E402

# 测试**单独起一个 Edge**：app 抓取用的是 bf 那个调试端口(9333/它自己的 profile)，
# 如果测试也挤在里面，app 抓 BOSS 时新开的标签页会把测试标签页挤到后台 →
# Chromium 限流后台标签 → Streamlit 前端重连时触发重跑，**正在跑的搜岗会被打断**
# （实测：后端日志"搜岗结束：42.6s，合并 132 条"，页面上却永远不显示结果）。
# 真实使用不会这样：用户自己那个浏览器 ≠ 我们抓取用的这个调试浏览器。
TEST_PORT = 9444

Q = chr(39)          # 单引号：JS 里用，避开 shell/双引号
ERR_KWS = ("Traceback", "AttributeError", "cannot be modified after the widget",
           "StreamlitAPIException", "KeyError", "TypeError", "NameError")


def launch_test_browser() -> bool:
    """起一个只给测试用的 Edge（独立 profile + 独立调试端口），等它可连。"""
    profile = Path(tempfile.gettempdir()) / "oa_click_test_profile"
    subprocess.Popen([bf.edge_path(),
                      f"--remote-debugging-port={TEST_PORT}",
                      f"--user-data-dir={profile}",
                      "--headless=new", "--no-first-run", "--no-default-browser-check",
                      "about:blank"])
    for _ in range(24):
        time.sleep(0.5)
        try:
            if requests.get(f"http://127.0.0.1:{TEST_PORT}/json/version",
                            timeout=3).status_code == 200:
                return True
        except Exception:
            continue
    return False


def new_tab(url: str) -> str:
    r = requests.put(f"http://127.0.0.1:{TEST_PORT}/json/new?{url}", timeout=10)
    if r.status_code != 200:
        r = requests.get(f"http://127.0.0.1:{TEST_PORT}/json/new?{url}", timeout=10)
    return r.json()["webSocketDebuggerUrl"]


def close_test_browser():
    """跑完把自己起的测试浏览器关掉，别在用户机器上留一个后台进程。"""
    try:
        v = requests.get(f"http://127.0.0.1:{TEST_PORT}/json/version", timeout=5).json()
        c = bf._CDP(v["webSocketDebuggerUrl"])
        try:
            c.call("Browser.close", timeout=10)
        finally:
            c.close()
    except Exception:
        pass


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


def open_select_js(label: str) -> str:
    """点开一个 aria-label 为 label 的下拉（Streamlit multiselect）。"""
    return ("(function(){var ins=Array.prototype.slice.call(document.querySelectorAll("
            + Q + "input" + Q + "));"
            + "var i=ins.filter(function(x){return (x.getAttribute(" + Q + "aria-label" + Q
            + ")||" + Q + Q + ").indexOf(" + Q + label + Q + ")>=0})[0];"
            + "if(!i){return " + Q + "no-input" + Q + "}"
            + "i.click();i.focus();return " + Q + "opened" + Q + "})()")


def pick_option_js(text: str) -> str:
    """在下拉里点一项 innerText 含 text 的选项。"""
    return ("(function(){var os=Array.prototype.slice.call(document.querySelectorAll("
            + Q + "[role=option]" + Q + "));"
            + "var o=os.filter(function(x){return x.innerText.indexOf(" + Q + text + Q + ")>=0})[0];"
            + "if(!o){return " + Q + "no-option:" + Q
            + "+os.map(function(x){return x.innerText}).join(" + Q + "," + Q + ").slice(0,200)}"
            + "o.click();return " + Q + "clicked" + Q + "})()")


def main():
    checks = []
    if not launch_test_browser():
        raise SystemExit("测试专用 Edge 启动失败（本机测试需要 Edge）")
    ws = new_tab("http://localhost:8501/jobs")
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
    # 可选：把 BOSS直聘 也加进来源（需要本机登录过 BOSS）。
    # 用 OA_TEST_BOSS=1 打开，默认不加，免得每次跑都要动浏览器 + 花十几秒。
    with_boss = os.environ.get("OA_TEST_BOSS") == "1"
    if with_boss:
        opened = js(open_select_js("来源"))
        time.sleep(2)
        picked = js(pick_option_js("BOSS直聘"))
        checks.append(("把「BOSS直聘」加进来源（%s）" % picked, picked == "clicked"))
        js("document.body.click()")          # 关掉下拉
        time.sleep(2)
    js(label_js("用缓存"))          # 关掉缓存开关，让这次点击真的走联网
    time.sleep(3)

    clicked = js(click_js("开始搜岗"))
    checks.append(("点了「开始搜岗」（返回 %s）" % clicked, clicked == "clicked"))
    text, waited = "", 0
    budget = 150 if with_boss else 90   # 勾了 BOSS 要起浏览器 + 翻页，给更长时间
    while waited < budget:          # 真实搜岗会随网络波动
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
    close_test_browser()
    return 0 if ok_n == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
