# -*- coding: utf-8 -*-
"""阶段1 验收：空态 / 错误态组件能渲染出预期结构（离线，不需要浏览器/网络）。

跑法：python offeragent\\test_ui_states.py
"""
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

# Windows 控制台默认 GBK，直接 print emoji 会 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from streamlit.testing.v1 import AppTest  # noqa: E402

SRC = (
    "import sys\n"
    f"sys.path.insert(0, r'{HERE}')\n"
    "import streamlit as st\n"
    "from ui_kit import empty_state, error_box\n"
    "empty_state('标题A', '说明A', icon='📭', hint='提示A')\n"
    "empty_state('标题B')\n"
    "error_box('标题C', '细节C')\n"
    "error_box('标题D')\n"
)


def main() -> int:
    at = AppTest.from_string(SRC, default_timeout=60).run()
    if at.exception:
        print("❌ 渲染异常：", [(type(e).__name__, str(e)[:200]) for e in at.exception])
        return 1
    html = "".join(m.value for m in at.markdown)
    checks = {
        "空态容器 .oa-empty": html.count("oa-empty") >= 1,
        "空态图标": "oa-empty-icon" in html,
        "空态标题": "标题A" in html and "标题B" in html,
        "空态说明/提示": "说明A" in html and "提示A" in html,
        "错误块 .oa-errbox": html.count("oa-errbox") >= 1,
        "错误标题/细节": "标题C" in html and "细节C" in html and "标题D" in html,
    }
    bad = [k for k, v in checks.items() if not v]
    for k, v in checks.items():
        print(("  ✅ " if v else "  ❌ ") + k)
    if bad:
        print(f"\n❌ {len(bad)} 项未通过：{bad}")
        return 1
    print("\n✅ 空态/错误态组件 6/6 通过")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)
