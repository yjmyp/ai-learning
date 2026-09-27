# -*- coding: utf-8 -*-
"""检查 theme.py 的样式到底有没有生效（诊断"界面难看"是不是样式没应用）。"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import browser_fetch as bf  # noqa: E402

CHECKS = {
    "候选容器 main": "(function(){var e=document.querySelector('main');return e?getComputedStyle(e).maxWidth+' / '+e.className:'无';})()",
    "候选容器 .block-container": "(function(){var e=document.querySelector('.block-container');return e?getComputedStyle(e).maxWidth+' / '+e.className:'无';})()",
    "候选容器 section.main": "(function(){var e=document.querySelector('section.main');return e?getComputedStyle(e).maxWidth+' / '+e.className:'无';})()",
    "候选容器 stAppViewContainer": "(function(){var e=document.querySelector('[data-testid=stAppViewContainer]');return e?getComputedStyle(e).maxWidth+' / '+e.className:'无';})()",
    "候选容器 stMainBlockContainer": "(function(){var e=document.querySelector('[data-testid=stMainBlockContainer]');return e?getComputedStyle(e).maxWidth+' / '+e.className:'无';})()",
    "候选容器 stMain": "(function(){var e=document.querySelector('[data-testid=stMain]');return e?getComputedStyle(e).maxWidth+' / '+e.className:'无';})()",
    "垂直块间距": "(function(){var e=document.querySelector('[data-testid=stVerticalBlock]');return e?getComputedStyle(e).rowGap:'无';})()",
    "CSS变量 --brand": "getComputedStyle(document.documentElement).getPropertyValue('--brand').trim()",
    "页头元素存在": "!!document.querySelector('.oa-head-title')",
    "页头字号": "(function(){var e=document.querySelector('.oa-head-title');return e?getComputedStyle(e).fontSize:'无';})()",
    "页头字体粗细": "(function(){var e=document.querySelector('.oa-head-title');return e?getComputedStyle(e).fontWeight:'无';})()",
    "侧边栏背景色": "(function(){var e=document.querySelector('[data-testid=stSidebar]');return e?getComputedStyle(e).backgroundColor:'无';})()",
    "主容器最大宽度": "(function(){var e=document.querySelector('main .block-container');return e?getComputedStyle(e).maxWidth:'无';})()",
    "按钮圆角": "(function(){var e=document.querySelector('.stButton > button');return e?getComputedStyle(e).borderRadius:'无';})()",
    "全局字号": "getComputedStyle(document.body).fontSize",
    "页面标题": "document.title",
}


def main():
    if not bf.launch(headless=True):
        raise SystemExit("Edge 启动失败")
    ws = bf._new_tab("http://localhost:8501")
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    time.sleep(10)
    for name, expr in CHECKS.items():
        r = cdp.call("Runtime.evaluate",
                     {"expression": expr, "returnByValue": True}, timeout=40)
        print(f"  {name}: {r.get('result', {}).get('value')}")
    cdp.close()


if __name__ == "__main__":
    main()
