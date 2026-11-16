# -*- coding: utf-8 -*-
"""演示数据模块测试（离线，用临时目录，不碰真实 data/）。

跑法：python offeragent\\test_demo_data.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import store      # noqa: E402
import demo_data  # noqa: E402

RESULTS = []


def check(name, ok, extra=""):
    RESULTS.append((name, bool(ok)))
    print(("  ✅ " if ok else "  ❌ ") + name + (f"  {extra}" if extra else ""))


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="oa_demo_"))
    old = (store.JDS_DIR, store.MATCH_DIR, store.PROFILE_PATH,
           demo_data.JDS_DIR, demo_data.PROFILE_PATH)
    try:
        store.JDS_DIR = tmp / "jds"
        store.MATCH_DIR = tmp / "meta"
        store.PROFILE_PATH = tmp / "profile.md"
        demo_data.JDS_DIR = store.JDS_DIR
        demo_data.PROFILE_PATH = store.PROFILE_PATH
        store.ensure_dirs()

        check("空库时 demo_job_names 为空", demo_data.demo_job_names() == [])

        msg = demo_data.seed_demo()
        check("seed_demo 载入 6 个演示岗位", "6 个演示岗位" in msg, msg)
        check("岗位库有 6 条", len(store.list_jobs()) == 6, str(len(store.list_jobs())))
        check("演示岗位被正确标记", len(demo_data.demo_job_names()) == 6)
        check("真实岗位数为 0", demo_data.real_job_count() == 0)
        check("示例画像已写入", store.PROFILE_PATH.exists())

        # 演示数据不能被当成真实数据（防止误判拦截自己）
        got = {n for n, m, _ in store.list_jobs()}
        check("岗位名与 JD 落盘正确", len(got) == 6 and all((store.JDS_DIR / (n + ".txt")).exists() for n in got))

        msg = demo_data.clear_demo()
        check("clear_demo 清掉 6 个", "清除 6 个演示岗位" in msg, msg)
        check("岗位库清空", len(store.list_jobs()) == 0)
        check("示例画像一并删除", not store.PROFILE_PATH.exists())
        check("重复清除给友好提示", "没有找到演示数据" in demo_data.clear_demo())

        # 有真实岗位时必须拒绝自动覆盖
        store.save_new_job("我的真实岗位", "南京", "这是我自己找的岗位 JD")
        check("有真实岗位时拒绝载入", "已经有" in demo_data.seed_demo())
        check("拒绝后岗位数不变", len(store.list_jobs()) == 1)
        check("force=True 可以强制载入", "6 个演示岗位" in demo_data.seed_demo(force=True))
        check("强制后演示+真实共存", demo_data.real_job_count() == 1 and len(demo_data.demo_job_names()) == 6)
        demo_data.clear_demo()
        check("清演示不影响真实岗位", demo_data.real_job_count() == 1 and len(store.list_jobs()) == 1)
    finally:
        (store.JDS_DIR, store.MATCH_DIR, store.PROFILE_PATH,
         demo_data.JDS_DIR, demo_data.PROFILE_PATH) = old
        shutil.rmtree(tmp, ignore_errors=True)

    bad = [n for n, ok in RESULTS if not ok]
    print()
    if bad:
        print(f"❌ {len(bad)}/{len(RESULTS)} 项未通过：{bad}")
        return 1
    print(f"✅ 演示数据 {len(RESULTS)}/{len(RESULTS)} 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
