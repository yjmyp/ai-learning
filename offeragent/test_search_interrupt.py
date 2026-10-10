# -*- coding: utf-8 -*-
"""浏览器验收：**搜岗跑到一半被重跑打断，结果也不能丢**。

为什么要单独写这个（2026-10-10 实测复现的事故）：
  点「开始搜岗」→ 搜索要跑十几秒（全是等网络）→ 这期间页面上任何一次重跑
  （动别的控件 / 前端重连 / 手机切后台）都会中断"正在跑的那次运行"。
  旧运行算出来的结果只写进了当次的 st.session_state → 新运行读到空 →
  页面既不出结果也不报错，等满 120 秒还是空的，用户看到的就是"点了没反应"。

修完之后这里要成立：搜索结束后结果落在 data/last_search.json；
页面重跑 / 刷新后从快照读回来，能看见「合并后共 N 条」。

前提：本地 app 跑在 http://localhost:8501（本机 Edge 可用）。
跑法：python offeragent/test_search_interrupt.py
会被 run_tests.py 默认跳过（需 --browser），因为它要起浏览器 + 真联网。
"""
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
import job_sources as jobsrc  # noqa: E402   # 注意：别叫 js，main() 里的 js() 是 CDP 求值

# 单独起一个 Edge（独立 profile + 独立端口）：别和 app 抓取用的调试浏览器挤在一起，
# 否则新开的抓取标签页会把测试标签页挤到后台，Chromium 限流后台标签 →
# Streamlit 前端重连触发重跑，测试就变成"自己打断自己"（test_search_click.py 踩过）。
TEST_PORT = 9448
APP = "http://localhost:8501/jobs"
Q = chr(39)
ERR_KWS = ("Traceback", "AttributeError", "cannot be modified after the widget",
           "StreamlitAPIException", "KeyError", "TypeError", "NameError")


def launch_test_browser() -> bool:
    profile = Path(tempfile.gettempdir()) / "oa_interrupt_test_profile"
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
            + "return " + Q + "notfound" + Q + "})()")


def label_js(text: str) -> str:
    """点一个 innerText 含 text 的 <label>（用来拨「用缓存」开关）。"""
    return ("(function(){var ls=Array.prototype.slice.call(document.querySelectorAll("
            + Q + "label" + Q + "));"
            + "var l=ls.filter(function(x){return x.innerText.indexOf(" + Q + text + Q + ")>=0})[0];"
            + "if(l){l.click();return " + Q + "clicked" + Q + "}"
            + "return " + Q + "notfound" + Q + "})()")


def main():
    checks = []
    if not launch_test_browser():
        raise SystemExit("测试专用 Edge 启动失败")
    ws = new_tab(APP)
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    cdp.call("Emulation.setDeviceMetricsOverride",
             {"width": 1500, "height": 1400, "deviceScaleFactor": 1, "mobile": False})
    time.sleep(12)          # 等 Streamlit 首屏

    def js(expr, timeout=120):
        r = cdp.call("Runtime.evaluate",
                     {"expression": expr, "returnByValue": True}, timeout=timeout)
        return r.get("result", {}).get("value")

    checks.append(("搜岗页打开了", "开始搜岗" in (js("document.body.innerText") or "")))
    js(label_js("用缓存"))            # 关缓存：保证这次真的联网、搜索足够久
    time.sleep(3)
    before = jobsrc.load_last_search()  # 先记下"上一次"的快照，后面要确认它被刷新了
    t_click = time.time()
    clicked = js(click_js("开始搜岗"))
    checks.append(("点了「开始搜岗」（%s）" % clicked, clicked == "clicked"))
    time.sleep(2)
    # 搜索还在飞的时候动一下控件 → 触发重跑，模拟"用户 / 前端把这次运行打断"
    interrupted = js(label_js("用缓存"))
    checks.append(("搜索期间触发了页面重跑（%s）" % interrupted, interrupted == "clicked"))

    # 等后台把这次搜索跑完并把快照写下来（直接轮询磁盘，不经浏览器）
    snap, waited = {}, 0
    while waited < 150:
        time.sleep(5)
        waited += 5
        snap = jobsrc.load_last_search()
        if snap.get("jobs") and (snap.get("t") or 0) >= t_click:
            break
    n = len(snap.get("jobs") or [])
    fresh = (snap.get("t") or 0) >= t_click
    checks.append(("搜索跑完并落了快照（%d 条，等了 %ds）" % (n, waited), n > 0 and fresh))
    if before.get("t"):
        checks.append(("快照确实是这一轮新写的（不是上一轮残留）",
                       (snap.get("t") or 0) > (before.get("t") or 0)))

    # 重新打开 /jobs：这次运行没有搜过，只能靠快照兜底 —— 结果必须还在
    cdp.call("Page.navigate", {"url": APP}, timeout=60)
    text, waited2 = "", 0
    while waited2 < 45:
        time.sleep(3)
        waited2 += 3
        text = js("document.body.innerText") or ""
        if "合并后共" in text or any(k in text for k in ERR_KWS):
            break
    errs = [k for k in ERR_KWS if k in text]
    checks.append(("刷新后没有报错关键词%s" % ("" if not errs else "：" + str(errs)), not errs))
    checks.append(("刷新后结果还在（出现「合并后共 N 条」，等了 %ds）" % waited2,
                   "合并后共" in text))
    checks.append(("并说清了这是「上一次搜岗」的结果", "上一次搜岗" in text))

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
