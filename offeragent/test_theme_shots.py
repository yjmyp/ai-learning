# -*- coding: utf-8 -*-
"""
给 B / C 两套主题各截几张图，方便对比。

跑法：python offeragent\test_theme_shots.py
输出：offeragent/data/shots/theme{B,C}_*.png
注意：会临时改 data/config.json 的 theme 字段，跑完恢复原值。
"""
import base64
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import browser_fetch as bf  # noqa: E402
from job_sources import html_to_text  # noqa: E402

CFG = HERE / "data" / "config.json"
SHOTS = HERE / "data" / "shots"
PAGES = ["今日", "岗位"]
THEMES = [("B Linear（深色紧凑）", "B"), ("C Stripe（浅色宽松）", "C")]
ERR = ["Traceback", "StreamlitDuplicateElementId", "KeyError", "NameError", "TypeError"]


def set_theme(name: str):
    cfg = json.loads(CFG.read_text(encoding="utf-8")) if CFG.exists() else {}
    cfg["theme"] = name
    CFG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    old = None
    if CFG.exists():
        try:
            old = json.loads(CFG.read_text(encoding="utf-8")).get("theme")
        except Exception:
            old = None
    if not bf.launch(headless=True):
        raise SystemExit("Edge 启动失败")

    for theme_name, tag in THEMES:
        set_theme(theme_name)
        for label in PAGES:
            ws = bf._new_tab("http://localhost:8501")
            cdp = bf._CDP(ws)
            cdp.call("Page.enable")
            cdp.call("Emulation.setDeviceMetricsOverride", {
                "width": 1500, "height": 1000, "deviceScaleFactor": 1, "mobile": False})
            time.sleep(11)
            click = ("(function(){var ls=[].slice.call(document.querySelectorAll('label'));"
                     f"var el=ls.filter(function(e){{return e.innerText.trim().indexOf('{label}')>=0;}})"
                     ".filter(function(e){return e.innerText.trim().length<8;})[0];"
                     "if(!el) return 'not-found'; el.click(); return 'clicked';})()")
            r = cdp.call("Runtime.evaluate", {"expression": click, "returnByValue": True}, timeout=40)
            time.sleep(7)
            text = html_to_text(cdp.call("Runtime.evaluate", {
                "expression": "document.documentElement.outerHTML",
                "returnByValue": True}, timeout=40).get("result", {}).get("value") or "")
            bad = [k for k in ERR if k in text]
            shot = SHOTS / f"theme{tag}_{label}.png"
            res = cdp.call("Page.captureScreenshot",
                           {"format": "png", "captureBeyondViewport": True}, timeout=60)
            shot.write_bytes(base64.b64decode(res.get("data", "")))
            print(f"主题 {tag} · {label:<4} 点击={r.get('result',{}).get('value')} "
                  f"报错={bad if bad else '无'} → {shot.name}")
            cdp.close()

    if old:
        set_theme(old)
    print(f"\n截图目录：{SHOTS}")


if __name__ == "__main__":
    main()
