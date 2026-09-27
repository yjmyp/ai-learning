# -*- coding: utf-8 -*-
"""新信息架构验收：五个分区、二级子页、去重规则（话术只有一处、简历只有一处）。

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

    pages = {}
    for g in ["今天", "找工作", "🧬 我的", "展示", "设置"]:
        click("label", g)
        pages[g] = text_now()

    checks = []
    # 一级：五个分区都在侧边栏、且都点得开
    checks.append(("五个一级分区都能打开",
                   all("Traceback" not in v for v in pages.values())))
    # 今天
    checks.append(("今天有二级：今日行动 / 数据与日志",
                   "今日行动" in pages["今天"] and "数据与日志" in pages["今天"]))
    click("label", "今天")
    click("button", "数据与日志")
    dl = text_now()
    checks.append(("统计数据在「数据与日志」里", "投递漏斗" in dl))
    checks.append(("顶部流程条仍显示进度", "① 找岗" in dl and "④ 有回应" in dl))
    click("button", "今日行动")
    checks.append(("今天不再放每日目标输入框", "每天投几家" not in pages["今天"]))
    # 找工作
    w = pages["找工作"]
    checks.append(("找工作的二级齐全",
                   all(k in w for k in ["岗位库", "匹配分析", "简历", "投递台", "投递记录"])))
    # 我的
    m = pages["🧬 我的"]
    checks.append(("我的的二级齐全",
                   all(k in m for k in ["自我蒸馏", "面试拷问", "分身陪练", "复盘入库"])))
    # 展示
    s = pages["展示"]
    checks.append(("展示有素材自检", "对外素材自检" in s))
    checks.append(("展示有名片链接", "公开数字名片" in s or "twin=1" in s))
    # 设置
    st_ = pages["设置"]
    checks.append(("设置有每日投递目标", "每日投递目标" in st_))
    checks.append(("设置有花费保护", "花费保护" in st_))
    checks.append(("设置不再放分享链接", "twin=1" not in st_))

    # 去重规则 1：话术只在投递台生成
    click("label", "今天")
    today = text_now()
    checks.append(("今日行动卡片改跳投递台", "去投递台生成话术" in today))
    click("label", "找工作")
    click("button", "投递台")
    desk = text_now()
    checks.append(("投递台有批量/单条两种模式",
                   "批量" in desk and "单条精修" in desk))
    checks.append(("投递台是三版话术场景", "BOSS" in desk and "邮件" in desk and "内推" in desk))
    checks.append(("投递台不再有简历定制", "简历定制" not in desk))
    # 去重规则 2：简历只有一个地方
    click("label", "找工作")
    click("button", "简历")
    res = text_now()
    checks.append(("简历页含内容+模板+覆盖检查",
                   "简历内容 / 模板 / 照片" in res and "按岗位检查覆盖" in res))
    checks.append(("简历页无 Traceback", "Traceback" not in res))

    cdp.close()
    ok = 0
    for cname, good in checks:
        print(("✅ " if good else "❌ ") + cname)
        ok += 1 if good else 0
    print(f"\n{ok}/{len(checks)} 通过")


if __name__ == "__main__":
    main()
