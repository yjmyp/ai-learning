# -*- coding: utf-8 -*-
"""trace 日志轮转验收：日志不能无限增长把磁盘写满。

跑法：python test_trace_rotate.py（秒级，不依赖服务）
"""
import importlib
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    # 用临时目录 + 极小阈值验证轮转，别碰真实 trace
    tmp = os.path.join(HERE, "data", "tmp_trace_rotate")
    os.makedirs(tmp, exist_ok=True)
    path = os.path.join(tmp, "trace.jsonl")
    for f in (path, path + ".1"):
        if os.path.exists(f):
            os.remove(f)
    os.environ["TRACE_MAX_BYTES"] = "300"
    import trace as trace_mod
    trace_mod = importlib.reload(trace_mod)
    trace_mod.TRACE_DIR = tmp
    trace_mod.TRACE_PATH = path
    for i in range(40):                       # 每条约 60 字节，40 条必然超阈值
        trace_mod.log("ask", i=i, q="测试问题内容" * 3)
    cur = os.path.getsize(path) if os.path.exists(path) else -1
    checks = [
        ("轮转生成备份文件 trace.jsonl.1", os.path.exists(path + ".1")),
        ("当前 trace 小于阈值（%d 字节 < 300）" % cur, 0 <= cur < 300),
        ("load() 仍能读回记录（不因轮转报错）", len(trace_mod.load()) > 0),
    ]
    for f in (path, path + ".1"):
        try:
            os.remove(f)
        except Exception:
            pass
    try:
        os.rmdir(tmp)
    except Exception:
        pass
    ok = sum(1 for _, v in checks if v)
    for name, good in checks:
        print(("PASS " if good else "FAIL ") + name)
    print("\n%d/%d 通过" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
