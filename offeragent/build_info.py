# -*- coding: utf-8 -*-
"""运行版本自检：把"这台机器跑的到底是哪版代码 + 哪个 Streamlit"变成一行字。

为什么要它：2026-10-10 的事故里，第一条报错的文案（`Assign st.session_state[...]
before creating the widget...`）只存在于 Streamlit 1.65.0，而本机装的是 1.61.1 ——
也就是说"本地测试全绿"根本没证明云端不会崩，两边根本不是同一个运行时。
再加上 Streamlit Cloud 有时要手动 Reboot 才加载新提交（CONTEXT 第 16 条踩过），
所以设置页把两个数字都印出来：**本地和云端对不上 = 云端还在跑旧代码 / 旧版本**。
（和 resume_templates.build_tag() 是同一个思路，只是这里盖整个 offeragent/。）
"""
import functools
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def streamlit_version() -> str:
    """当前进程实际用的 Streamlit 版本（拿不到就 unknown，绝不抛）。"""
    try:
        import streamlit
        return str(getattr(streamlit, "__version__", "unknown"))
    except Exception:
        return "unknown"


def code_fingerprint(root=None) -> str:
    """offeragent/ 下**应用代码**的内容指纹（8 位十六进制）。

    - 只看 .py 内容，不看 mtime → 本地和云端只要代码一样，数字就一样；
    - 跳过 __pycache__ / data / test_*.py —— 测试和数据不该让数字乱跳。
    """
    root = Path(root) if root else HERE
    try:
        h = hashlib.md5()
        for p in sorted(root.rglob("*.py")):
            if "__pycache__" in p.parts or "data" in p.parts:
                continue
            if p.name.startswith("test_"):
                continue
            h.update(str(p.relative_to(root)).encode("utf-8"))
            h.update(p.read_bytes())
        return h.hexdigest()[:8]
    except Exception:
        return "unknown"


@functools.lru_cache(maxsize=1)
def describe() -> dict:
    """给界面用的一行版本信息（缓存在进程里，别每次渲染都重算）。"""
    return {
        "streamlit": streamlit_version(),
        "code": code_fingerprint(),
        "python": "%d.%d.%d" % sys.version_info[:3],
    }
