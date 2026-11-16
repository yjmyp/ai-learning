# -*- coding: utf-8 -*-
"""数字分身页布局回归：语音组件不能用 scrollHeight 回传高度。

2026-10-20 实测 bug：iframe 被列高拉伸后回传 scrollHeight，形成
“页面变高 → iframe 变高 → 回传更大高度”的循环，把 /twin 撑到 4 万 px。
"""
from pathlib import Path

BASE = Path(__file__).resolve().parent


def test_voice_component_height_is_fixed():
    html = (BASE / "static" / "voice_input" / "index.html").read_text(encoding="utf-8")
    assert "document.documentElement.scrollHeight" not in html
    assert "height: 46" in html


def test_listen_passes_fixed_height():
    src = (BASE / "twin_voice.py").read_text(encoding="utf-8")
    assert "height=48" in src


def test_twin_chat_is_scroll_container():
    src = (BASE / "pages_twin.py").read_text(encoding="utf-8")
    assert 'st.container(height=410, border=True, key="oa_twin_chat")' in src
    assert "avatar=_cur, height=270" in src


def test_player_supports_compact_sidebar():
    src = (BASE / "twin_voice.py").read_text(encoding="utf-8")
    assert "compact: bool = False" in src
    assert "flex-wrap" in src


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("4/4 passed")
