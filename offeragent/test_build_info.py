# -*- coding: utf-8 -*-
"""运行版本自检验收：代码指纹 + Streamlit 版本 + 依赖上界。不用联网。

背景（2026-10-10）：云端 `streamlit>=1.36` 自动装到 1.65.0，本机是 1.61.1，
同一份代码两个运行时 —— 用户贴的第一条报错文案只存在于 1.65.0，
也就是说"本地测试全绿"证明不了云端不出事。这份测试钉住三件事：
  1. 代码指纹只跟"应用代码内容"有关（改代码就变、动测试文件不变、和机器无关）；
  2. 设置页要印的版本信息一定拿得到（拿不到也得是 unknown，不能抛异常把页面搞崩）；
  3. requirements 里 Streamlit 必须带上界（防止云端又自动漂到没测过的版本）。

跑法：python offeragent/test_build_info.py
"""
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import build_info  # noqa: E402


def _ver(s: str):
    """'1.65.0' → (1, 65, 0)；够用就行，不引额外依赖。"""
    out = []
    for piece in str(s).split("."):
        num = "".join(ch for ch in piece if ch.isdigit())
        out.append(int(num) if num else 0)
    return tuple((out + [0, 0, 0])[:3])


def _streamlit_spec(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.lower().startswith("streamlit"):
            return line
    return ""


def test_fingerprint_tracks_code_only():
    """指纹：内容变就变；只动 test_*.py 不变；与文件时间无关。"""
    tmp = Path(tempfile.mkdtemp(prefix="oa_bi_"))
    (tmp / "app_a.py").write_text("print(1)\n", encoding="utf-8")
    (tmp / "test_app_a.py").write_text("print('test')\n", encoding="utf-8")
    f1 = build_info.code_fingerprint(tmp)
    stable = build_info.code_fingerprint(tmp) == f1
    (tmp / "test_app_a.py").write_text("print('test changed')\n", encoding="utf-8")
    test_only_ok = build_info.code_fingerprint(tmp) == f1
    (tmp / "app_a.py").write_text("print(2)\n", encoding="utf-8")
    changed = build_info.code_fingerprint(tmp) != f1
    return stable and test_only_ok and changed and len(f1) == 8


def test_describe_never_throws():
    """设置页要印的字段都能拿到，且形状对（拿不到也得是 unknown）。"""
    d = build_info.describe()
    ok_ver = isinstance(d["streamlit"], str) and d["streamlit"] != ""
    ok_code = isinstance(d["code"], str) and len(d["code"]) == 8
    ok_py = d["python"].count(".") == 2
    return ok_ver and ok_code and ok_py


def test_requirements_pin_streamlit():
    """两份 requirements 的 Streamlit 都要有上界，且本机装的版本落在区间里。"""
    import streamlit
    installed = _ver(streamlit.__version__)
    ok_all = True
    for req in (HERE / "requirements.txt", ROOT / "requirements.txt"):
        spec = _streamlit_spec(req)
        if not spec:
            return False
        tokens = [t.strip() for t in spec.split("streamlit", 1)[1].split(",") if t.strip()]
        low = next((_ver(t[2:]) for t in tokens if t.startswith(">=")), None)
        high = next((_ver(t[1:]) for t in tokens if t.startswith("<")), None)
        if low is None or high is None:      # 没上界 = 云端又会自动漂，直接判失败
            ok_all = False
        elif not (low <= installed < high):
            ok_all = False
    return ok_all


def main():
    checks = [
        ("代码指纹：改代码就变、动测试不变、8 位十六进制", test_fingerprint_tracks_code_only()),
        ("版本信息拿得到（Streamlit / Python / 代码指纹）", test_describe_never_throws()),
        ("requirements 的 Streamlit 有上界且本机版本落在区间里（两份文件一致要求）",
         test_requirements_pin_streamlit()),
    ]
    ok_n = sum(1 for _, v in checks if v)
    for name, good in checks:
        print(("✅ " if good else "❌ ") + name)
    print("\n%d/%d 通过" % (ok_n, len(checks)))
    return 0 if ok_n == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
