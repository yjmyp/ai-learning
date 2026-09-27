# -*- coding: utf-8 -*-
"""云端空数据冒烟测试：把代码复制到临时目录（不含 data/），在 8502 端口跑一遍。

为什么需要：Streamlit Cloud 上 data/ 是空的（本地求职数据不上传），
本地 8501 有数据所以走不到「首次访问」的分支。这个脚本专门模拟首次访问。

跑法：python offeragent\test_cloud_boot.py
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
import requests  # noqa: E402

PY = sys.executable
PORT = 8502
NAV = [("今天", "/"), ("岗位库", "/jobs"), ("匹配分析", "/match"),
       ("简历", "/resume"), ("投递台", "/apply"), ("投递记录", "/records"),
       ("自我蒸馏", "/distill"), ("面试准备", "/interview"),
       ("名片与分享", "/show"), ("设置", "/settings")]
ERR_KWS = ["Traceback", "StreamlitDuplicateElementId", "KeyError",
           "AttributeError", "NameError", "TypeError", "ValueError",
           "ModuleNotFoundError", "FileNotFoundError"]


def stage(tmp: Path):
    """只复制代码，不复制 data/（模拟云端仓库内容）。"""
    for p in HERE.iterdir():
        if p.name in ("data", "__pycache__", ".git"):
            continue
        if p.name.startswith("reference_"):
            continue
        if p.is_file():
            if p.suffix in (".png", ".jpg", ".log"):
                continue
            shutil.copy2(p, tmp / p.name)
        elif p.is_dir():
            dst = tmp / p.name
            dst.mkdir(parents=True, exist_ok=True)
            for f in p.iterdir():
                if f.is_file() and f.name not in ("secrets.toml",):
                    shutil.copy2(f, dst / f.name)
    (tmp / "data").mkdir(exist_ok=True)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="oa_cloud_"))
    stage(tmp)
    print(f"临时目录：{tmp}")
    proc = subprocess.Popen(
        [PY, "-m", "streamlit", "run", "offer_agent_app.py",
         "--server.headless", "true", "--server.port", str(PORT)],
        cwd=str(tmp), stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        ok = False
        for _ in range(30):
            time.sleep(2)
            try:
                if requests.get(
                        f"http://localhost:{PORT}/_stcore/health",
                        timeout=5).text.strip() == "ok":
                    ok = True
                    break
            except Exception:
                continue
        if not ok:
            raise SystemExit("❌ 云端模拟启动失败（30 次探测都没起来）")
        print("✅ 空数据启动成功，开始逐页巡检")

        if not bf.launch(headless=True):
            raise SystemExit("Edge 启动失败")
        ws = bf._new_tab(f"http://localhost:{PORT}")
        cdp = bf._CDP(ws)
        cdp.call("Page.enable")
        time.sleep(12)

        def text_now():
            html = cdp.call("Runtime.evaluate", {
                "expression": "document.documentElement.outerHTML",
                "returnByValue": True}, timeout=60).get("result", {}).get("value") or ""
            return html_to_text(html)

        bad_total = 0
        for label, path in NAV:
            cdp.call("Page.navigate",
                     {"url": f"http://localhost:{PORT}" + path}, timeout=60)
            time.sleep(6)
            t = text_now()
            bad = [k for k in ERR_KWS if k in t]
            bad_total += len(bad)
            print(f"{label:<8} {path:<11} 报错={bad if bad else '无'}"
                  f" | 文本 {len(t)} 字")
        cdp.close()
        print("\n结论：", f"✅ 空数据（云端首访）{len(NAV)} 个页面都没有报错"
              if not bad_total else f"❌ 空数据下有 {bad_total} 处报错")
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
