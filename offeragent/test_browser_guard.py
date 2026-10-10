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

    # 2) 候选清单覆盖常见位置 + PATH（Windows 严格检查本地路径；Linux/macOS 只查通用项）
    real_platform = bf.sys.platform
    cands = bf.edge_candidates()
    if real_platform == "win32":
        checks.append(("候选清单里有 LocalAppData 路径",
                       any("Microsoft\\Edge\\Application".lower() in c.lower()
                           or "Microsoft/Edge/Application".lower() in c.lower()
                           for c in cands)))
    checks.append(("候选清单里有 Chrome 兜底",
                   any("chrome" in c.lower() for c in cands)))
    checks.append(("候选清单非空", len(cands) > 0))
    checks.append(("错误提示里给了解决办法",
                   "EDGE_PATH" in bf.no_browser_message()
                   and "牛客" in bf.no_browser_message()))

    # 3) 模拟云端：Linux 平台
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

    # 5) 标签页回收：_new_tab 开的标签必须被关掉
    #    （cdp.close() 关的是 websocket，不是标签页；以前实测攒到 52 个，
    #     浏览器越来越慢，一次搜索从十几秒被拖到 150 秒以上）
    closed = []

    class _FakeResp:
        status_code = 200

        def json(self):
            return {"id": "x"}

    orig_get = bf.requests.get
    bf.requests.get = lambda url, **kw: (closed.append(url), _FakeResp())[1]
    try:
        ok_close = bf._close_tab("ws://127.0.0.1:9333/devtools/page/TARGET123")
    finally:
        bf.requests.get = orig_get
    checks.append(("_close_tab 从 ws_url 取 targetId 并调 /json/close/<id>",
                   bool(ok_close and closed and closed[-1].endswith("/json/close/TARGET123"))))

    orig_ours, orig_close_id = bf.our_tabs, bf._close_tab_id
    bf.our_tabs = lambda: [{"id": "t%d" % i} for i in range(20)]
    gone = []
    bf._close_tab_id = lambda tid: (gone.append(tid), True)[1]
    try:
        n = bf.close_stale_tabs(keep=4, max_before_clean=12)
    finally:
        bf.our_tabs, bf._close_tab_id = orig_ours, orig_close_id
    checks.append(("堆积超阈值时只留 keep 个（20 个 → 关掉 %d 个）" % n, n == 16))

    ok_n = 0
    for cname, good in checks:
        print(("✅ " if good else "❌ ") + cname)
        ok_n += 1 if good else 0
    print(f"\n{ok_n}/{len(checks)} 通过")
    return 0 if ok_n == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
