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

PLAN = {
    "今天": ["今日行动", "数据与日志"],
    "找工作": ["岗位库", "匹配分析", "简历", "投递台", "投递记录"],
    "🧬 我的": ["自我蒸馏", "面试拷问", "分身陪练", "复盘入库"],
    "展示": [],
    "设置": [],
}
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

    def click(kind, label):
        sel = "label" if kind == "label" else "button"
        js = (f"(function(){{var ls=[].slice.call(document.querySelectorAll('{sel}'));"
              f"var el=ls.filter(function(e){{return e.innerText.trim().indexOf('{label}')>=0;}})"
              ".filter(function(e){return e.innerText.trim().length<16;})[0];"
              "if(!el) return 'not-found'; el.click(); return 'clicked';})()")
        r = cdp.call("Runtime.evaluate", {"expression": js, "returnByValue": True},
                     timeout=40).get("result", {}).get("value")
        time.sleep(6)
        return r

    bad = []
    for group, subs in PLAN.items():
        click("label", group)
        targets = subs or ["（一级页）"]
        for sub in targets:
            if subs:
                click("button", sub)
            t = text_now()
            hits = [k for k in ERR_KWS if k in t]
            flag = "❌" if hits else "✅"
            print(f"{flag} {group} → {sub:<10} 报错={hits if hits else '无'} | {len(t)} 字")
            if hits:
                bad.append((group, sub, hits))
    cdp.close()
    print()
    if bad:
        print(f"❌ {len(bad)} 个子页有报错：")
        for g, s, h in bad:
            print("   ", g, "→", s, h)
    else:
        print("✅ 所有子页都没有报错")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
