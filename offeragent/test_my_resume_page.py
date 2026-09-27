# -*- coding: utf-8 -*-
"""「我的简历」页验收：照片上传在这里、模板选择在这里、设置页不再放照片。

跑法：python offeragent\test_my_resume_page.py（需要 localhost:8501 已在跑）
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
    time.sleep(12)

    def text_now():
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

    click_nav("我的资料")
    mine = text_now()
    click_nav("设置")
    settings = text_now()
    cdp.close()

    checks = [
        ("我的简历页有照片区块", "简历照片" in mine),
        ("我的简历页有上传入口", "上传照片" in mine),
        ("我的简历页有模板选择", "简历模板" in mine),
        ("三个模板都出现",
         all(k in mine for k in ["经典单栏", "左侧栏", "极简黑白"])),
        ("有下载 HTML 按钮", "下载这份 HTML" in mine),
        ("提示了命令行出 PDF", "make_resume_pdf.py" in mine),
        ("我的简历页无 Traceback", "Traceback" not in mine),
        ("设置页不再有照片上传", "上传照片" not in settings),
        ("设置页保留分享链接", "分享链接" in settings or "twin=1" in settings),
    ]
    ok = 0
    for cname, good in checks:
        print(("✅ " if good else "❌ ") + cname)
        ok += 1 if good else 0
    print(f"\n{ok}/{len(checks)} 通过")


if __name__ == "__main__":
    main()
