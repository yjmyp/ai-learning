# -*- coding: utf-8 -*-
"""搜岗提速验收：并发翻页（含礼貌节流）+ 结果缓存。**不用联网**。

背景（实测数字）：抓 8 页牛客 = 26.6 秒，其中本地解析 160 条只花 0.0011 秒
（占 0.004%）——时间全花在等网络上。所以提速只有两条正路：
  ① 并发翻页（3 路），把「页数 × 单页耗时」压成「页数/3 × 单页耗时」
  ② 结果缓存，同关键词+城市 10 分钟内再搜 = 秒回、且不打站点
这个测试把这两件事的行为钉死（并发真的并发、节流真的节流、缓存真的命中/真的过期）。

跑法：python offeragent/test_search_cache.py
"""
import os
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 缓存写到临时目录：测试绝不能碰真缓存文件 offeragent/data/search_cache.json
_TMP = tempfile.mkdtemp(prefix="oa_cache_test_")
os.environ["JOBS_CACHE"] = os.path.join(_TMP, "search_cache.json")

import job_sources as js  # noqa: E402


ROWS = [{"title": "AI 岗 A", "company": "甲", "city": "南京", "salary": "",
         "url": "u1", "source": "甲平台", "extra": "", "jd": "",
         "match_hits": 1, "city_hit": True}]


def test_cache_basic():
    js.cache_clear()
    js.cache_put("甲平台", "AI", "南京", 50, list(ROWS))
    hit, age = js.cache_get("甲平台", "AI", "南京", 50)
    ok_hit = hit == ROWS and age >= 0
    # 关键词大小写/空格不该影响命中（缓存键做了归一）
    hit2, _ = js.cache_get("甲平台", " ai ", " 南京 ", 50)
    ok_norm = hit2 == ROWS
    # 换了关键词 / 城市 / 每源上限 = 另一份缓存，不能串味
    miss = [js.cache_get("甲平台", "Java", "南京", 50)[0],
            js.cache_get("甲平台", "AI", "上海", 50)[0],
            js.cache_get("甲平台", "AI", "南京", 100)[0]]
    return ok_hit and ok_norm and all(m is None for m in miss)


def test_cache_ttl():
    js.cache_clear()
    js.cache_put("甲平台", "AI", "南京", 50, list(ROWS))
    time.sleep(0.02)
    fresh, _ = js.cache_get("甲平台", "AI", "南京", 50, ttl=600)
    expired, _ = js.cache_get("甲平台", "AI", "南京", 50, ttl=0)     # 任何 age > 0 都算过期
    return fresh == ROWS and expired is None


def test_cache_guard_and_stats():
    js.cache_clear()
    js.cache_put("甲平台", "AI", "南京", 50, [])      # 空结果不写缓存
    empty_ok = js.cache_stats()["entries"] == 0
    js.cache_put("甲平台", "AI", "南京", 50, list(ROWS))
    st = js.cache_stats()
    js.CACHE_ENABLED = False
    off_ok = js.cache_get("甲平台", "AI", "南京", 50)[0] is None
    js.CACHE_ENABLED = True
    n = js.cache_clear()
    return empty_ok and st["entries"] == 1 and st["size_kb"] > 0 and off_ok and n == 1


def test_parallel_really_parallel():
    """6 页、每页 sleep 0.2：串行要 1.2 秒，3 路并发应明显更快。"""
    def fetch(p):
        time.sleep(0.2)
        return p
    t0 = time.perf_counter()
    out = js.parallel_pages(fetch, 6, workers=3, key="t-par", min_interval=0)
    dt = time.perf_counter() - t0
    return dt < 0.9 and [p for p, _ in out] == [1, 2, 3, 4, 5, 6]


def test_parallel_throttle():
    """并发不等于轰站：同一站点两次请求的发出时间必须隔开 min_interval。"""
    js._LAST_HIT.clear()
    stamps = []

    def fetch(p):
        stamps.append(time.time())
        return p
    js.parallel_pages(fetch, 6, workers=3, key="t-thr", min_interval=0.2)
    stamps.sort()
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    return bool(gaps) and min(gaps) >= 0.19      # 留 10ms 调度误差


def test_parallel_stop_and_error():
    """到底了要提前收工（不多翻），单页报错只废那一页。"""
    def fetch(p):
        if p == 4:
            raise RuntimeError("这一页网络挂了")
        return p
    capped = js.parallel_pages(fetch, 8, workers=3, key="t-stop",
                               min_interval=0, stop_when=lambda r: r == 2)
    ok_cap = [p for p, _ in capped] == [1, 2]
    got = dict(js.parallel_pages(fetch, 5, workers=3, key="t-err", min_interval=0))
    ok_err = got.get(4) is None and got.get(5) == 5
    seq = js.parallel_pages(fetch, 3, workers=1, key="t-seq", min_interval=0)
    ok_seq = [p for p, _ in seq] == [1, 2, 3]
    return ok_cap and ok_err and ok_seq


def test_search_all_uses_cache():
    """真跑一遍 search_all：第二次同条件必须命中缓存、不再调来源函数。"""
    js.CACHE_ENABLED = True
    js.cache_clear()
    calls = {"n": 0}

    def fake_search(src, keyword, city="", ask_model=None, diag=None, **kwargs):
        calls["n"] += 1
        if diag is not None:
            diag["raw"] = len(ROWS)
        return list(ROWS)

    orig = js.search
    js.search = fake_search
    try:
        r1 = js.search_all("AI", "南京", sources=["甲平台"], max_per_source=50)
        r2 = js.search_all("AI", "南京", sources=["甲平台"], max_per_source=50)
        r3 = js.search_all("AI", "南京", sources=["甲平台"], max_per_source=50,
                           use_cache=False)
        js.search_all("AI", "上海", sources=["甲平台"], max_per_source=50)   # 换城市=另一份缓存
    finally:
        js.search = orig
        js.CACHE_ENABLED = False
        js.cache_clear()
    return (calls["n"] == 3                        # 第 2 次命中缓存，没调来源
            and r2["cache_hits"] == 1 and r1["cache_hits"] == 0
            and len(r1["jobs"]) == len(r2["jobs"]) == len(r3["jobs"]) == 1
            and r1["jobs"] == r2["jobs"])


def test_cross_source_parallel():
    """纯 HTTP 的来源要并发抓（总耗时≈最慢的那个，而不是三个相加），且输出顺序不变。

    故意让完成顺序和输入顺序相反（腾讯 0.05s 先回、牛客 0.30s 后回），
    这样"输出仍按 sources 顺序"这条才真的被验证到。
    """
    js.CACHE_ENABLED = False
    delays = {"牛客": 0.30, "腾讯招聘": 0.05, "网易招聘": 0.20}

    def fake_search(src, keyword, city="", ask_model=None, diag=None, **kw):
        time.sleep(delays.get(src, 0))
        return [{"title": "岗-" + src, "company": "公司" + src, "city": "南京",
                 "salary": "", "url": "u-" + src, "source": src, "extra": "",
                 "jd": "", "match_hits": 1, "city_hit": True}]

    orig = js.search
    js.search = fake_search
    try:
        t0 = time.perf_counter()
        r = js.search_all("AI", "南京", sources=list(delays), strict_city=True)
        dt = time.perf_counter() - t0
    finally:
        js.search = orig
    order_ok = [j["source"] for j in r["jobs"]] == ["牛客", "腾讯招聘", "网易招聘"]
    return dt < 0.6 and order_ok and len(r["jobs"]) == 3


class _CountingSem(threading.BoundedSemaphore):
    """给 BoundedSemaphore 记一笔"当前占用了几个"，用来验证全局名额池真的生效。"""

    def __init__(self, value):
        super().__init__(value)
        self.held = 0
        self.peak = 0

    def acquire(self, *a, **k):
        got = super().acquire(*a, **k)
        if got:
            self.held += 1
            self.peak = max(self.peak, self.held)
        return got

    def release(self):
        self.held -= 1
        return super().release()


def test_net_slot_budget():
    """全局名额池：不管起多少线程，同时在飞的数量不许超过 GLOBAL_INFLIGHT。"""
    orig = js._INFLIGHT
    sem = _CountingSem(js.GLOBAL_INFLIGHT)
    js._INFLIGHT = sem
    try:
        def one():
            with js._NetSlot():
                time.sleep(0.05)
        threads = [threading.Thread(target=one) for _ in range(9)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        js._INFLIGHT = orig
    return 2 <= sem.peak <= js.GLOBAL_INFLIGHT and sem.held == 0


def test_request_path_takes_slot():
    """真正发包的那一行确实占了名额（用假 requests 观察：请求发出时名额已占用）。"""
    orig_sem, orig_post = js._INFLIGHT, js.requests.post
    sem = _CountingSem(js.GLOBAL_INFLIGHT)
    held_at_send = []

    class _FakeResp:
        def json(self):
            return {"code": 0, "data": {"datas": [], "totalCount": 0}}

    def fake_post(url, **kw):
        held_at_send.append(sem.held)       # 发包这一刻占着几个名额
        return _FakeResp()

    js._INFLIGHT, js.requests.post = sem, fake_post
    try:
        js._nowcoder_fetch_page(1, "&query=AI", 20)
    finally:
        js._INFLIGHT, js.requests.post = orig_sem, orig_post
    return held_at_send == [1]              # 发这一个请求时，正好占 1 个名额


def test_search_guard():
    """正在搜岗时，第二次调用要**立刻拒绝**，而不是默默排队（排队会让两边都更慢）。"""
    js.CACHE_ENABLED = False
    orig_wait, orig_search = js.SEARCH_LOCK_WAIT, js.search
    js.SEARCH_LOCK_WAIT = 0.2

    def slow_search(src, keyword, city="", ask_model=None, diag=None, **kw):
        time.sleep(0.6)
        return []

    errors = []

    def second_call():
        time.sleep(0.05)          # 让第一次先拿到闸
        try:
            js.search_all("AI", "", sources=["牛客"])
        except Exception as e:
            errors.append(str(e))

    js.search = slow_search
    try:
        t = threading.Thread(target=second_call)
        t.start()
        first = js.search_all("AI", "", sources=["牛客"])
        t.join()
    finally:
        js.search, js.SEARCH_LOCK_WAIT = orig_search, orig_wait
        js.CACHE_ENABLED = False
    return (first["jobs"] == [] and len(errors) == 1
            and "还没跑完" in errors[0])



def test_browser_source_stays_serial():
    """要浏览器 + 大模型的来源（实习僧/BOSS）不许进线程池——ask_chat 依赖 Streamlit 会话状态。"""
    js.CACHE_ENABLED = False
    in_main = {}

    def fake_search(src, keyword, city="", ask_model=None, diag=None, **kw):
        in_main[src] = threading.current_thread() is threading.main_thread()
        return []

    orig = js.search
    js.search = fake_search
    try:
        js.search_all("AI", "", sources=["牛客", "腾讯招聘", "实习僧"])
    finally:
        js.search = orig
    return in_main.get("实习僧") is True and in_main.get("牛客") is False


def main():
    checks = [
        ("缓存读写 + 键归一（关键词/城市/上限不串味）", test_cache_basic()),
        ("缓存 TTL：新鲜命中、过期失效", test_cache_ttl()),
        ("空结果不缓存 / 统计 / 开关 / 清空", test_cache_guard_and_stats()),
        ("并发翻页真的并发（6 页 × 0.2s 明显快于串行 1.2s）", test_parallel_really_parallel()),
        ("礼貌节流：同站点请求间隔 ≥ 0.2s（并发≠轰站）", test_parallel_throttle()),
        ("到底提前收工 / 单页失败只废这页 / 单线程退化成顺序", test_parallel_stop_and_error()),
        ("search_all 第二次同条件命中缓存、不再联网", test_search_all_uses_cache()),
        ("跨来源并发：纯 HTTP 三个来源并行、输出顺序仍按 sources", test_cross_source_parallel()),
        ("实习僧/BOSS 不进线程池（ask_chat 非线程安全）", test_browser_source_stays_serial()),
        ("全局名额池：最多的在飞请求数 = GLOBAL_INFLIGHT（勾几个来源都一样）", test_net_slot_budget()),
        ("真正发包的那一行确实占了名额（假 requests 观测）", test_request_path_takes_slot()),
        ("同时只允许一次搜岗（第二次立刻拒绝，不排队）", test_search_guard()),
    ]
    ok_n = sum(1 for _, v in checks if v)
    for name, good in checks:
        print(("✅ " if good else "❌ ") + name)
    print("\n%d/%d 通过" % (ok_n, len(checks)))
    return 0 if ok_n == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
