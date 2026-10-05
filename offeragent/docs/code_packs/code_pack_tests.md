# 代码包：测试与项目说明（26 个测试 + run_tests + README）

> 内容包括：26 个测试脚本、统一测试入口 run_tests.py、README。目标是让 AI 看懂「测试怎么组织、怎么跑、断言什么」。

## 怎么喂
把本文件全文复制给 DeepSeek，开头加一句：
> 「先读完全文代码，再按我的水平逐块讲解，一次一小步，先框架后填空，不直接给完整答案。」

## 包含的文件

| 文件 | 行数 | 说明 |
|---|---|---|
| `offeragent/test_all_pages_sweep.py` | 81 | 见下方代码 |
| `offeragent/test_app_pages.py` | 74 | 见下方代码 |
| `offeragent/test_app_render.py` | 40 | 见下方代码 |
| `offeragent/test_auth_gate.py` | 80 | 见下方代码 |
| `offeragent/test_browser_guard.py` | 91 | 见下方代码 |
| `offeragent/test_cloud_boot.py` | 120 | 见下方代码 |
| `offeragent/test_css_check.py` | 47 | 见下方代码 |
| `offeragent/test_distill.py` | 81 | 见下方代码 |
| `offeragent/test_feature_research.py` | 76 | 见下方代码 |
| `offeragent/test_flow_check.py` | 107 | 见下方代码 |
| `offeragent/test_grab_error.py` | 38 | 见下方代码 |
| `offeragent/test_my_resume_page.py` | 93 | 见下方代码 |
| `offeragent/test_nav_structure.py` | 122 | 见下方代码 |
| `offeragent/test_ocr.py` | 54 | 见下方代码 |
| `offeragent/test_ref_links.py` | 30 | 见下方代码 |
| `offeragent/test_resume_clean.py` | 61 | 见下方代码 |
| `offeragent/test_resume_preview.py` | 123 | 见下方代码 |
| `offeragent/test_source_yield.py` | 68 | 见下方代码 |
| `offeragent/test_sources.py` | 44 | 见下方代码 |
| `offeragent/test_sources_live.py` | 68 | 见下方代码 |
| `offeragent/test_sources_parse.py` | 87 | 见下方代码 |
| `offeragent/test_talk.py` | 97 | 见下方代码 |
| `offeragent/test_theme_shots.py` | 78 | 见下方代码 |
| `offeragent/test_theme_verify.py` | 44 | 见下方代码 |
| `offeragent/test_twin_portal.py` | 55 | 见下方代码 |
| `offeragent/test_undefined_names.py` | 229 | 见下方代码 |
| `run_tests.py` | 98 | 见下方代码 |
| `offeragent/README.md` | 184 | 见下方代码 |

**合计 2370 行**（约 9KB），在 DeepSeek 上下文内。

---

## ===== offeragent/test_all_pages_sweep.py（81 行）=====

```python
# -*- coding: utf-8 -*-
"""全量巡检：把每一个一级分区的**每一个二级子页**都点一遍。

为什么需要：线上白屏那次，浏览器脚本只点了一级导航（默认子页），
「投递记录」这个子页里的 NameError 就没被发现。这个脚本按子页巡。

跑法：python offeragent\test_all_pages_sweep.py（需要 localhost:8501 已在跑）
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

# 原生多页导航后每页都有真实 URL，直接按 URL 巡，比点元素稳
PLAN = [
    ("今天（行动 + 数据）", "/"),
    ("岗位库", "/jobs"),
    ("匹配分析", "/match"),
    ("简历（模板/照片/覆盖）", "/resume"),
    ("投递台", "/apply"),
    ("投递记录", "/records"),
    ("自我蒸馏", "/distill"),
    ("面试准备（拷问/陪练/复盘）", "/interview"),
    ("名片与分享", "/show"),
    ("设置", "/settings"),
]
ERR_KWS = ["Traceback", "NameError", "KeyError", "AttributeError", "TypeError",
           "ValueError", "ModuleNotFoundError", "StreamlitDuplicateElementId",
           "UnboundLocalError", "IndexError"]


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

    def go(path):
        cdp.call("Page.navigate", {"url": "http://localhost:8501" + path}, timeout=60)
        time.sleep(6)

    bad = []
    for name, path in PLAN:
        go(path)
        t = text_now()
        hits = [k for k in ERR_KWS if k in t]
        flag = "❌" if hits else "✅"
        print(f"{flag} {name:<18} {path:<10} 报错={hits if hits else '无'} | {len(t)} 字")
        if hits:
            bad.append((name, path, hits))
    cdp.close()
    print()
    if bad:
        print(f"❌ {len(bad)} 个页面有报错：")
        for name, path, h in bad:
            print("   ", name, path, h)
    else:
        print("✅ 所有页面都没有报错")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
```

## ===== offeragent/test_app_pages.py（74 行）=====

```python
# -*- coding: utf-8 -*-
"""
逐页巡检：把 5 个导航页都点一遍，检查有没有报错，并给每页存一张截图。

跑法：python offeragent\test_app_pages.py
输出：offeragent/data/shots/page_*.png
"""
import base64
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
# Windows 控制台默认 GBK，直接 print emoji 会 UnicodeEncodeError，这里强制 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import browser_fetch as bf  # noqa: E402
from job_sources import html_to_text  # noqa: E402

OUT_DIR = HERE / "data" / "shots"
# 原生多页导航：每页有真实 URL，直接按 URL 巡
PLAN = [("today", "/"), ("jobs", "/jobs"), ("match", "/match"),
        ("resume", "/resume"), ("apply", "/apply"), ("records", "/records"),
        ("distill", "/distill"), ("interview", "/interview"),
        ("show", "/show"), ("settings", "/settings")]
ERR_KWS = ["Traceback", "StreamlitDuplicateElementId", "KeyError",
           "AttributeError", "NameError", "TypeError", "ValueError",
           "ModuleNotFoundError", "st.error"]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not bf.launch(headless=True):
        raise SystemExit("Edge 启动失败")
    ws = bf._new_tab("http://localhost:8501")
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    cdp.call("Emulation.setDeviceMetricsOverride", {
        "width": 1500, "height": 1000, "deviceScaleFactor": 1, "mobile": False})
    time.sleep(10)  # 等首屏加载

    def evaljs(expr):
        r = cdp.call("Runtime.evaluate",
                     {"expression": expr, "returnByValue": True}, timeout=60)
        return r.get("result", {}).get("value")

    results = []
    for i, (label, path) in enumerate(PLAN):
        cdp.call("Page.navigate", {"url": "http://localhost:8501" + path}, timeout=60)
        time.sleep(6)
        text = html_to_text(evaljs("document.documentElement.outerHTML") or "")
        bad = [k for k in ERR_KWS if k in text]
        shot = OUT_DIR / f"page_{i + 1}_{label}.png"
        res = cdp.call("Page.captureScreenshot",
                       {"format": "png", "captureBeyondViewport": True}, timeout=60)
        shot.write_bytes(base64.b64decode(res.get("data", "")))
        results.append((label, path, bad, len(text), shot.name))
        print(f"{label:<9} {path:<10} 报错={bad if bad else '无'}"
              f" | 文本 {len(text)} 字 | {shot.name}")

    cdp.close()
    print(f"\n截图目录：{OUT_DIR}")
    bad_total = [r for r in results if r[2]]
    print("结论：", f"✅ {len(PLAN)} 个页面都没有报错" if not bad_total
          else f"❌ 有 {len(bad_total)} 个页面报错")


if __name__ == "__main__":
    main()
```

## ===== offeragent/test_app_render.py（40 行）=====

```python
# -*- coding: utf-8 -*-
"""用无头浏览器打开本地应用，检查页面是否渲染正常、有没有报错。"""
import re
import sys
from pathlib import Path

# Windows 控制台默认 GBK，直接 print emoji/✓ 会 UnicodeEncodeError，强制 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import browser_fetch as bf  # noqa: E402
from job_sources import html_to_text  # noqa: E402


def check(url: str, label: str):
    html = bf.fetch_html(url, wait=8)
    text = html_to_text(html)
    print(f"--- {label} ---")
    print(f"  HTML {len(html)} 字节 | 文本 {len(text)} 字符")
    bad = []
    for kw in ["Traceback", "KeyError", "AttributeError", "NameError",
               "TypeError", "ValueError", "ModuleNotFound"]:
        if kw in text:
            bad.append(kw)
    print("  报错关键词：", bad if bad else "无")
    # 看看关键标题在不在
    for kw in ["今日行动", "导航", "OfferAgent", "待投"]:
        print(f"  含「{kw}」：{kw in text}")
    return not bad


if __name__ == "__main__":
    ok = check("http://localhost:8501", "首页渲染检查")
    print("\n结论：", "✅ 渲染正常" if ok else "❌ 页面里有报错，需要修")
```

## ===== offeragent/test_auth_gate.py（80 行）=====

```python
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
```

## ===== offeragent/test_browser_guard.py（91 行）=====

```python
# -*- coding: utf-8 -*-
"""浏览器抓取（BOSS）的兜底与守卫验收：

1. 环境变量 EDGE_PATH 优先
2. 云端（Linux）明确说"只在本机可用"，而不是抛「没找到 Edge」
3. 云端跑「全部平台」时会跳过 BOSS，并把原因写进 errors，不炸整个搜索

跑法：python offeragent\test_browser_guard.py
"""
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import browser_fetch as bf          # noqa: E402
import job_sources as js            # noqa: E402


def main():
    checks = []

    # 1) 环境变量优先
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
        fake = f.name
    import os
    old = os.environ.get("EDGE_PATH")
    os.environ["EDGE_PATH"] = fake
    try:
        checks.append(("EDGE_PATH 环境变量优先", bf.edge_path() == fake))
    except Exception as e:
        checks.append(("EDGE_PATH 环境变量优先", False))
        print("   异常：", e)
    finally:
        if old is None:
            os.environ.pop("EDGE_PATH", None)
        else:
            os.environ["EDGE_PATH"] = old
        Path(fake).unlink(missing_ok=True)

    # 2) 候选清单覆盖常见位置 + PATH
    cands = bf.edge_candidates()
    checks.append(("候选清单里有 LocalAppData 路径",
                   any("Microsoft\\Edge\\Application".lower() in c.lower()
                       or "Microsoft/Edge/Application".lower() in c.lower()
                       for c in cands)))
    checks.append(("候选清单里有 Chrome 兜底",
                   any("chrome" in c.lower() for c in cands)))
    checks.append(("错误提示里给了解决办法",
                   "EDGE_PATH" in bf.no_browser_message()
                   and "牛客" in bf.no_browser_message()))

    # 3) 模拟云端：Linux 平台
    real_platform = bf.sys.platform
    try:
        bf.sys.platform = "linux"
        ok, why = bf.desktop_available()
        checks.append(("云端判定为不可用", ok is False))
        checks.append(("云端理由说得是人话（提到云端/牛客）",
                       ("云端" in why) or ("牛客" in why)))
        ok2, why2 = js.boss_available()
        checks.append(("job_sources 也同步为不可用", ok2 is False))

        # 只选 BOSS：应被跳过并写进 errors，而不是抛异常
        res = js.search_all("AI", "南京", ask_model=None, sources=["BOSS直聘"])
        checks.append(("云端只选 BOSS 时优雅跳过", res["jobs"] == []
                       and "BOSS直聘" in res["errors"]))
    finally:
        bf.sys.platform = real_platform

    # 4) 本机（Windows）应当能用（CI/云端跑这条会跳过）
    if real_platform in ("win32", "darwin"):
        ok, why = bf.desktop_available()
        checks.append(("本机判定为可用", ok is True))

    ok_n = 0
    for cname, good in checks:
        print(("✅ " if good else "❌ ") + cname)
        ok_n += 1 if good else 0
    print(f"\n{ok_n}/{len(checks)} 通过")
    return 0 if ok_n == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
```

## ===== offeragent/test_cloud_boot.py（120 行）=====

```python
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
```

## ===== offeragent/test_css_check.py（47 行）=====

```python
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
```

## ===== offeragent/test_distill.py（81 行）=====

```python
# -*- coding: utf-8 -*-
"""
自我蒸馏模块端到端测试：用一组示例答案跑一遍，看 6 份产物长什么样。
不会覆盖你真实的 data/*.md（输出写到 data/distill_test/）。

跑法：python offeragent\test_distill.py
"""
import re
import sys
from pathlib import Path

import requests

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import distill  # noqa: E402

SECRETS = HERE / ".streamlit" / "secrets.toml"
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

# 示例答案（用来验证产出结构，不是余剑的真实答案）
SAMPLE = {
    "q1": "RAG 知识库问答系统，个人笔记变成能问答的知识库；还有一个 Agent 工具调用 Demo，让模型按 JSON 调计算工具。",
    "q2": "RAG：11 篇资料切 254 块，自建 12 条评估集，top-1/3/5 = 75%/83%/92%。Demo：3 个工具，能拦 5 类坏输出。",
    "q3": "RAG 部署过 Streamlit Cloud，后来因为省 costs 下线了；代码在 GitHub。",
    "q4": "把链路跑通这件事最顺，从读文件到检索到生成，我能一块块拆开调。",
    "q5": "从空白文件写新功能最容易卡，看得懂别人的代码但自己起手难。",
    "q6": "LangChain、Docker、模型微调、多 Agent，都没做过。",
    "q7": "先找一个能跑的最小例子改，改着改着再回头看原理。",
    "q8": "看官方文档加抄改现成代码，然后做一个小 demo 验证。",
    "q9": "下午和晚上效率高，一个人安静时最好；有人催或者任务目标不清楚时容易停住。",
    "q10": "好奇占一半，另一半是想快点有作品去面试。",
    "q11": "先硬扛一会儿，扛不动就换别的任务缓一下，很少主动找人。",
    "q12": "最不能接受目标是天天变、没人带又要我出结果的活。",
    "q13": "喜欢各做一块最后合，但自己一个人做也行，同步太频繁会打断我。",
    "q14": "先列出来对比，实在分不清就问人。",
    "q15": "队友说过我执行快、能自己查资料；也说过我有时候钻牛角尖、不太主动说话。",
}


def load_key() -> str:
    m = re.search(r'DEEPSEEK_API_KEY\s*=\s*"([^"]+)"',
                  SECRETS.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("没找到 API Key")
    return m.group(1)


def main():
    key = load_key()

    def ask(prompt: str) -> str:
        r = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}]},
            timeout=180,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    state = {"answers": SAMPLE, "followups": {}}
    print(f"模拟进度：{distill.progress(state)}")
    out_dir = HERE / "data" / "distill_test"
    outputs = distill.distill(state, ask, out_dir=out_dir)
    print(f"\n生成 {len(outputs)} 份文件 → {out_dir}")
    for name in ["profile.md", "highlights.md", "interview_answers.md",
                 "gaps.md", "work_style.md", "clone_brief.md"]:
        content = outputs.get(name, "")
        print("\n" + "=" * 70)
        print(f"【{name}】 {len(content)} 字")
        print("=" * 70)
        print(content[:1500])


if __name__ == "__main__":
    main()
```

## ===== offeragent/test_feature_research.py（76 行）=====

```python
# -*- coding: utf-8 -*-
"""扒一扒同类求职工具都有什么功能，给"还能加什么"做参考。"""
import base64
import re
import sys
import time
import urllib.parse

import requests

# Windows 控制台默认 GBK，直接 print emoji 会 UnicodeEncodeError，强制 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

H = {"User-Agent": "codex"}

QUERIES = [
    "job application tracker", "AI interview prep", "resume tailoring LLM",
    "job search automation agent", "求职 管理 系统",
]


def search(q, n=4):
    u = ("https://api.github.com/search/repositories?q="
         + urllib.parse.quote(q) + f"&sort=stars&per_page={n}")
    try:
        return requests.get(u, headers=H, timeout=30).json().get("items", [])
    except Exception:
        return []


def readme(repo):
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/readme",
                         headers=H, timeout=30).json()
        return base64.b64decode(r["content"].replace("\n", "")).decode("utf-8", "ignore")
    except Exception:
        return ""


def features(text, limit=14):
    """从 README 里挑出像功能点儿的行。"""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith(("- ", "* ", "• ")):
            continue
        s = re.sub(r"[*`_]", "", s[2:]).strip()
        if not (6 <= len(s) <= 90):
            continue
        if re.search(r"(install|npm|pip|docker|clone|yarn|http|license|目录)", s, re.I):
            continue
        out.append(s)
        if len(out) >= limit:
            break
    return out


if __name__ == "__main__":
    seen = set()
    for q in QUERIES:
        print("=" * 72)
        print("搜索：", q)
        for it in search(q):
            full = it["full_name"]
            if full in seen:
                continue
            seen.add(full)
            print(f"\n▌{full}  ({it.get('stargazers_count')}⭐)")
            print(f"  {it.get('description') or ''}"[:110])
            for f in features(readme(full), 10):
                print("   ·", f)
            time.sleep(0.5)
```

## ===== offeragent/test_flow_check.py（107 行）=====

```python
# -*- coding: utf-8 -*-
"""流程改造验收：检查顶部流程条、一站式岗位卡片、我的资料导航是否真的渲染出来。

跑法：python offeragent\test_flow_check.py（需要 localhost:8501 已在跑）
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
    time.sleep(11)

    def page_text():
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

    def goto(path):
        cdp.call("Page.navigate", {"url": "http://localhost:8501" + path}, timeout=60)
        time.sleep(7)

    def current_path():
        return cdp.call("Runtime.evaluate",
                        {"expression": "location.pathname", "returnByValue": True},
                        timeout=40).get("result", {}).get("value")

    def click_button(text):
        js = ("(function(){var bs=[].slice.call(document.querySelectorAll('button'));"
              f"var el=bs.filter(function(e){{return e.innerText.trim().indexOf('{text}')>=0;}})[0];"
              "if(!el) return 'not-found'; el.click(); return 'clicked';})()")
        r = cdp.call("Runtime.evaluate", {"expression": js, "returnByValue": True},
                     timeout=40).get("result", {}).get("value")
        time.sleep(7)
        return r

    checks = []
    t = page_text()
    checks.append(("今日页有流程条 ①找岗", "① 找岗" in t))
    checks.append(("今日页有流程条 ④有回应", "④ 有回应" in t))
    checks.append(("今日页有今日投递目标", "今天 " in t and "家" in t))

    goto("/jobs")
    t = page_text()
    checks.append(("岗位页有一站式卡片", "一站式" in t))
    checks.append(("一站式含②ATS 简历覆盖", "ATS 简历覆盖" in t))
    checks.append(("一站式含④标记已投", "标记已投" in t))

    # 关键回归：岗位卡片的「🔍 匹配」要真的跳到 /match（原生多页跳转）
    r = click_button("🔍 匹配")
    t = page_text()
    checks.append(("点匹配按钮跳到 /match",
                   r == "clicked" and current_path() == "/match"))
    checks.append(("跳转后页面是匹配分析", "匹配分析" in t))
    checks.append(("跳转后无 Traceback/StreamlitAPIException",
                   "Traceback" not in t and "StreamlitAPIException" not in t))

    goto("/distill")
    t = page_text()
    checks.append(("自我蒸馏页正常", "自我蒸馏" in t))
    goto("/interview")
    t = page_text()
    checks.append(("面试准备页含拷问与陪练",
                   "面试拷问" in t and "分身陪练" in t))

    goto("/resume")
    t = page_text()
    checks.append(("简历页无 Traceback", "Traceback" not in t))
    checks.append(("简历来源三选一在简历页", "问答式生成一份" in t))

    cdp.close()
    ok = 0
    for cname, good in checks:
        print(("✅ " if good else "❌ ") + cname)
        ok += 1 if good else 0
    print(f"\n{ok}/{len(checks)} 通过")


if __name__ == "__main__":
    main()
```

## ===== offeragent/test_grab_error.py（38 行）=====

```python
# -*- coding: utf-8 -*-
"""抓某个页面的报错原文。"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import browser_fetch as bf  # noqa: E402
from job_sources import html_to_text  # noqa: E402


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "岗位"
    if not bf.launch(headless=True):
        raise SystemExit("edge fail")
    ws = bf._new_tab("http://localhost:8501")
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    time.sleep(11)
    click = ("(function(){var ls=[].slice.call(document.querySelectorAll('label'));"
             f"var el=ls.filter(function(e){{return e.innerText.trim().indexOf('{label}')>=0;}})"
             ".filter(function(e){return e.innerText.trim().length<8;})[0];"
             "if(!el) return 'not-found'; el.click(); return 'clicked';})()")
    cdp.call("Runtime.evaluate", {"expression": click, "returnByValue": True}, timeout=40)
    time.sleep(8)
    html = cdp.call("Runtime.evaluate", {
        "expression": "document.documentElement.outerHTML",
        "returnByValue": True}, timeout=40).get("result", {}).get("value") or ""
    text = html_to_text(html)
    i = text.find("Traceback")
    print(text[max(0, i - 200): i + 1500] if i >= 0 else "没找到 Traceback")
    cdp.close()


if __name__ == "__main__":
    main()
```

## ===== offeragent/test_my_resume_page.py（93 行）=====

```python
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
    time.sleep(7)
    mine_html = cdp.call("Runtime.evaluate", {
        "expression": "document.documentElement.outerHTML",
        "returnByValue": True}, timeout=60).get("result", {}).get("value") or ""
    mine = html_to_text(mine_html)
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
        ("预览样式被隔离（带作用域前缀）",
         any(s in mine_html for s in [".oa-pv-classic-grid .page",
                                      ".oa-pv-classic .page"])),
        ("有放大整页预览", "放大看" in mine),
        ("有下载 HTML 按钮", "下载这份 HTML" in mine),
        ("提示了命令行出 PDF", "make_resume_pdf.py" in mine),
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
```

## ===== offeragent/test_nav_structure.py（122 行）=====

```python
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
```

## ===== offeragent/test_ocr.py（54 行）=====

```python
# -*- coding: utf-8 -*-
"""测 OCR：生成一张带中文的图片，再用 RapidOCR 识别回来。"""
import sys
from pathlib import Path

HERE = Path(__file__).parent


def make_image(path: Path) -> str:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (900, 260), "white")
    d = ImageDraw.Draw(img)
    font = None
    for cand in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
                 r"C:\Windows\Fonts\simsun.ttc"]:
        if Path(cand).exists():
            try:
                font = ImageFont.truetype(cand, 34)
                break
            except Exception:
                continue
    lines = ["余剑 南京邮电大学 网络工程 2027届",
             "项目：RAG 知识库问答系统（已上线）",
             "top-1/3/5 = 75% / 83% / 92%",
             "技能：Python Chroma FastAPI"]
    for i, t in enumerate(lines):
        d.text((30, 25 + i * 58), t, fill="black", font=font)
    img.save(path)
    return "\n".join(lines)


def main():
    tmp = HERE / "data" / "ocr_test.png"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    truth = make_image(tmp)
    print("原图文字：")
    print(truth)
    try:
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        result, _ = engine(str(tmp))
        text = "\n".join(x[1] for x in (result or []))
        print("\nOCR 识别结果：")
        print(text)
        hits = sum(1 for kw in ["南京邮电大学", "网络工程", "RAG", "Python", "83"]
                   if kw in text)
        print(f"\n关键信息命中 {hits}/5")
    except Exception as e:
        print("\nOCR 失败：", type(e).__name__, str(e)[:200])


if __name__ == "__main__":
    main()
```

## ===== offeragent/test_ref_links.py（30 行）=====

```python
# -*- coding: utf-8 -*-
"""检查要推荐的参考链接能不能打开。"""
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

LINKS = [
    ("shadcn 主题", "https://ui.shadcn.com/themes"),
    ("shadcn 后台示例", "https://ui.shadcn.com/examples/dashboard"),
    ("Tailwind 色板", "https://tailwindcss.com/docs/colors"),
    ("Radix 配色系统", "https://www.radix-ui.com/colors"),
    ("Linear", "https://linear.app/"),
    ("Tremor 仪表盘", "https://tremor.so/"),
    ("Streamlit 官方画廊", "https://streamlit.io/gallery"),
    ("streamlit-shadcn-ui demo", "https://streamlit-shadcn-ui.streamlit.app/"),
    ("Reactive Resume", "https://rxresu.me/"),
    ("OpenResume", "https://www.open-resume.com/"),
    ("Material 3 配色", "https://m3.material.io/styles/color/system/overview"),
    ("Coolors 配色器", "https://coolors.co/"),
]

if __name__ == "__main__":
    for name, url in LINKS:
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            print(f"{'OK ' if r.status_code == 200 else str(r.status_code):<4} {name:<26} {url}")
        except Exception as e:
            print(f"ERR  {name:<26} {url}  ({type(e).__name__})")
```

## ===== offeragent/test_resume_clean.py（61 行）=====

```python
# -*- coding: utf-8 -*-
"""简历文本清洗 + 问答式生成（含照片题）的验收。

跑法：python offeragent\test_resume_clean.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from resume_clean import clean, has_junk          # noqa: E402
import resume_builder                              # noqa: E402

JUNK = (
    "# 余剑\n\n"
    "项目：file:///C:/Users/29947/Documents/Codex/ai-learning/%E7%AE%80%E5%8E%86/"
    "%E4%BD%99%E5%89%91-%E7%AE%80%E5%8E%86-AI%E5%B\n\n"
    "本机 C:\\Users\\29947\\Documents\\Codex\\ai-learning\\简历\\我的简历.md\n\n"
    "正常内容：top-5 命中率 92%，占比 30%\n"
)


def main():
    checks = []
    out, rep = clean(JUNK)
    checks.append(("识别出乱码", has_junk(JUNK)))
    checks.append(("清洗后无 file://", "file://" not in out))
    checks.append(("清洗后无百分号编码", "%E7%AE%80" not in out))
    checks.append(("清洗后无本机路径", "C:\\Users" not in out))
    checks.append(("正常百分比没被误删", "92%" in out and "30%" in out))
    checks.append(("清洗报告有条目", len(rep) >= 2))

    # 问答式生成：照片题必须在题目列表里，且位置合理
    keys = [k for k, _, _ in resume_builder.QUESTIONS]
    checks.append(("有照片这一题", "photo" in keys))
    checks.append(("照片题在联系方式之后", keys.index("photo") > keys.index("contact")))
    checks.append(("题目总数 ≥ 13", len(keys) >= 13))

    # 答案里粘贴路径会被自动清洗
    st = {"answers": {}, "idx": 0}
    resume_builder.answer(st, "file:///C:/x/%E7%AE%80%E5%8E%86/ abc")
    checks.append(("答案里的路径被清洗", "file://" not in st["answers"]["name"]))

    ok = 0
    for name, good in checks:
        print(("✅ " if good else "❌ ") + name)
        ok += 1 if good else 0
    print(f"\n{ok}/{len(checks)} 通过")

    # 恢复问答状态，别把测试答案留在正式文件里
    resume_builder.save({"answers": {}, "idx": 0})


if __name__ == "__main__":
    main()
```

## ===== offeragent/test_resume_preview.py（123 行）=====

```python
# -*- coding: utf-8 -*-
"""简历模板预览的验收：三套模板有没有被裁 / 留大片空白，照片样式有没有生效。

为什么专门测这个：预览用「缩放进 Streamlit」实现，踩过两个坑——
  ① 用 transform: scale 缩放：容器按未缩放高度撑开 → 缩略图下面一大片空白
  ② 作用域 class 带了点（class=".oa-pv-classic"）→ 预览样式全失效，
     照片按原图 600x800 撑开，看起来就是"排版乱 + 图片不对"

这个脚本直接量 DOM：容器高度 vs 内容视觉高度、页脚在不在框内、照片渲染尺寸。

跑法：python offeragent/test_resume_preview.py（需要 localhost:8501 在跑）
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

# 每套模板打印态的照片尺寸（CSS 里写死的），用来验证 CSS 真的生效了
PHOTO_RULE = {"classic": (104, 140), "sidebar": (120, 158), "compact": (96, 128)}

MEASURE_JS = """
(function(){
  function measure(wrap){
    var inner = wrap.firstElementChild;
    var wr = wrap.getBoundingClientRect();
    var ir = inner.getBoundingClientRect();
    var foot = inner.querySelector('.foot');
    var fr = foot ? foot.getBoundingClientRect() : null;
    return {
      cls: wrap.className,
      zoom: getComputedStyle(inner).zoom,
      wrap_h: Math.round(wr.height),
      inner_visual_h: Math.round(ir.height),
      blank: Math.round(wr.height - ir.height),
      clipped: Math.round(ir.height) > Math.round(wr.height) + 2,
      foot_visible: fr ? (fr.bottom <= wr.bottom + 2) : null
    };
  }
  var out = {tpls: {}, photos: []};
  ['classic','sidebar','compact'].forEach(function(t){
    // 类名现在带实例后缀（-grid / -zoom），按前缀选
    var wraps = [].slice.call(document.querySelectorAll('[class^="oa-pv-wrap-' + t + '"]'));
    out.tpls[t] = wraps.map(measure);
  });
  document.querySelectorAll('img[alt="照片"]').forEach(function(im){
    var r = im.getBoundingClientRect();
    out.photos.push({w: Math.round(r.width), h: Math.round(r.height),
                     natW: im.naturalWidth, natH: im.naturalHeight,
                     loaded: im.complete && im.naturalWidth > 0});
  });
  return JSON.stringify(out);
})()
"""


def main():
    if not bf.launch(headless=True):
        raise SystemExit("Edge 启动失败")
    ws = bf._new_tab("http://localhost:8501/resume")
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    cdp.call("Emulation.setDeviceMetricsOverride", {
        "width": 1500, "height": 1100, "deviceScaleFactor": 1, "mobile": False})
    time.sleep(15)
    raw = cdp.call("Runtime.evaluate", {"expression": MEASURE_JS, "returnByValue": True},
                   timeout=60).get("result", {}).get("value")
    cdp.close()
    d = json.loads(raw)

    bad = []
    print("== 每套模板的每个预览块（缩略 + 放大） ==")
    for t, items in d["tpls"].items():
        if not items:
            print(f"❌ {t}: 没找到预览容器")
            bad.append(f"{t}:容器缺失")
            continue
        for i, m in enumerate(items, 1):
            head = f"{t}#{i}(zoom={m['zoom']})"
            if m["clipped"]:
                print(f"❌ {head} 被裁：内容 {m['inner_visual_h']} > 容器 {m['wrap_h']}")
                bad.append(f"{t}#{i}:被裁")
            elif m["blank"] > 24:
                print(f"❌ {head} 留白 {m['blank']}px（容器 {m['wrap_h']} > 内容 "
                      f"{m['inner_visual_h']}）")
                bad.append(f"{t}#{i}:留白")
            elif m["foot_visible"] is False:
                print(f"❌ {head} 页脚不可见（应显示到脚注）")
                bad.append(f"{t}#{i}:页脚不可见")
            else:
                print(f"✅ {head} 容器 {m['wrap_h']}px = 内容 {m['inner_visual_h']}px，页脚可见")

    print()
    print("== 照片（CSS 生效的话应该是 模板尺寸 × zoom） ==")
    if not d["photos"]:
        print("ℹ️ 预览里没有照片（本机 简历/照片.jpg 不存在）——放一张再测更准")
    for p in d["photos"]:
        ratio = round(p["h"] / p["w"], 3) if p["w"] else 0
        ok = p["loaded"] and 1.3 < ratio < 1.4 and p["w"] < 200
        print(("✅ " if ok else "❌ ")
              + f"{p['w']}x{p['h']}（原图 {p['natW']}x{p['natH']}，比例 {ratio}）")
        if not ok:
            bad.append("照片尺寸不对")

    print()
    if bad:
        print("❌ 有问题：", bad)
        return 1
    print("✅ 三套模板预览都完整、照片样式生效")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## ===== offeragent/test_source_yield.py（68 行）=====

```python
# -*- coding: utf-8 -*-
"""岗位数为什么这么少？——用真实抓取对比「改造前 / 改造后」的过滤逻辑。

跑法：python offeragent/test_source_yield.py
说明：需要联网。牛客不需要登录；BOSS 需要本机登录过（没登录会报未登录，属正常）。
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

import job_sources as js  # noqa: E402


def old_logic_count(rows, kw, city):
    """旧逻辑：关键词或城市不命中就直接丢掉。"""
    kws = [k.lower() for k in js.split_terms(kw)]
    cities = js.split_terms(city)
    kept = []
    for r in rows:
        blob = f"{r.get('title', '')} {r.get('extra', '')} {r.get('city', '')}".lower()
        if kws and not any(k in blob for k in kws):
            continue
        if cities and not any(c in blob for c in cities):
            continue
        kept.append(r)
    return kept


def probe(kw, city):
    d = {}
    t0 = time.time()
    try:
        rows = js.search_nowcoder(kw, city, diag=d)
    except Exception as e:
        print(f"关键词={kw!r} 城市={city!r} → 抓取失败：{type(e).__name__} {str(e)[:80]}")
        return
    old = old_logic_count(rows, kw, city)
    print(f"关键词={kw!r} 城市={city!r}")
    print(f"   页面结构化岗位 {d.get('raw')} 条 → 现在返回 {len(rows)} 条"
          f"（旧逻辑只剩 {len(old)} 条）｜用时 {time.time() - t0:.1f}s")
    for r in rows[:3]:
        print(f"     · {r['title'][:22]:<24} {r['city']:<8} 命中 {r.get('match_hits')}")


def main():
    print("== 牛客：同一份数据，新旧过滤逻辑对比 ==")
    probe("AI", "南京")
    probe("AI", "")
    probe("AI 算法 大模型", "南京 上海")
    print()
    print("== 三个源合起来跑一遍（看 by_source / diag） ==")
    res = js.search_all("AI", "南京", ask_model=None)
    print("各平台条数：", res["by_source"])
    print("失败原因：", res["errors"])
    print("诊断：", res["diag"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## ===== offeragent/test_sources.py（44 行）=====

```python
# -*- coding: utf-8 -*-
"""测试几个公开岗位源能不能抓（判断阶段 4 该接哪些源）。"""
import re
import sys

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
H = {"User-Agent": UA}

SOURCES = [
    ("实习僧", "https://www.shixiseng.com/interns?keyword=AI&city=%E5%8D%97%E4%BA%AC"),
    ("应届生求职网", "https://s.yingjiesheng.com/search.php?word=AI&sort=score"),
    ("牛客实习中心", "https://www.nowcoder.com/jobs/intern/center"),
    ("BOSS直聘搜索", "https://www.zhipin.com/web/geek/job?query=AI&city=101190100"),
    ("南大就业网", "https://job.nju.edu.cn/"),
    ("南邮就业网", "https://jiuye.njupt.edu.cn/"),
]


def probe(name: str, url: str):
    try:
        r = requests.get(url, headers=H, timeout=20)
        text = r.text
        has_kw = "实习" in text or "招聘" in text
        # 粗略数一下有没有像岗位链接的东西
        links = len(re.findall(r'href="[^"]*(?:job|intern|position)[^"]*"', text, re.I))
        print(f"{name:<14} HTTP {r.status_code} | {len(text):>7} 字节 | "
              f"含关键词 {has_kw} | 疑似岗位链接 {links}")
        return r.status_code == 200 and links > 0
    except Exception as e:
        print(f"{name:<14} 失败: {type(e).__name__}: {str(e)[:60]}")
        return False


if __name__ == "__main__":
    print("探测公开岗位源（能不能直接抓）：\n")
    ok = []
    for name, url in SOURCES:
        if probe(name, url):
            ok.append(name)
    print("\n可直接抓的源：", ok if ok else "无")
```

## ===== offeragent/test_sources_live.py（68 行）=====

```python
# -*- coding: utf-8 -*-
"""联网搜岗实测：牛客（结构化解析）+ 实习僧（大模型抽取）。BOSS 需要先登录，跳过。"""
import re
import sys
from pathlib import Path

import requests

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import job_sources  # noqa: E402

SECRETS = HERE / ".streamlit" / "secrets.toml"
API_URL = "https://api.deepseek.com/chat/completions"


def load_key() -> str:
    m = re.search(r'DEEPSEEK_API_KEY\s*=\s*"([^"]+)"',
                  SECRETS.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("没找到 API Key")
    return m.group(1)


def make_ask(key):
    def ask(prompt: str) -> str:
        r = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json={"model": "deepseek-chat",
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=180,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    return ask


def show(name, jobs):
    print(f"\n【{name}】拿到 {len(jobs)} 条")
    for j in jobs[:5]:
        print(f"  - {j['title']} | {j['company']} | {j['city']} | {j['salary']}")
        if j.get("extra"):
            print(f"      {j['extra']}")
        if j.get("url"):
            print(f"      {j['url']}")


if __name__ == "__main__":
    key = load_key()
    ask = make_ask(key)
    try:
        show("牛客 · 关键词 AI", job_sources.search_nowcoder("AI", ""))
    except Exception as e:
        print("牛客失败:", type(e).__name__, str(e)[:120])
    try:
        show("实习僧 · AI / 南京", job_sources.search_shixiseng("AI", "南京", ask))
    except Exception as e:
        print("实习僧失败:", type(e).__name__, str(e)[:120])
    print("\n" + "=" * 70)
    print("多平台合并（牛客 + 实习僧 + BOSS）")
    res = job_sources.search_all("AI", "南京", ask_model=ask)
    print("各平台结果：", res["by_source"])
    for k, v in res["errors"].items():
        print(f"  失败 {k}：{v[:100]}")
    show("合并去重后", res["jobs"])
```

## ===== offeragent/test_sources_parse.py（87 行）=====

```python
# -*- coding: utf-8 -*-
"""看实习僧 / 牛客 的页面里，岗位数据藏在哪个 JSON 里。"""
import json
import re

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
H = {"User-Agent": UA}


def peek(d, depth=0, path="$"):
    if depth > 3:
        return
    if isinstance(d, dict):
        for k, v in list(d.items())[:8]:
            if isinstance(v, (dict, list)):
                print("    " + "  " * depth + f"{path}.{k} ({type(v).__name__}, {len(v)})")
                peek(v, depth + 1, f"{path}.{k}")
            else:
                print("    " + "  " * depth + f"{path}.{k} = {str(v)[:40]}")
    elif isinstance(d, list) and d:
        peek(d[0], depth + 1, f"{path}[0]")


def show(name, url, patterns):
    print("=" * 70)
    print(name)
    try:
        r = requests.get(url, headers=H, timeout=25)
        text = r.text
    except Exception as e:
        print("  请求失败:", type(e).__name__)
        return
    for label, pat in patterns:
        m = re.search(pat, text, re.S)
        if not m:
            print(f"  [{label}] 没找到")
            continue
        raw = m.group(1)
        print(f"  [{label}] 命中，长度 {len(raw)}")
        try:
            peek(json.loads(raw))
        except Exception as e:
            print("    JSON 解析失败:", str(e)[:80])
            print("    预览:", raw[:200])


if __name__ == "__main__":
    # 牛客：看岗位字段结构
    print("=" * 70)
    print("牛客 jobList 第一条的字段")
    try:
        r = requests.get("https://www.nowcoder.com/jobs/intern/center",
                         headers=H, timeout=25)
        m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;', r.text, re.S)
        data = json.loads(m.group(1))
        jobs = data["store"]["interCenter"]["jobList"]
        print(f"  共 {len(jobs)} 条，第一条字段：")
        for k, v in jobs[0].items():
            print(f"    {k} = {str(v)[:60]}")
        print("\n  前三条标题：")
        for j in jobs[:3]:
            print("   -", j.get("jobName"), "|", j.get("companyName"), "|",
                  j.get("cityName"), "|", j.get("salaryDesc") or j.get("salaryMin"))
    except Exception as e:
        print("  失败:", type(e).__name__, str(e)[:100])

    # 实习僧：找链接和 JSON 脚本
    print("\n" + "=" * 70)
    print("实习僧页面结构探测")
    try:
        r = requests.get("https://www.shixiseng.com/interns?keyword=AI&city=%E5%8D%97%E4%BA%AC",
                         headers=H, timeout=25)
        t = r.text
        print("  状态", r.status_code, "长度", len(t))
        ids = re.findall(r'<script[^>]*id="([^"]+)"', t)
        print("  script id：", ids[:10])
        hrefs = re.findall(r'href="(/intern/[^"]+)"', t)
        print(f"  /intern/ 链接数：{len(hrefs)}，前三个：{hrefs[:3]}")
        if not hrefs:
            hrefs2 = re.findall(r'href="([^"]*intern[^"]*)"', t)
            print(f"  含 intern 的链接数：{len(hrefs2)}，前三个：{hrefs2[:3]}")
    except Exception as e:
        print("  失败:", type(e).__name__, str(e)[:100])
```

## ===== offeragent/test_talk.py（97 行）=====

```python
# -*- coding: utf-8 -*-
"""
话术对比测试：同一个岗位，用旧提示词 vs 新提示词各生成一条，直接看差别。

跑法：python offeragent\test_talk.py [岗位名]
默认岗位：weilan_ai
"""
import re
import sys
from pathlib import Path

import requests

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
JDS_DIR = DATA_DIR / "jds"
SECRETS = HERE / ".streamlit" / "secrets.toml"

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

sys.path.insert(0, str(HERE))
from prompts import build_talk_prompt, check_talk, generate_talk  # noqa: E402


def load_api_key() -> str:
    text = SECRETS.read_text(encoding="utf-8")
    m = re.search(r'DEEPSEEK_API_KEY\s*=\s*"([^"]+)"', text)
    if not m:
        raise SystemExit("没在 .streamlit/secrets.toml 里找到 DEEPSEEK_API_KEY")
    return m.group(1)


def ask(prompt: str, *materials: str, key: str, temperature: float = 0.8) -> str:
    content = prompt + "\n\n" + "\n\n".join(
        f"【材料 {i + 1}】\n{m}" for i, m in enumerate(materials)
    )
    r = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": [{"role": "user", "content": content}],
              "temperature": temperature},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


# v2 的旧提示词（原样搬过来，用于对比）
OLD_PROMPT_TALK = """你是资深求职顾问兼文案。根据「画像」与「岗位 JD」，写一条发给 HR 的中文打招呼语。
铁律：
1. 像真人微信聊天，自然口语、有温度，绝不像简历复读机、绝不堆列表
2. 不写"您好！我是XX大学XX专业XX届学生"这种模板开头；改为自然切入（如"看到贵司在招XX方向的实习…"）
3. 结构：一句自然开场 → 一句最有说服力的相关经历（带 1 个量化数字，自然融入）→ 一句表达兴趣/意愿
4. 长度 60~100 字
5. 直接输出正文，不要标题、称呼、落款、emoji"""


def main():
    job = sys.argv[1] if len(sys.argv) > 1 else "weilan_ai"
    jd_path = JDS_DIR / f"{job}.txt"
    if not jd_path.exists():
        raise SystemExit(f"找不到 JD：{jd_path}")

    key = load_api_key()
    profile = (DATA_DIR / "profile.md").read_text(encoding="utf-8")
    jd = jd_path.read_text(encoding="utf-8")

    print(f"岗位：{job}")
    print("=" * 70)

    print("\n【旧版提示词生成】\n")
    old = ask(OLD_PROMPT_TALK, profile, jd, key=key)
    print(old)
    old_hits = check_talk(old)
    print(f"\n禁用词命中：{old_hits if old_hits else '无'}")

    print("\n" + "=" * 70)
    print("\n【新版 · BOSS 打招呼（含自动校验重写）】\n")
    new, new_hits = generate_talk(
        lambda p, *m: ask(p, *m, key=key), "boss", profile, jd
    )
    print(new)
    print(f"\n禁用词命中：{new_hits if new_hits else '无（校验通过）'}")

    print("\n" + "=" * 70)
    print("\n【新版 · 邮件/网申自我介绍】\n")
    mail, mail_hits = generate_talk(
        lambda p, *m: ask(p, *m, key=key), "email", profile, jd
    )
    print(mail)
    print(f"\n禁用词命中：{mail_hits if mail_hits else '无（校验通过）'}")


if __name__ == "__main__":
    main()
```

## ===== offeragent/test_theme_shots.py（78 行）=====

```python
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
```

## ===== offeragent/test_theme_verify.py（44 行）=====

```python
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
```

## ===== offeragent/test_twin_portal.py（55 行）=====

```python
# -*- coding: utf-8 -*-
"""公开数字名片页验收（?twin=1）：照片位、分享链接、问数字人、两个信息页签。

跑法：python offeragent\test_twin_portal.py（需要 localhost:8501 已在跑）
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
    ws = bf._new_tab("http://localhost:8501/?twin=1")
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    time.sleep(15)
    html = cdp.call("Runtime.evaluate", {
        "expression": "document.documentElement.outerHTML",
        "returnByValue": True}, timeout=60).get("result", {}).get("value") or ""
    text = html_to_text(html)
    cdp.close()

    checks = [
        ("名片头有姓名", "余剑" in text),
        ("有职位定位", "AI 应用开发实习生" in text),
        ("有学校 / 届别标签", "南京邮电大学" in text and "2027" in text),
        ("照片位存在（图或占位字）", "余" in text),
        ("有分享/转载入口", ("分享" in text) or ("转载" in text)),
        ("有「问数字人」主入口", "有问题直接问他" in text),
        ("宣传语含 AI 可能有误声明", "以本人沟通为准" in text),
        ("有「我是谁」页签", "我是谁" in text),
        ("有「项目证据」页签", "项目证据" in text),
        ("提到 RAG 项目", "RAG" in text),
        ("没有 Traceback", "Traceback" not in text),
    ]
    ok = 0
    for cname, good in checks:
        print(("✅ " if good else "❌ ") + cname)
        ok += 1 if good else 0
    print(f"\n{ok}/{len(checks)} 通过")


if __name__ == "__main__":
    main()
```

## ===== offeragent/test_undefined_names.py（229 行）=====

```python
# -*- coding: utf-8 -*-
"""静态扫一遍：找出「用了但从没定义」的变量名（云端 NameError 的根因）。

为什么需要：线上就是靠这类错误白屏的——page_applications 引用了被删掉的
applied_jobs，浏览器验收脚本没点到那个分支所以没发现。这个脚本不跑页面，秒出结果。

跑法：python offeragent/test_undefined_names.py
"""
import ast
import builtins
import sys
from pathlib import Path

HERE = Path(__file__).parent
TARGETS = sorted(HERE.glob("*.py"))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ALLOW = set(dir(builtins)) | {"st", "self", "cls", "__name__", "__file__"}


SCOPE = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


def _body_of(scope) -> list:
    if isinstance(scope, ast.Lambda):
        return [scope.body]
    return list(getattr(scope, "body", []) or [])


def _args_of(scope) -> set:
    a = getattr(scope, "args", None)
    if not a:
        return set()
    out = {x.arg for x in (a.posonlyargs + a.args + a.kwonlyargs)}
    if a.vararg:
        out.add(a.vararg.arg)
    if a.kwarg:
        out.add(a.kwarg.arg)
    return out


def _child_scopes(body) -> list:
    """这个作用域里直接嵌套的内层作用域（不再往下钻）。"""
    out = []

    def rec(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, SCOPE):
                out.append(child)
                continue
            rec(child)

    for stmt in body:
        if isinstance(stmt, SCOPE):
            out.append(stmt)
            continue
        rec(stmt)
    return out


def _local_defs(body) -> set:
    """这个作用域里定义过的名字（含内层函数名，但不下沉进内层函数体）。"""
    names = set()

    def visit(node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
            return
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, ast.alias):
            names.add((node.asname or node.name).split(".")[0])
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.Lambda):
            names.update(_args_of(node))
        for child in ast.iter_child_nodes(node):
            visit(child)

    for stmt in body:
        visit(stmt)
    return names


def _own_loads(scope) -> list:
    """本作用域里读取的 Name（跳过内层作用域的函数体）。"""
    out = []

    def rec(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, SCOPE):
                continue
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                out.append(child)
            rec(child)

    for stmt in _body_of(scope):
        if isinstance(stmt, SCOPE):
            continue
        if isinstance(stmt, ast.Name) and isinstance(stmt.ctx, ast.Load):
            out.append(stmt)
        rec(stmt)
    return out


def _walk(scope, outer: set, problems: list):
    body = _body_of(scope)
    avail = outer | _local_defs(body) | _args_of(scope)
    name = getattr(scope, "name", "<lambda>")
    for node in _own_loads(scope):
        if node.id not in avail and node.id not in ALLOW:
            problems.append((name, node.id, node.lineno))
    for child in _child_scopes(body):
        _walk(child, avail, problems)


def _collect_assigns(body, names, depth=0):
    """收集容器内（try/if/with/for）的赋值名，不下钻函数体。"""
    if depth > 2:
        return
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
            continue
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
            continue
        if isinstance(node, (ast.If, ast.Try, ast.With, ast.For, ast.While)):
            _collect_assigns(node.body, names, depth + 1)
            if isinstance(node, ast.Try):
                for h in node.handlers:
                    _collect_assigns(h.body, names, depth + 1)


def _module_top_names(mod_name: str, here: Path, depth: int = 0) -> set:
    """不执行模块，用 ast 收集它顶层定义/导入的名字（处理 import * 误报）。"""
    if depth > 2:
        return set()
    mod_file = here / f"{mod_name}.py"
    if not mod_file.exists():
        return set()
    try:
        tree = ast.parse(mod_file.read_text(encoding="utf-8"))
    except Exception:
        return set()
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            for a in node.names:
                if a.name == "*":
                    names |= _module_top_names(node.module, here, depth + 1)
                else:
                    names.add(a.asname or a.name)
    _collect_assigns(tree.body, names)
    return names


def _star_import_extra(tree, here: Path) -> set:
    """`from X import *` 的源模块顶层名字（静态收集，不执行模块）。"""
    extra = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.ImportFrom) and node.module
                and any(a.name == "*" for a in node.names)):
            extra |= _module_top_names(node.module, here)
    return extra


def check_source(src: str):
    tree = ast.parse(src)
    problems = []
    module_scope = _local_defs(tree.body) | _star_import_extra(tree, HERE)
    for stmt in tree.body:
        if isinstance(stmt, SCOPE):
            _walk(stmt, module_scope, problems)
        else:
            for child in _child_scopes([stmt]):
                _walk(child, module_scope, problems)
    return problems


SELF_TEST = """
def a():
    return never_defined_anywhere


def b():
    ok = 1
    return ok
"""


def main():
    self_hits = check_source(SELF_TEST)
    if not any(n == "never_defined_anywhere" for _, n, _ in self_hits):
        print("❌ 自检失败：这个检查器抓不到明显的未定义名，先别信它的结论")
        return 2
    total = 0
    for p in TARGETS:
        if p.name.startswith("test_") or p.name.startswith("_probe"):
            continue
        try:
            probs = check_source(p.read_text(encoding="utf-8"))
        except SyntaxError as e:
            print(f"❌ {p.name} 语法错误：{e}")
            total += 1
            continue
        for fn, name, line in probs:
            print(f"❌ {p.name}:{line} 函数 {fn}() 用了未定义的 `{name}`")
            total += 1
    print(f"\n发现 {total} 处可疑未定义名" if total
          else "✅ 没有发现未定义的变量名（自检也通过）")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
```

## ===== run_tests.py（98 行）=====

```python
# -*- coding: utf-8 -*-
"""统一测试入口：一键跑通全部离线测试。

用法:
    python run_tests.py            # 跑全部离线测试（跳过 live/网络/API 类）
    python run_tests.py --live     # 连 live/网络/API 类一起跑（会真实调用 API，费额度）

规则:
    - 文件名含 "live" 或 "_live" 的测试默认跳过（需真实网络/API key）
    - 单测失败不中断，全部跑完统一汇总
    - 退出码: 0=全过, 1=有失败
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OFFERAGENT = ROOT / "offeragent"
PY = sys.executable

def collect_tests():
    tests = []
    for base in (ROOT, OFFERAGENT):
        for p in sorted(base.glob("test_*.py")):
            if not p.name.startswith("test_"):
                continue
            if p.name.startswith("test_agent.py") and base is not ROOT:
                continue  # 根目录的 test_agent.py 是主回归，避免重复
            tests.append(p)
    return tests

def is_live(p: Path) -> bool:
    return "live" in p.name.lower()

def needs_service(p: Path) -> bool:
    """依赖「本地 Streamlit 服务 + 浏览器」的验收测试（需先手动起 app）。"""
    try:
        src = p.read_text(encoding="utf-8")
    except Exception:
        return False
    return "localhost:8501" in src and "bf.launch" in src

def run_one(p: Path, timeout: int = 300):
    try:
        r = subprocess.run([PY, str(p)], capture_output=True, text=True,
                           timeout=timeout, cwd=str(p.parent))
        ok = r.returncode == 0
        tail = (r.stdout or r.stderr).strip().splitlines()
        tail = "\n".join(tail[-4:]) if tail else "(无输出)"
        return ok, tail
    except subprocess.TimeoutExpired:
        return False, f"超时(>{timeout}s)"
    except Exception as e:  # noqa: BLE001
        return False, f"无法运行: {e}"

def main():
    live = "--live" in sys.argv
    browser = "--browser" in sys.argv
    tests = collect_tests()
    passed, failed, skipped = [], [], []

    print(f"== OfferAgent 测试总入口 ==")
    print(f"发现 {len(tests)} 个测试文件（{'含 live' if live else '跳过 live/网络类'}"
          f"{'，含浏览器验收' if browser else '，跳过浏览器验收'}）\n")

    for p in tests:
        if is_live(p) and not live:
            skipped.append(p)
            print(f"  [跳过] {p.relative_to(ROOT)} (live/网络类，加 --live 才跑)")
            continue
        if needs_service(p) and not browser:
            skipped.append(p)
            print(f"  [跳过] {p.relative_to(ROOT)} (需本地 app 服务 + 浏览器，加 --browser 才跑)")
            continue
        ok, tail = run_one(p)
        name = p.relative_to(ROOT)
        if ok:
            passed.append(p)
            print(f"  [通过] {name}")
        else:
            failed.append(p)
            print(f"  [失败] {name}")
            for line in tail:
                print(f"           {line}")

    print("\n== 汇总 ==")
    print(f"  通过: {len(passed)}  失败: {len(failed)}  跳过: {len(skipped)}  (共 {len(tests)})")
    if failed:
        print("\n失败清单:")
        for p in failed:
            print(f"  - {p.relative_to(ROOT)}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## ===== offeragent/README.md（184 行）=====

```markdown
# 🎯 OfferAgent · 求职智能体

> 一个会"先认识自己、再找工作"的 AI 求职工作台：自我蒸馏 → 岗位匹配 → 投递话术 → 半自动投递 → 面试拷问 → 复盘进化。
> 附带**公开数字人名片页**：HR 知情访问，AI 分身用真实画像回答问题。
>
> 参考 srbhr/Resume-Matcher 的架构思路 + Liyaxuxu/icebreaker-hr 的话术经验，用 Streamlit 实现；核心差异化（自我蒸馏、数字分身、复盘闭环）为自研。

## 三个核心理念

1. **只挑不编**：所有生成内容只能来自你的真实素材，进行中的项目不许升级描述
2. **生成归工具，发送归人**：程序不替你发送任何消息（平台风控 + 诚信红线），最后一眼和最后一下由你完成
3. **有据可查**：每个界面都写清楚数据从哪来、算出来的分是什么意思

## 🤖 Agent 化引擎（2026-09 新增）

> 🎯 **批量打分排序**：`batch_score.py`（项目根）——分派「岗位分析师」子 Agent 对全部待投岗位评估质量 + 算匹配度，回填 `match_score/verdict` 到 meta.json，输出按匹配分从高到低的投递优先级（实测 13 岗：AI 应用开发可转正 88 > 蔚蓝 86 > Calix 82 > 小米/南大/三和 78 > 蚂蚁/纷子/境瞳/产品经理 72 > 亚信/彩讯 62；彩讯已排除）；Web 端「数据与日志」页也有「⚡ 批量打分」按钮。
>
> 📐 **架构图**：完整系统架构（画像地基 → 单 Agent 引擎 → 多 Agent 协作 → 落盘闭环）见 ![架构图](docs/architecture.png)（SVG 源文件：docs/architecture.svg）。

把"人点按钮的应用"升级为**模型自主规划工具链的真 Agent**（`offer_agent_core.py` + `offer_agent_tools.py`）：

```
用户给一个目标 → 模型自主规划 → 依次调用工具 → 根据每个结果决定下一步 → 执行类动作停在人确认
```

- **工具注册表**：8 个工具统一 schema（assess_job / split_jd / match_job / generate_talk / check_talk / funnel / needs_followup / open_application🔒），全部复用本项目现有函数，不新造业务逻辑
- **状态对象 + ReAct 循环**：messages + 记忆 + trace + 预算上限（防死循环）
- **安全边界**：执行类动作（打开投递链接）标记 `human_confirm`，必须停在用户确认——"发送前那一下永远由人做"不变
- **可观测**：每步工具调用写入 trace，可导出复盘
- **实测**：`python agent_cli.py` 用真实岗位（Calix）跑通全链：质量评估 100 → JD 拆解 → 匹配 88% → 话术（禁用词 0）→ 校验 → 停在投递确认

> 命令行演示（项目根目录）：`python agent_cli.py --job <岗位>`（默认 calix）/ `--confirm`（模拟确认）
>
> **Web 端已接入**：主应用侧边栏「找工作 → Agent 流程（引擎演示）」——选岗位 → 一键跑完整工具链 → 看 trace → 确认投递。
>
> **Agent 化增强（2026-09 第二批）**：
> - **多岗位泛化**：已跑通 ant_agent（蚂蚁，match 78%）/ xiaomi_agent（小米，match 72%）/ calix（88%）；`--job <名>` 换岗即用
> - **链接失效检测**：open_application 执行前自动核验 URL——404/410 或无法访问 → 不打开、提示"不要投空"（实测：calix 占位链接 404 被拦，蚂蚁真实链接 200 放行）
> - **trace 落盘**：每次运行写入 `data/agent_logs.jsonl`（时间/岗位/公司/match_score/步数/是否确认/trace 全文），可复盘可统计
> - **Web 商业化升级（2026-09-29）**：Agent 页加岗位信息卡 + 投递日志表 + 「一键批量跑全部待投岗位」；数据页加「Agent 运行洞察」（匹配分分布图 + 运行记录）；默认主题切换为 D 精修浅色版
> - **引擎三升级（2026-09-29 第三批）**：
>   - **匹配分门禁**：`GATE_SCORE=60`——match_job 返回 `verdict`（建议投 / 不建议投），日志带裁决列，低于 60 分自动提示别投空
>   - **记忆落盘 SQLite**：`agent_memory.py` v2，`Memory(db_path=...)` 把事实/对话写入 `data/memory.db`，**跨会话记住用户**（无 db_path 保持纯内存，向后兼容）
>   - **多 Agent 协作**：`offer_agent_multi.py`——主管（Supervisor，唯一工具 dispatch）+ 子 Agent（岗位分析师：assess/split/match；话术专家：generate/check；**投递复盘员：funnel/needs_followup**，独立状态与角色提示词）；CLI `--multi` 跑通（Calix 匹配 82、门禁建议投、话术截断自动重派自纠错、复盘员漏斗分析端到端通过）；Web 批量处理跟随运行模式（单/多 Agent）；投递动作（open_application）不在子 Agent 工具集，永远人确认

## 核心功能

| 页面 | 功能 |
| --- | --- |
导航用 Streamlit 原生多页（`st.navigation`）：**每页有真实 URL**，可刷新、可前进后退、可分享链接；侧边栏按分区显示。一共 10 页——刻意不超过 10，因为 Streamlit 侧边栏超过 10 个就会把剩下的折叠成「View more」。

| 分区 | 页面（URL） | 干什么 |
| --- | --- | --- |
| 主线 | 今天（行动 + 数据）`/` | 待投清单逐条推进；第二个页签是漏斗 / 趋势 / 岗位排名 / 日报——**统计口径只有这一处** |
| 找工作 | 岗位库 `/jobs` · 匹配分析 `/match` · 简历 `/resume` · 投递台 `/apply` · 投递记录 `/records` | 一条链走完：多渠道搜岗 → 匹配 → 简历（内容 + 三套模板 + 照片 + ATS 覆盖检查）→ **唯一的话术生成入口**（批量 / 单条）→ 记录与跟进 |
| 我的 | 自我蒸馏 `/distill` · 面试准备 `/interview` | 画像 → 面试拷问 → 分身陪练 → 复盘写回画像（一个闭环，同页三个页签） |
| 对外 | 名片与分享 `/show` | 对外素材自检、公开名片链接（`?twin=1` 免密）、简历 PDF 导出 |
| 其它 | 设置 `/settings` | API Key / 模型（默认 flash）/ 每日投递目标 / 每日调用限额 / 访问密码 / 主题 |

**两条硬规则**：一个动作只有一个入口（话术只在「投递台」生成，其他地方是「跳过去并定位这条」，跨页跳转用 `st.switch_page`）；同一个数字只有一个出处（统计只在「今天 → 数据与日志」）。

## 亮点细节

- **自我蒸馏（Self-Distill）**：问答式 15 题把真实的你蒸馏成结构化画像 `profile.md`，之后所有环节都基于这份画像，不编造。
- **数字分身名片页**：`/?twin=1` 免密码访问。HR 点进链接即可：看基本盘 → 看项目证据（上线应用 / GitHub / 简历 PDF）→ 直接问分身问题。页面标注"AI 分身基于真实画像，最终以本人沟通为准"。
- **半自动批量投递台**：一键为全部待投岗位生成话术 → 逐条"复制 / 打开 / 保存修改 / 标记已投"。发送那一下永远留给人。
- **话术 v6**：BOSS 极简直接版（"你好，我是 XX 学校 XX 专业学生，2027 届，想投贵公司 XX 岗位，以下是我的简历"）+ 邮件/内推人话版；禁用词 45+ 自动拦截 AI 腔，生成后自动校验。
- **面试拷问**：按 JD 出题 → 逐题点评 → 总评与改进清单；复盘可写回画像，分身越用越准。
- **链接失效检测**：投递前自动重访岗位 URL，404/410 标记失效，避免投空。
- **L1 密码门**：密码 SHA-256 哈希存储（`data/config.json` 或 Secrets `APP_PASSWORD`）。
- **5 套主题**（含深色 Night）。

## 快速开始（本地）

```bash
cd offeragent
pip install -r requirements.txt

# 1) 准备素材：把自己的情况写进 me.txt（姓名/学校/技能/项目/求职目标/硬约束）
# 2) 配置密钥：复制 .streamlit/secrets.toml.example 为 secrets.toml，填入 DEEPSEEK_API_KEY
# 3) 启动
streamlit run offer_agent_app.py
```

打开 `http://localhost:8501` → 先到「我的资料 → 自我蒸馏」生成画像，再去「岗位」加 JD 或从 URL 导入。

## 测试（一键全跑）

```bash
python run_tests.py            # 项目根目录：离线测试全跑（15+ 通过 / 0 失败基线）
python run_tests.py --live     # 连 live/网络/API 类一起跑（真实调 API，费额度）
python run_tests.py --browser  # 连浏览器验收类一起跑（需先本地起 app）
```

覆盖：Agent 引擎回归（22 项）、全部页面 import 扫描（防云端 NameError）、密码门、链接检测、话术校验、简历 ATS、导航结构、云端启动模拟等 26 个测试文件。

## 文档

- `docs/interview_talk.md` —— 面试讲法：8 个可深挖技术点 + 通用应答套路 + 必背数字
- `docs/weekly_ops.md` —— 每周 30 分钟运营流程（让项目喂真实数据）
- `docs/architecture.png` / `.svg` —— 系统架构图

## 部署上线（Streamlit Community Cloud）

1. 把 `offeragent` 目录推到 GitHub（`.gitignore` 已排除 `data/` 与 `.streamlit/secrets.toml`，隐私与密钥不泄露）
2. [share.streamlit.io](https://share.streamlit.io) → GitHub 登录 → New app
   - Repository 选你的仓库；**Main file path 填 `offeragent/offer_agent_app.py`**
3. Advanced settings → Secrets 填两项：

```toml
DEEPSEEK_API_KEY = "sk-你的key"
APP_PASSWORD = "给工作台设的访问密码"
```

4. Deploy → 2 分钟拿到公开链接（**在线地址：_你的 Streamlit Cloud 链接，填到这里_**）
5. 数字名片页：公开链接后加 `/?twin=1`（免密码，供 HR 访问）

> 依赖策略：`requirements.txt` 用 `>=` 下限（不锁死版本）——Streamlit Cloud 每次部署装最新已验证兼容版本，避免锁旧版踩依赖坑。

> 部署版是空数据开始（本地 `data/` 不上传）：首屏先用 me.txt 蒸馏画像，再导入岗位。设计如此——你的求职数据留在本机。

## 架构

```
offeragent/
├── offer_agent_app.py      # Streamlit 主应用（全部页面 + 公开名片页）
├── prompts.py              # 所有提示词集中管理（画像/匹配/建议/话术 v6 + 禁用词 45+）
├── digital_twin.py         # 数字分身（自我介绍/反问/扮演我/复盘/岗位雷达/画像进化）
├── distill*.py             # 自我蒸馏（问答式/填表式）
├── jd_fetcher.py           # JD 抓取（直连优先，r.jina.ai 兜底）
├── job_sources.py          # 岗位源（牛客/实习僧/BOSS，结构化解析 + 浏览器抓取）
├── job_quality.py          # 岗位质量检测
├── company_lookup.py       # 公司信息补全
├── resume_tailor.py        # ATS 简历覆盖检查
├── resume_builder.py       # 简历生成
├── interview_drill.py      # 面试拷问（出题/点评/总评）
├── pipeline.py             # 漏斗/跟进/被拒归因
├── v41.py                  # 增强：批量匹配/链接检测/漏斗图/面试提醒/密码哈希
├── apply_assist.py         # 投递辅助（复制/打开/记录；明确不做全自动）
├── theme.py                # 5 套主题
└── data/                   # 运行数据（本地，git 排除）
    ├── profile.md          # 蒸馏后的画像
    ├── jds/                # 岗位库（JD + meta）
    ├── match_results/      # 匹配报告
    ├── applications.jsonl  # 投递日志
    ├── reviews.jsonl       # 面试复盘
    └── talk_queue.json     # 批量话术队列
```

## 安全与隐私

- 密钥只存在本机 `data/config.json` 或部署 Secrets；`data/` 全目录 git 排除（含 BOSS 登录态 `edge_profile`）
- 密码 SHA-256 哈希，不存明文
- 数字分身只回答画像里的事实，提示词硬规则"没有就直说没有"，不编造
- 不做全自动投递、不做 AI 冒充本人面试（平台风控 + 身份诚信红线）

## 技术栈

Python · Streamlit · DeepSeek API · requests · plotly · pypdf · python-docx · 纯本地数据（无外部数据库）

## 分层架构（2026-09-29 重构）

主入口 offer_agent_app.py 只保留页面编排；业务逻辑按层拆出，可独立测试：

| 模块 | 职责 | 依赖 |
|------|------|------|
| store.py | 数据层：岗位库/简历读写、日志读取、分数对账（单一权威源）、投递防抖 | 纯 Python |
| llm.py | AI 层：Key 解析、每日额度保护、调用、报告解析 | streamlit + requests |
| ui_kit.py | 渲染层：页头/仪表盘/岗位档案/报告卡片/下一步提示 | streamlit + plotly |

- 单一权威源：data/jds/*.meta.json 的 match_score/status 是唯一权威；agent_logs.jsonl 只记事件，历史分数是快照不覆盖岗位库。store.audit_scores() 一键对账，Web 端「数据与日志」页可看。
- 投递防抖：已投岗位禁止重复投递；24 小时内投过也会被拦（store.check_apply_allowed）。

## 数据持久化（Streamlit Cloud 重启不丢数据）

Streamlit Cloud 无持久磁盘，每次重启回到仓库代码。根治方案（sync_data.py）：

1. 建一个私有仓库（如 yjmyp/offeragent-data）
2. GitHub → Settings → Developer settings → Personal access tokens 生成 token（勾 repo 权限）
3. 本地：set GITHUB_PAT=ghp_xxx && python offeragent\sync_data.py push（把 data/ 打包进私有仓库，本地是权威）
4. 云端：Settings → Secrets 填 GITHUB_PAT + DATA_REPO；app 启动检测到岗位库为空会自动 pull 恢复

模板见 .streamlit/secrets.toml.example（含 DAILY_CALL_LIMIT 防刷额度保护）。
```
