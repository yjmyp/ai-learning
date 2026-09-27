# -*- coding: utf-8 -*-
"""调试小工具：打印当前页面所有 label / button 的可见文字。

用途：写验收脚本时先看清 Streamlit 到底把控件渲染成什么。
跑法：python offeragent\\_probe_dom.py [导航词]
"""
import json
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

JS = """
(function(){
  var out = {labels: [], buttons: [], radios: []};
  document.querySelectorAll('label').forEach(function(e){
    var t = (e.innerText || '').trim(); if (t) out.labels.push(t);});
  document.querySelectorAll('button').forEach(function(e){
    var t = (e.innerText || '').trim(); if (t) out.buttons.push(t);});
  document.querySelectorAll('[role=radio]').forEach(function(e){
    var t = (e.innerText || '').trim(); if (t) out.radios.push(t);});
  return JSON.stringify(out);
})()
"""


def main():
    nav = sys.argv[1] if len(sys.argv) > 1 else ""
    if not bf.launch(headless=True):
        raise SystemExit("Edge 启动失败")
    ws = bf._new_tab("http://localhost:8501")
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    time.sleep(13)
    if nav:
        js = ("(function(){var ls=[].slice.call(document.querySelectorAll('label'));"
              f"var el=ls.filter(function(e){{return e.innerText.trim().indexOf('{nav}')>=0;}})"
              ".filter(function(e){return e.innerText.trim().length<10;})[0];"
              "if(!el) return 'not-found'; el.click(); return 'clicked';})()")
        print("点击", nav, "=", cdp.call("Runtime.evaluate",
                                        {"expression": js, "returnByValue": True},
                                        timeout=40).get("result", {}).get("value"))
        time.sleep(7)
    raw = cdp.call("Runtime.evaluate", {"expression": JS, "returnByValue": True},
                   timeout=40).get("result", {}).get("value")
    cdp.close()
    d = json.loads(raw)
    for k, v in d.items():
        print(f"--- {k} ({len(v)}) ---")
        for item in v[:30]:
            print("   ", item.replace("\n", " / ")[:60])


if __name__ == "__main__":
    main()
