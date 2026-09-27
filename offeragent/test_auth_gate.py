# -*- coding: utf-8 -*-
"""密码门验收：用 APP_PASSWORD 起一个临时实例，确认「不输密码进不去」。

跑法：python offeragent\test_auth_gate.py
"""
import os
import subprocess
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
import requests  # noqa: E402

PORT = 8504
DEMO_PW = "demo-pass-2027"


def main():
    env = dict(os.environ, APP_PASSWORD=DEMO_PW)
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "offer_agent_app.py",
         "--server.headless", "true", "--server.port", str(PORT)],
        cwd=str(HERE), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        ok = False
        for _ in range(30):
            time.sleep(2)
            try:
                if requests.get(f"http://localhost:{PORT}/_stcore/health",
                                timeout=5).text.strip() == "ok":
                    ok = True
                    break
            except Exception:
                continue
        if not ok:
            raise SystemExit("❌ 带密码的实例没起来")

        if not bf.launch(headless=True):
            raise SystemExit("Edge 启动失败")
        ws = bf._new_tab(f"http://localhost:{PORT}")
        cdp = bf._CDP(ws)
        cdp.call("Page.enable")
        time.sleep(12)
        html = cdp.call("Runtime.evaluate", {
            "expression": "document.documentElement.outerHTML",
            "returnByValue": True}, timeout=60).get("result", {}).get("value") or ""
        text = html_to_text(html)
        cdp.close()

        checks = [
            ("出现 🔒 密码页", "🔒" in text or "访问密码" in text),
            ("有「进入」按钮", "进入" in text),
            ("没输密码看不到主界面", "待投岗位" not in text and "今日行动" not in text),
        ]
        good = 0
        for cname, okk in checks:
            print(("✅ " if okk else "❌ ") + cname)
            good += 1 if okk else 0
        print(f"\n{good}/{len(checks)} 通过")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    main()
