# -*- coding: utf-8 -*-
"""新信息架构验收：原生多页导航（分区 + 真实 URL）+ 去重规则。

跑法：python offeragent\test_nav_structure.py（需要 localhost:8501 已在跑）
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

EXPECT_LINKS = {
    "今天（行动 + 数据）": "/",
    "岗位库": "/jobs", "匹配分析": "/match", "简历（模板 / 照片）": "/resume",
    "投递台": "/apply", "投递记录": "/records",
    "自我蒸馏": "/distill", "面试准备（拷问 / 陪练 / 复盘）": "/interview",
    "名片与分享": "/show", "设置": "/settings",
}


def main():
    if not bf.launch(headless=True):
        raise SystemExit("Edge 启动失败")
    ws = bf._new_tab("http://localhost:8501")
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    cdp.call("Emulation.setDeviceMetricsOverride", {
        "width": 1500, "height": 1300, "deviceScaleFactor": 1, "mobile": False})
    time.sleep(13)

    def text_at(path):
        cdp.call("Page.navigate", {"url": "http://localhost:8501" + path}, timeout=60)
        time.sleep(6)
        html = cdp.call("Runtime.evaluate", {
            "expression": "document.documentElement.outerHTML",
            "returnByValue": True}, timeout=60).get("result", {}).get("value") or ""
        return html_to_text(html), html

    root_text, root_html = text_at("/")
    # 侧边栏导航：应该是带 href 的链接（原生多页），不是自己画的单选按钮
    # 侧边栏链接是绝对地址（http://host/path），按这个匹配
    missing = [f"{t}({h})" for t, h in EXPECT_LINKS.items()
               if f"localhost:8501{h}" not in root_html
               and f"localhot:8501{h}" not in root_html
               and f"8501{h}" not in root_html]
    has_old_radio = 'role="radiogroup"' in root_html and "导航" in root_text

    checks = [
        ("侧边栏 10 个页面链接都在（没被折叠）", not missing),
        ("没有被折叠的「View more」", "more" not in root_html.lower()
         or "view more" not in root_html.lower()),
        ("不再有自己的「导航」单选组", not has_old_radio),
        ("今日行动页有流程条", "① 找岗" in root_text),
        ("今日行动卡片改跳投递台", "去投递台生成话术" in root_text),
        ("今日页不再放每日目标输入框", "每天投几家" not in root_text),
        ("今天页有两个页签", "行动清单" in root_text and "数据与日志" in root_text),
    ]

    # 数据与日志是「今天」页的第二个页签
    cdp.call("Runtime.evaluate", {"expression":
             "(function(){var bs=[].slice.call(document.querySelectorAll('button, [role=tab]'));"
             "var el=bs.filter(function(e){return e.innerText.trim().indexOf('数据与日志')>=0;})[0];"
             "if(!el) return 'nf'; el.click(); return 'ok';})()",
             "returnByValue": True}, timeout=40)
    time.sleep(6)
    tab_text = html_to_text(cdp.call("Runtime.evaluate", {
        "expression": "document.documentElement.outerHTML",
        "returnByValue": True}, timeout=60).get("result", {}).get("value") or "")
    checks.append(("统计数据在今天页的第二个页签里（漏斗）", "投递漏斗" in tab_text))

    apply_text, _ = text_at("/apply")
    checks.append(("投递台有批量/单条两种方式",
                   "批量" in apply_text and "单条精修" in apply_text))
    checks.append(("投递台有三版话术场景",
                   "BOSS" in apply_text and "邮件" in apply_text and "内推" in apply_text))
    checks.append(("投递台不再有简历定制", "简历定制" not in apply_text))

    res_text, _ = text_at("/resume")
    checks.append(("简历页同时有内容与覆盖检查两个页签",
                   "简历内容 / 模板 / 照片" in res_text and "ATS" in res_text))
    checks.append(("简历页有三套模板缩略预览",
                   all(k in res_text for k in ["经典单栏", "左侧栏", "极简黑白"])))

    int_text, _ = text_at("/interview")
    checks.append(("面试准备页三个页签齐全",
                   all(k in int_text for k in ["面试拷问", "分身陪练", "复盘入库"])))

    rec_text, _ = text_at("/records")
    checks.append(("投递记录只记事实（漏斗指向数据页）",
                   "数据与日志" in rec_text))

    show_text, _ = text_at("/show")
    checks.append(("展示页有素材自检", "对外素材自检" in show_text))
    checks.append(("展示页有名片链接", "twin=1" in show_text))

    set_text, _ = text_at("/settings")
    checks.append(("设置有每日投递目标", "每日投递目标" in set_text))
    checks.append(("设置有花费保护", "花费保护" in set_text))
    checks.append(("设置不再放分享链接", "twin=1" not in set_text))

    cdp.close()
    ok = 0
    for cname, good in checks:
        print(("✅ " if good else "❌ ") + cname)
        ok += 1 if good else 0
    if missing:
        print("   缺失链接：", missing)
    print(f"\n{ok}/{len(checks)} 通过")
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
