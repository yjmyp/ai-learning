# -*- coding: utf-8 -*-
"""保住线上演示链接：检测休眠 → 点唤醒 → 轮询到真正可用（Streamlit Cloud 免费版必备）。

为什么需要：Streamlit Community Cloud 免费应用无访问一段时间后会休眠，访客打开看到的是
「This app has gone to sleep due to inactivity」+ 一个唤醒按钮。简历里放这种链接，
HR 点开就关——所以必须有人定期访问，把它叫醒。

用法：
    python tools/keep_alive.py                 # 检查 + 必要时唤醒（默认两个应用）
    python tools/keep_alive.py --url <URL> --marker 知识库
    python tools/keep_alive.py --dry-run       # 只看状态，不点唤醒
    python tools/keep_alive.py --wait 180      # 唤醒后最多等多久（秒）

定时保活（Windows 计划任务，每 6 小时一次，需要机器开机）：
    schtasks /create /tn "演示链接保活" /sc hourly /mo 6 ^
      /tr "python C:\\Users\\29947\\Documents\\Codex\\ai-learning\\tools\\keep_alive.py" /f
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "offeragent"))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import browser_fetch as bf  # noqa: E402

# 默认要保活的链接（marker = 应用真正渲染出来时页面里一定会出现的字）
#
# 只保活"简历里对外给出的那个链接"：
#  · 根链接（不带参数）有访问密码墙，保活了面试官也看不到内容，没意义；
#  · ?twin=1 是免密数字名片页，这才是给 HR / 面试官的入口；
#  · RAG 云端部署目前是崩的（点开是 Traceback），已从简历移除，先不保活——
#    等修好再加回来（加回来时记得把 marker 一起补上）。
APPS = [
    {"name": "OfferAgent 数字名片（免密）",
     "url": "https://ai-learning-c62pgpcfp7us6rztelatpj.streamlit.app/?twin=1",
     "markers": ["名片", "求职", "余剑"]},
]

CLICK_JS = """(function(){
  var bs=[].slice.call(document.querySelectorAll("button"));
  for(var i=0;i<bs.length;i++){
    var s=(bs[i].innerText||"").trim();
    if(/back up|wake/i.test(s)){ bs[i].click(); return "clicked:"+s; }
  }
  return "no-button";
})()"""


def page_text(url, wait=20):
    """用无头浏览器取渲染后的正文（Streamlit 的内容要等 websocket 推完才在 DOM 里）。"""
    from job_sources import html_to_text
    try:
        return html_to_text(bf.fetch_html(url, wait=wait))
    except Exception as e:
        return "__ERR__%s" % type(e).__name__


def status_of(text, markers):
    """判断状态。判据故意宽松：只要没有休眠字样就算"在服务"。

    为什么不要求必须命中应用特征字：Streamlit 页面正文是 websocket 推过来的，
    headless 抓取时经常只拿到外壳（实测同一链接两次抓取，一次有内容一次只有页脚），
    拿它当"可用"判据会误判成故障。休眠页则有稳定特征字样，不会漏判。
    """
    if text.startswith("__ERR__"):
        return "error", text
    low = text.lower()
    if "gone to sleep" in low or "wake it up" in low or "wake it back up" in low:
        return "sleeping", ""
    found = [m for m in markers if m in text]
    return "up", ",".join(found)


def keep_one(url, markers, dry_run=False, wait=240):
    st, extra = status_of(page_text(url), markers)
    print("  首次探测：%s %s" % (st, extra))
    if st == "up":
        return True, st
    if dry_run or st == "error":
        return False, st
    print("  检测到休眠，点唤醒按钮 …")
    try:
        print("     ", bf.run_js(url, CLICK_JS, wait=8))
    except Exception as e:
        print("      点击失败：", type(e).__name__)
    t0 = time.time()
    while time.time() - t0 < wait:
        time.sleep(20)
        st, extra = status_of(page_text(url), markers)
        print("     +%ds → %s %s" % (int(time.time() - t0), st, extra))
        if st == "up":
            return True, st
    return False, st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="")
    ap.add_argument("--name", default="自定义链接")
    ap.add_argument("--marker", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--wait", type=int, default=180)
    args = ap.parse_args()

    apps = APPS
    if args.url:
        apps = [{"name": args.name, "url": args.url,
                 "markers": [args.marker] if args.marker else ["a", "e", "i", "o", "u"]}]

    if not bf.launch(headless=True):
        print("❌ 浏览器启动失败：" + (bf.no_browser_message() or ""))
        return 2

    results = []
    for app in apps:
        name, url = app["name"], app["url"]
        print(f"\n=== {name} ===\n{url}")
        ok, st = keep_one(url, app["markers"], dry_run=args.dry_run, wait=args.wait)
        print("  结果：", "✅ 可用" if ok else "❌ 不可用（%s）" % st)
        results.append((name, ok, st))

    print("\n== 汇总 ==")
    bad = 0
    for name, ok, _ in results:
        print(("  ✅ " if ok else "  ❌ ") + name)
        bad += 0 if ok else 1
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
