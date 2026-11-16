# -*- coding: utf-8 -*-
"""搜岗「边搜边出」与相关度排序的离线测试（不联网）。

覆盖三件事：
  1. 第一个来源完成后就能读到进行中快照（以前要等所有来源跑完）；
  2. 搜索结束后进行中快照被清掉，不会让下一次搜索看到旧结果；
  3. 关键词命中岗位名的结果排在前面（相关度排序真的生效）。
"""
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

_tmp = Path(tempfile.mkdtemp(prefix="oa_stream_"))
os.environ["JOBS_PARTIAL"] = str(_tmp / "partial.json")
os.environ["JOBS_LAST_SEARCH"] = str(_tmp / "last.json")
os.environ["JOBS_CACHE"] = str(_tmp / "cache.json")

import job_sources as js  # noqa: E402


def _job(src, title):
    return {"title": title, "company": "公司" + src, "city": "南京", "salary": "",
            "url": "u-" + src + "-" + title, "source": src, "extra": "", "jd": "",
            "match_hits": 1, "city_hit": True}


def test_partial_snapshot_visible_before_all_done():
    js.CACHE_ENABLED = False
    delays = {"牛客": 0.20, "腾讯招聘": 0.60, "网易招聘": 0.90}

    def fake_search(src, keyword, city="", ask_model=None, diag=None, **kw):
        time.sleep(delays[src])
        return [_job(src, "AI 应用开发")]

    orig = js.search
    js.search = fake_search
    seen = []
    stop = threading.Event()

    def watch():
        while not stop.is_set():
            part = js.load_partial()
            if part:
                seen.append((part.get("done"), len(part.get("merged") or [])))
            time.sleep(0.05)

    t = threading.Thread(target=watch)
    t.start()
    try:
        res = js.search_all("AI", "南京", sources=list(delays), strict_city=True)
    finally:
        stop.set()
        t.join()
        js.search = orig
    ok = (len(res["jobs"]) == 3
          and any(done < 3 and n >= 1 for done, n in seen)   # 中途就能看到部分结果
          and seen[-1][0] <= 3)
    return ok, seen


def test_partial_cleared_after_finish():
    return js.load_partial() == {}


def test_relevance_order():
    js.CACHE_ENABLED = False

    def fake_search(src, keyword, city="", ask_model=None, diag=None, **kw):
        if src == "牛客":
            return [_job(src, "行政专员")]
        return [_job(src, "AI 大模型应用开发")]

    orig = js.search
    js.search = fake_search
    try:
        res = js.search_all("AI 大模型", "南京", sources=["牛客", "腾讯招聘"],
                            strict_city=True)
    finally:
        js.search = orig
    return [j["title"] for j in res["jobs"]][0].startswith("AI")


def main():
    checks = []
    ok, seen = test_partial_snapshot_visible_before_all_done()
    checks.append(("第一个来源完成即可读到进行中结果", ok))
    checks.append(("搜索结束清掉进行中快照", test_partial_cleared_after_finish()))
    checks.append(("关键词命中岗位名的排前面", test_relevance_order()))
    for name, good in checks:
        print(("✅ " if good else "❌ ") + name)
    print("\n%d/%d 通过" % (sum(1 for _, g in checks if g), len(checks)))
    print("中途快照序列：", seen[:6])
    return 0 if all(g for _, g in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())

