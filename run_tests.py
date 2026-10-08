# -*- coding: utf-8 -*-
"""统一测试入口：一键跑通全部离线测试。

用法:
    python run_tests.py            # 跑全部离线测试（跳过 live/网络/API 类）
    python run_tests.py --live     # 连 live/网络/API 类一起跑（会真实调用 API，费额度）
    python run_tests.py --service  # 额外跑 rag2 服务化测试（起端口，约 1 分钟）

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
RAG2 = ROOT / "rag2"
PY = sys.executable

def collect_tests(with_service: bool = False):
    tests = []
    bases = [ROOT, OFFERAGENT] + ([RAG2] if with_service else [])
    for base in bases:
        for p in sorted(base.glob("test_*.py")):
            if not p.name.startswith("test_"):
                continue
            if p.name.startswith("test_agent.py") and base is not ROOT:
                continue  # 根目录的 test_agent.py 是主回归，避免重复
            if base is RAG2 and p.name in ("test_rag2.py", "test_p3.py"):
                continue  # 检索质量回归，含模型加载，本地按需单跑
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
                           timeout=timeout, cwd=str(p.parent),
                           encoding="utf-8", errors="replace")  # Windows 控制台默认 GBK，会解码崩
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
    service = "--service" in sys.argv
    tests = collect_tests(with_service=service)
    passed, failed, skipped = [], [], []

    print(f"== 项目测试总入口 ==")
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
