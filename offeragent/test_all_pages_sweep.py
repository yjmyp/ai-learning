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
    ("Agent 流程", "/agent"),
    ("数字分身", "/twin"),
    ("公开数字名片", "/?twin=1"),
]
ERR_KWS = ["Traceback", "NameError", "KeyError", "AttributeError", "TypeError",
           "ValueError", "ModuleNotFoundError", "StreamlitDuplicateElementId",
           "UnboundLocalError", "IndexError"]


def read_page(path: str, wait: float = 6.0, attempts: int = 2) -> str:
    """每页独立建 CDP 连接；连接异常时整页重开一次。

    之前所有页面共用一条长连接，Windows 偶发中止 WebSocket（WinError 10053）后，
    后续页面都会连带失败。页面级重连既隔离了这种环境噪声，也不会掩盖 Streamlit 报错。
    """
    last_error = None
    for attempt in range(1, attempts + 1):
        ws = None
        cdp = None
        try:
            ws = bf._new_tab("http://localhost:8501" + path)
            cdp = bf._CDP(ws)
            cdp.call("Page.enable")
            time.sleep(wait)
            html = cdp.call("Runtime.evaluate", {
                "expression": "document.documentElement.outerHTML",
                "returnByValue": True}, timeout=60).get("result", {}).get("value") or ""
            if not html:
                raise RuntimeError("页面没有返回 HTML")
            return html_to_text(html)
        except Exception as exc:
            last_error = exc
            if attempt < attempts:
                print(f"   ↻ {path} 连接异常，重开页面重试：{type(exc).__name__}: {exc}")
        finally:
            if cdp is not None:
                cdp.close()
            if ws is not None:
                bf._close_tab(ws)
    raise RuntimeError(f"{path} 连续 {attempts} 次读取失败：{last_error}") from last_error


def main():
    if not bf.launch(headless=True):
        raise SystemExit("Edge 启动失败")

    bad = []
    for name, path in PLAN:
        try:
            t = read_page(path)
        except Exception as exc:
            print(f"❌ {name:<18} {path:<10} 巡检失败：{exc}")
            bad.append((name, path, [type(exc).__name__]))
            continue
        hits = [k for k in ERR_KWS if k in t]
        flag = "❌" if hits else "✅"
        print(f"{flag} {name:<18} {path:<10} 报错={hits if hits else '无'} | {len(t)} 字")
        if hits:
            bad.append((name, path, hits))
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
