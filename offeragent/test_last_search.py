# -*- coding: utf-8 -*-
"""搜岗结果快照验收：**页面重跑不丢结果**。不用联网、不用浏览器。

背景（2026-10-10 实测复现）：点「开始搜岗」后搜索要跑十几秒，这期间页面上任何
一次重跑（动别的控件 / 前端重连 / 手机切后台）都会中断"正在跑的那次运行"。
旧运行算出来的结果只写在当次的 st.session_state 里 → 新运行读到空 →
页面既不出结果也不报错，等满 120 秒还是空的，用户看到的就是"点了没反应"。

修法（这份测试要钉住的行为）：
  1. search_all() 返回**之前**就把完整结果落一份磁盘快照（纯文件写入，不碰 Streamlit）；
  2. 快照读写都不能把搜岗搞挂：文件坏了/过期/类型不对 → 当没有，不抛异常；
  3. 搜岗失败（比如"上一次还没跑完"被拒）**不能冲掉**上一份好结果；
  4. 页面读入口 pages_work._search_view()：session_state 空就回落到快照，
     并且能说清"这是上一次的结果"（restored=True + age_s + 关键词）。

跑法：python offeragent/test_last_search.py
"""
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 快照写到临时目录：测试绝不能碰真文件 offeragent/data/last_search.json
_TMP = tempfile.mkdtemp(prefix="oa_last_test_")
SNAP = os.path.join(_TMP, "last_search.json")
os.environ["JOBS_LAST_SEARCH"] = SNAP
os.environ["JOBS_CACHE"] = os.path.join(_TMP, "search_cache.json")

import job_sources as js  # noqa: E402
import streamlit as st  # noqa: E402
import pages_work as pw  # noqa: E402


ROWS = [{"title": "AI 岗 A", "company": "甲", "city": "南京", "salary": "",
         "url": "u1", "source": "甲平台", "extra": "", "jd": "",
         "match_hits": 1, "city_hit": True},
        {"title": "AI 岗 B", "company": "乙", "city": "南京", "salary": "",
         "url": "u2", "source": "甲平台", "extra": "", "jd": "",
         "match_hits": 1, "city_hit": True}]

RES = {"jobs": list(ROWS), "by_source": {"甲平台": 2}, "errors": {},
       "diag": {"甲平台": {"raw": 2}}, "cities": {"甲平台": [("南京", 2)]},
       "relaxed": {}, "city_miss": {}, "relaxed_all": False, "wants": ["南京"],
       "cache_hits": 0}


def write_snapshot(payload):
    with open(SNAP, "w", encoding="utf-8") as f:
        f.write(payload if isinstance(payload, str) else json.dumps(payload,
                                                                  ensure_ascii=False))


def test_save_load_roundtrip():
    """写进去再读出来：岗位、各来源命中、关键词、年龄都得对得上。"""
    ok = js.save_last_search(RES, "AI", "南京", ["甲平台"], True, 50, 1.5)
    snap = js.load_last_search()
    return (ok and len(snap["jobs"]) == 2 and snap["by_source"] == {"甲平台": 2}
            and snap["keyword"] == "AI" and snap["city"] == "南京"
            and snap["age_s"] >= 0 and snap["wants"] == ["南京"])


def test_ttl_and_broken_file():
    """过期 / 不是 JSON / 不是对象 / jobs 不是列表 —— 一律当"没有"，且不抛异常。"""
    write_snapshot({"t": time.time() - 100, "jobs": list(ROWS), "keyword": "旧"})
    expired_gone = js.load_last_search(ttl=30) == {}
    still_there = len(js.load_last_search(ttl=1000).get("jobs") or []) == 2
    write_snapshot("这不是 JSON")
    broken_ok = js.load_last_search() == {}
    write_snapshot([1, 2, 3])
    not_dict_ok = js.load_last_search() == {}
    write_snapshot({"t": time.time(), "jobs": "不是列表"})
    bad_jobs_ok = js.load_last_search() == {}
    return expired_gone and still_there and broken_ok and not_dict_ok and bad_jobs_ok


def test_search_all_writes_snapshot():
    """真跑一遍 search_all（假来源，离线）：返回前快照必须已经落盘。"""
    js.CACHE_ENABLED = False
    orig_search = js.search
    js.search = lambda src, kw, city="", ask_model=None, diag=None, **k: list(ROWS)
    try:
        res = js.search_all("AI", "南京", sources=["甲平台"], max_per_source=50)
    finally:
        js.search = orig_search
        js.CACHE_ENABLED = True
    snap = js.load_last_search()
    return (len(res["jobs"]) == 2 and len(snap.get("jobs") or []) == 2
            and snap["keyword"] == "AI" and snap["by_source"] == {"甲平台": 2}
            and snap["jobs"][0]["title"] == "AI 岗 A")


def test_failed_search_keeps_snapshot():
    """搜岗失败（闸被占着 → 直接拒绝）不能把上一份好结果冲掉。"""
    js.save_last_search(RES, "AI", "南京", ["甲平台"])
    js._SEARCH_LOCK.acquire()          # 模拟"上一次搜岗还在跑"
    raised = False
    try:
        try:
            js.search_all("B", "上海", sources=["甲平台"])
        except RuntimeError:
            raised = True
    finally:
        js._SEARCH_LOCK.release()
    snap = js.load_last_search()
    return raised and snap.get("keyword") == "AI" and len(snap.get("jobs") or []) == 2


def test_in_flight_flag():
    """界面靠这个判断"结果不是没有，是还在跑"。"""
    free_ok = js.search_in_flight() is False
    js._SEARCH_LOCK.acquire()
    try:
        busy_ok = js.search_in_flight() is True
    finally:
        js._SEARCH_LOCK.release()
    return free_ok and busy_ok


def test_page_view_falls_back_to_snapshot():
    """页面读入口：session_state 空 → 用快照；session_state 有 → 用当次的。"""
    js.save_last_search(RES, "AI", "南京", ["甲平台"])
    view = pw._search_view()                  # 这次运行没搜过，只有快照
    fallback_ok = (view["restored"] is True and len(view["jobs"]) == 2
                   and view["query"] == "AI" and view["age_s"] >= 0
                   and view["stats"] == {"甲平台": 2})
    st.session_state["sr_results"] = [{"title": "当次的", "source": "甲平台"}]
    st.session_state["sr_stats"] = {"甲平台": 1}
    view2 = pw._search_view()                 # 当次有结果：不能被快照顶替
    fresh_ok = (view2["restored"] is False and len(view2["jobs"]) == 1
                and view2["jobs"][0]["title"] == "当次的"
                and view2["stats"] == {"甲平台": 1})
    return fallback_ok and fresh_ok


def main():
    checks = [
        ("快照读写：岗位/各来源命中/关键词/年龄都对得上", test_save_load_roundtrip()),
        ("过期 / 坏文件 / 类型不对 → 当没有，不抛异常", test_ttl_and_broken_file()),
        ("search_all 返回前就把结果落了盘（假来源，离线）", test_search_all_writes_snapshot()),
        ("搜岗失败不冲掉上一份好结果", test_failed_search_keeps_snapshot()),
        ("search_in_flight 能分辨「在跑 / 没跑」", test_in_flight_flag()),
        ("页面读入口：session_state 空就从快照兜底，有就用当次的", test_page_view_falls_back_to_snapshot()),
    ]
    ok_n = sum(1 for _, v in checks if v)
    for name, good in checks:
        print(("✅ " if good else "❌ ") + name)
    print("\n%d/%d 通过" % (ok_n, len(checks)))
    return 0 if ok_n == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
