# -*- coding: utf-8 -*-
"""语音组件缺失时的降级回归。

复制代码到临时目录，删除 static/voice_input 后启动应用，确认：
1. 应用仍能启动；
2. 公开名片页可打开且无 Python/Streamlit 异常；
3. 页面明确提示可改用文字输入。

跑法：python offeragent\test_voice_degraded.py
"""
import shutil
import subprocess
import sys
import tempfile
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
from test_cloud_boot import ERR_KWS, PY, PORT, stage  # noqa: E402
import requests  # noqa: E402


def main():
    tmp = Path(tempfile.mkdtemp(prefix="oa_voice_degraded_"))
    stage(tmp)
    shutil.rmtree(tmp / "static" / "voice_input")
    shutil.copy2(HERE / "data" / "profile.md", tmp / "data" / "profile.md")
    proc = subprocess.Popen(
        [PY, "-m", "streamlit", "run", "offer_agent_app.py",
         "--server.headless", "true", "--server.port", str(PORT + 2)],
        cwd=str(tmp), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        ok = False
        for _ in range(30):
            time.sleep(2)
            try:
                if requests.get(
                        f"http://localhost:{PORT + 2}/_stcore/health",
                        timeout=5).text.strip() == "ok":
                    ok = True
                    break
            except Exception:
                continue
        if not ok:
            raise SystemExit("❌ 删除语音组件后应用启动失败")

        if not bf.launch(headless=True):
            raise SystemExit("Edge 启动失败")
        ws = bf._new_tab(f"http://localhost:{PORT + 2}/twin")
        cdp = bf._CDP(ws)
        cdp.call("Page.enable")
        time.sleep(12)
        html = cdp.call("Runtime.evaluate", {
            "expression": "document.documentElement.outerHTML",
            "returnByValue": True}, timeout=60).get("result", {}).get("value") or ""
        text = html_to_text(html)
        cdp.close()

        bad = [keyword for keyword in ERR_KWS if keyword in text]
        checks = [
            ("应用可启动", ok),
            ("数字分身页可打开", "余剑" in text),
            ("无运行异常", not bad),
            ("提示可改用文字", "文字" in text and ("语音" in text or "语音组件" in text)),
        ]
        passed = 0
        for label, good in checks:
            print(("✅ " if good else "❌ ") + label)
            passed += int(good)
        print(f"\n{passed}/{len(checks)} 通过")
        if passed != len(checks):
            raise SystemExit(1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except Exception:
            proc.kill()
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"已清理临时目录：{tmp}")


if __name__ == "__main__":
    main()
