# -*- coding: utf-8 -*-
"""流程改造验收：检查顶部流程条、一站式岗位卡片、我的资料导航是否真的渲染出来。

跑法：python offeragent\test_flow_check.py（需要 localhost:8501 已在跑）
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
    ws = bf._new_tab("http://localhost:8501")
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    time.sleep(11)

    def page_text():
        html = cdp.call("Runtime.evaluate", {
            "expression": "document.documentElement.outerHTML",
            "returnByValue": True}, timeout=60).get("result", {}).get("value") or ""
        return html_to_text(html)

    def click_nav(label):
        js = ("(function(){var ls=[].slice.call(document.querySelectorAll('label'));"
              f"var el=ls.filter(function(e){{return e.innerText.trim().indexOf('{label}')>=0;}})"
              ".filter(function(e){return e.innerText.trim().length<10;})[0];"
              "if(!el) return 'not-found'; el.click(); return 'clicked';})()")
        r = cdp.call("Runtime.evaluate", {"expression": js, "returnByValue": True},
                     timeout=40).get("result", {}).get("value")
        time.sleep(7)
        return r

    def click_button(text):
        js = ("(function(){var bs=[].slice.call(document.querySelectorAll('button'));"
              f"var el=bs.filter(function(e){{return e.innerText.trim().indexOf('{text}')>=0;}})[0];"
              "if(!el) return 'not-found'; el.click(); return 'clicked';})()")
        r = cdp.call("Runtime.evaluate", {"expression": js, "returnByValue": True},
                     timeout=40).get("result", {}).get("value")
        time.sleep(7)
        return r

    checks = []
    t = page_text()
    checks.append(("今日页有流程条 ①找岗", "① 找岗（入库）" in t))
    checks.append(("今日页有流程条 ④有回应", "④ 有回应" in t))
    checks.append(("今日页有今日投递目标", "今天投递" in t))

    click_nav("岗位")
    t = page_text()
    checks.append(("岗位页有一站式卡片", "一站式" in t))
    checks.append(("一站式含②ATS 简历覆盖", "ATS 简历覆盖" in t))
    checks.append(("一站式含④标记已投", "标记已投" in t))

    # 关键回归：岗位卡片的「🔍 匹配」跳转（以前这里会因直接改 nav 而崩）
    r = click_button("匹配")
    t = page_text()
    checks.append(("点匹配按钮能跳到匹配分析", r == "clicked" and "匹配分析" in t))
    checks.append(("跳转后无 Traceback/StreamlitAPIException",
                   "Traceback" not in t and "StreamlitAPIException" not in t))
    click_button("回岗位库列表")

    click_nav("我的资料")
    t = page_text()
    checks.append(("我的资料含「我的简历」", "我的简历" in t))
    checks.append(("我的资料含「自我蒸馏」", "自我蒸馏" in t))
    checks.append(("简历来源三选一", "问答式生成一份" in t))

    click_nav("投递")
    t = page_text()
    checks.append(("投递页无 Traceback", "Traceback" not in t))
    checks.append(("投递页有简历定制", "简历定制" in t))

    cdp.close()
    ok = 0
    for cname, good in checks:
        print(("✅ " if good else "❌ ") + cname)
        ok += 1 if good else 0
    print(f"\n{ok}/{len(checks)} 通过")


if __name__ == "__main__":
    main()
