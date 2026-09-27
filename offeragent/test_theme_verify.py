# -*- coding: utf-8 -*-
"""验证三套主题切换后样式真的不同（对比侧边栏底色、字号、圆角）。"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import browser_fetch as bf  # noqa: E402

CFG = HERE / "data" / "config.json"
THEMES = ["A 默认（深蓝·中庸）", "B Linear（深色紧凑）", "C Stripe（浅色宽松）"]
QUERY = {
    "侧边栏底色": "(function(){var e=document.querySelector('[data-testid=stSidebar]');return e?getComputedStyle(e).backgroundColor:'无';})()",
    "全局字号": "getComputedStyle(document.body).fontSize",
    "页头字号": "(function(){var e=document.querySelector('.oa-head-title');return e?getComputedStyle(e).fontSize:'无';})()",
    "指标数字": "(function(){var e=document.querySelector('[data-testid=stMetricValue]');return e?getComputedStyle(e).fontSize:'无';})()",
    "主色变量": "getComputedStyle(document.documentElement).getPropertyValue('--brand').trim()",
}


def main():
    if not bf.launch(headless=True):
        raise SystemExit("Edge 启动失败")
    for name in THEMES:
        cfg = json.loads(CFG.read_text(encoding="utf-8")) if CFG.exists() else {}
        cfg["theme"] = name
        CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        ws = bf._new_tab("http://localhost:8501")
        cdp = bf._CDP(ws)
        cdp.call("Page.enable")
        time.sleep(11)
        print(f"\n【{name}】")
        for label, expr in QUERY.items():
            r = cdp.call("Runtime.evaluate",
                         {"expression": expr, "returnByValue": True}, timeout=40)
            print(f"  {label}: {r.get('result', {}).get('value')}")
        cdp.close()


if __name__ == "__main__":
    main()
