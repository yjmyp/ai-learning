# -*- coding: utf-8 -*-
"""
逐页巡检：把 10 个导航页都点一遍，检查有没有报错，并给每页存一张截图。

跑法：python offeragent\test_app_pages.py
输出：offeragent/data/shots/page_*.png

为什么长这样（2026-10-10 修）：
  原来写死 `sleep(6)` 就截图，遇到大页面（/apply 21 条岗位、/records 一堆记录）
  时截图调用会卡到 CDP 超时抛异常 → **整轮巡检从那一页起直接中断**，
  后面几页（记录/蒸馏/面试/名片/设置）其实从来没被检查过，看起来却是"绿"的。
  三次运行实测：第 5~6 页必崩。
  现在：① 等"渲染稳定"（连续两次文本一致且至少 10 秒）再动手，同 test_nav_structure.py；
       ② 每页单独开一个标签页，一页出问题不影响别页，也不污染连接；
       ③ 截图先试整页、失败退整屏、再失败只记一笔，不让巡检中断；
       ④ 汇总里把"哪几页没截到图"单独列出来，别再假装全绿。
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
APP = "http://localhost:8501"
# 原生多页导航：每页有真实 URL，直接按 URL 巡
PLAN = [("today", "/"), ("jobs", "/jobs"), ("match", "/match"),
        ("resume", "/resume"), ("apply", "/apply"), ("records", "/records"),
        ("distill", "/distill"), ("interview", "/interview"),
        ("show", "/show"), ("settings", "/settings")]
ERR_KWS = ["Traceback", "StreamlitDuplicateElementId", "KeyError",
           "AttributeError", "NameError", "TypeError", "ValueError",
           "ModuleNotFoundError", "st.error"]


def wait_stable(cdp, min_seconds: float = 10, max_seconds: float = 45):
    """轮询到页面渲染稳定为止（连续两次取到的文本完全一致），返回 (文本, HTML)。

    为什么不写死 sleep：Streamlit 首次编译某个页面偶尔超过 6 秒，取到的是半页 →
    同一项检查"这轮过、下轮不过"的假失败（test_nav_structure.py 踩过同一个坑）。
    """
    prev = None
    started = time.time()
    txt, html = "", ""
    while time.time() - started < max_seconds:
        time.sleep(2.5)
        html = cdp.call("Runtime.evaluate", {
            "expression": "document.documentElement.outerHTML",
            "returnByValue": True}, timeout=60).get("result", {}).get("value") or ""
        txt = html_to_text(html)
        if prev == txt and len(txt) > 300 and time.time() - started >= min_seconds:
            break
        prev = txt
    return txt, html


def grab_shot(cdp, path: Path) -> str:
    """截图：先试整页，失败退整屏，再失败返回原因（不让巡检中断）。"""
    last = "未知"
    for beyond, note in ((True, ""), (False, "整页截图失败，已退成整屏")):
        try:
            res = cdp.call("Page.captureScreenshot",
                           {"format": "png", "captureBeyondViewport": beyond},
                           timeout=30)
            data = res.get("data", "")
            if not data:
                continue
            path.write_bytes(base64.b64decode(data))
            return note
        except Exception as e:                       # 超时/连接坏掉都算
            last = type(e).__name__
    return f"截图失败（{last}）"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not bf.launch(headless=True):
        raise SystemExit("Edge 启动失败")

    results = []
    for i, (label, path) in enumerate(PLAN):
        shot_file = OUT_DIR / f"page_{i + 1}_{label}.png"
        t0 = time.perf_counter()
        ws = bf._new_tab(APP + path)          # 每页独立标签页：一页坏了不影响别页
        cdp = bf._CDP(ws)
        bad, note, txt_len = [], "", 0
        try:
            cdp.call("Page.enable")
            cdp.call("Emulation.setDeviceMetricsOverride", {
                "width": 1500, "height": 1000, "deviceScaleFactor": 1, "mobile": False})
            txt, _html = wait_stable(cdp)
            txt_len = len(txt)
            bad = [k for k in ERR_KWS if k in txt]
            note = grab_shot(cdp, shot_file)
        except Exception as e:                # 单页异常也只记一笔，继续下一页
            bad = bad or [f"巡检异常：{type(e).__name__}"]
            note = note or "未截图"
        finally:
            cdp.close()
            bf._close_tab(ws)
        results.append((label, path, bad, txt_len, shot_file.name, note))
        print(f"{label:<9} {path:<10} 报错={bad if bad else '无'}"
              f" | 文本 {txt_len} 字 | {shot_file.name}"
              + (f" | 注意：{note}" if note else "")
              + f" | {time.perf_counter() - t0:.1f}s")

    print(f"\n截图目录：{OUT_DIR}")
    bad_total = [r for r in results if r[2]]
    no_shot = [r for r in results if r[5]]
    if no_shot:
        print("以下页面截图有问题（只影响看不出图，不影响有没有报错的结论）：")
        for label, _p, _b, _n, name, note in no_shot:
            print(f"  - {label}：{note}（{name}）")
    if len(results) != len(PLAN):
        print(f"❌ 只巡检了 {len(results)}/{len(PLAN)} 个页面（不该发生）")
        return 1
    print("结论：", f"✅ {len(PLAN)} 个页面都巡检完了，都没有报错"
          if not bad_total else f"❌ 有 {len(bad_total)} 个页面报错")
    return 1 if bad_total else 0


if __name__ == "__main__":
    sys.exit(main())
