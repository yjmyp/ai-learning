# -*- coding: utf-8 -*-
"""静态检查：session_state 的 key 不许跟控件的 key 撞名。**不用跑 Streamlit、不联网。**

为什么要有这个检查（真实事故，2026-10-10）：
  `pages_work.py` 里城市多选框写的是 `key="src_cities"`，而搜岗结果那里又写了
  `st.session_state["src_cities"] = 各来源城市分布`。同一个 key 既当控件又当结果：
    · 写入时 Streamlit 直接报
      "st.session_state.src_cities cannot be modified after the widget with key
       src_cities is instantiated"
    · 下一轮渲染读到的是**控件值**（一个 list），`for s, rows in cdist.items()` →
      AttributeError: 'list' object has no attribute 'items'
  表现就是"点一次「开始搜岗」整页崩"，而且**只有真去点按钮才会暴露**——
  页面巡检只看渲染，看不到。

做法：用 AST 把每个文件里的两套 key 都抓出来对一遍：
  · 控件 key：调用了 `st.xxx(...)` / `cx.xxx(...)`（xxx 是控件函数名）且带 `key="..."`
  · 状态 key：`st.session_state["x"] = ...`、`st.session_state.x = ...`、
    `st.session_state.setdefault("x", ...)`
两套名字空间必须不相交。约定：控件一律 `wq_` 前缀，搜岗结果一律 `sr_` 前缀。

跑法：python offeragent/test_session_keys.py
"""
import ast
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Streamlit 里"带 key 的控件"函数名（够用即可；漏掉个别不影响主要防线）
WIDGET_FUNCS = {
    "text_input", "text_area", "multiselect", "selectbox", "select_slider",
    "toggle", "checkbox", "radio", "slider", "number_input", "date_input",
    "time_input", "color_picker", "button", "form_submit_button",
    "download_button", "link_button", "file_uploader", "camera_input",
    "audio_input", "chat_input", "data_editor", "segmented_control", "pills",
    "form", "feedback",
}


def _const_str(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def scan(path: Path):
    """返回 (控件 key→行号, 状态 key→行号)。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    widgets, states = {}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn_name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if fn_name in WIDGET_FUNCS:
                for kw in node.keywords:
                    if kw.arg == "key":
                        k = _const_str(kw.value)
                        if k:
                            widgets.setdefault(k, node.lineno)
            # st.session_state.setdefault("x", ...) 也相当于写这个 key
            if fn_name == "setdefault":
                base = getattr(node.func, "value", None)
                if isinstance(base, ast.Attribute) and base.attr == "session_state" and node.args:
                    k = _const_str(node.args[0])
                    if k:
                        states.setdefault(k, node.lineno)
        if isinstance(node, (ast.Assign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Subscript):
                    base = getattr(t.value, "value", None)
                    if isinstance(t.value, ast.Attribute) and t.value.attr == "session_state" \
                            and isinstance(base, ast.Name) and base.id == "st":
                        k = _const_str(t.slice)
                        if k:
                            states.setdefault(k, node.lineno)
                elif isinstance(t, ast.Attribute):
                    if isinstance(t.value, ast.Attribute) and t.value.attr == "session_state":
                        states.setdefault(t.attr, node.lineno)
    return widgets, states


def main():
    files = sorted(p for p in HERE.glob("*.py") if not p.name.startswith("test_"))
    files += [p for p in (HERE.parent.glob("*.py")) if not p.name.startswith("test_")]
    scanned, collisions = 0, []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        if "session_state" not in text:
            continue
        try:
            widgets, states = scan(path)
        except SyntaxError as e:
            collisions.append(f"{path.name}: 语法错误 {e}")
            continue
        scanned += 1
        for k in sorted(set(widgets) & set(states)):
            collisions.append(f"{path.name}: 控件 key「{k}」(第 {widgets[k]} 行) "
                              f"和 session_state key「{k}」(第 {states[k]} 行) 撞名")

    print(f"扫了 {scanned} 个用 session_state 的文件")
    if collisions:
        for c in collisions:
            print("❌ " + c)
        print("\n0/1 通过——同一个 key 既当控件又当结果，会在用户点按钮时整页报错。")
        return 1
    print("✅ 控件 key 与 session_state key 没有撞名（控件 wq_ / 结果 sr_ 两套命名空间）")
    print("\n1/1 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
