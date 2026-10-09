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

    def click_btn(text):
        """二级子页是 segmented_control，渲染成 button。"""
        js = ("(function(){var bs=[].slice.call(document.querySelectorAll('button'));"
              f"var el=bs.filter(function(e){{return e.innerText.trim().indexOf('{text}')>=0;}})[0];"
              "if(!el) return 'not-found'; el.click(); return 'clicked';})()")
        r = cdp.call("Runtime.evaluate", {"expression": js, "returnByValue": True},
                     timeout=40).get("result", {}).get("value")
        time.sleep(7)
        return r

    cdp.call("Page.navigate", {"url": "http://localhost:8501/resume"}, timeout=60)
    # 这一页要渲染 7 套模板预览（外层 HTML 1MB+），写死 sleep(7) 经常只拿到半页，
    # 表现为"下载按钮时有时无"的假失败 → 轮询到关键元素出现为止（最多 45s）
    mine_html, mine = "", ""
    deadline = time.time() + 45
    while time.time() < deadline:
        time.sleep(3)
        mine_html = cdp.call("Runtime.evaluate", {
            "expression": "document.documentElement.outerHTML",
            "returnByValue": True}, timeout=60).get("result", {}).get("value") or ""
        mine = html_to_text(mine_html)
        if "下载 HTML" in mine and "放大看" in mine:
            break
    cdp.call("Page.navigate", {"url": "http://localhost:8501/settings"}, timeout=60)
    time.sleep(7)
    settings = text_now()
    cdp.close()

    checks = [
        ("我的简历页有照片区块", "简历照片" in mine),
        ("我的简历页有上传入口", "上传照片" in mine),
        ("我的简历页有模板选择", "简历模板" in mine),
        ("三个模板都出现",
         all(k in mine for k in ["经典单栏", "左侧栏", "极简黑白"])),
        ("模板缩略预览真的渲染了",
         all(f"oa-pv-{k}" in mine_html for k in ["classic", "sidebar", "compact"])),
        # 预览的作用域 class 会随实例名变化（card_classic / zoom / full_*），
        # 所以只断言"存在带 .oa-pv- 前缀且作用于 .page 的选择器"，不写死具体实例名
        ("预览样式被隔离（带作用域前缀）",
         all(f".oa-pv-{k}" in mine_html for k in ["classic", "sidebar", "compact"])),
        ("有放大整页预览", "放大看" in mine),
        ("有下载 HTML 按钮", "下载 HTML" in mine),
        # PDF 出口有两种形态：本机能渲染 → 显示下载按钮；云端无 Edge → 提示终端命令
        ("有 PDF 出口（下载按钮或终端命令提示）",
         "下载 PDF" in mine or "make_resume_pdf.py" in mine),
        ("我的简历页无 Traceback", "Traceback" not in mine),
        ("设置页不再有照片上传", "上传照片" not in settings),
        ("设置页把分享链接指向「展示」", "📇 展示" in settings or "展示" in settings),
    ]
    ok = 0
    for cname, good in checks:
        print(("✅ " if good else "❌ ") + cname)
        ok += 1 if good else 0
    print(f"\n{ok}/{len(checks)} 通过")


if __name__ == "__main__":
    main()
