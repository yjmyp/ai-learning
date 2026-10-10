# -*- coding: utf-8 -*-
"""搜岗升级验收：城市归一 + 真过滤 + 多来源合并（不用联网）

用户反馈的原话是"填了城市但搜出来的对不上"，根因是**城市只影响排序、没做过滤**。
这个测试把新的城市语义钉死：归一化、多城市、远程、严格过滤、无命中时自动放宽。

跑法：python offeragent/test_job_search.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import job_sources as js  # noqa: E402

js.CACHE_ENABLED = False   # 下面是假数据，绝不能写进真缓存文件（否则真搜岗会捞到假岗位）


def fake_search(src, keyword, city="", ask_model=None, diag=None, **kwargs):
    """假的来源：甲平台有南京岗，乙平台全是深圳岗。

    **kwargs 必须留着：search_all 会额外传 max_items（每源抓取上限）。
    不接它，测试就会 TypeError —— 这正是"改了调用签名忘了改假实现"的典型翻车。
    """
    if diag is not None:
        diag["raw"] = 2
    if src == "甲平台":
        return [{"title": "AI 岗 A", "company": "南京公司", "city": "南京", "salary": "",
                 "url": "u1", "source": src, "extra": "", "jd": "", "match_hits": 1, "city_hit": True},
                {"title": "AI 岗 B", "company": "上海公司", "city": "上海", "salary": "",
                 "url": "u2", "source": src, "extra": "", "jd": "", "match_hits": 1, "city_hit": False}]
    return [{"title": "AI 岗 C", "company": "深圳公司", "city": "深圳", "salary": "",
             "url": "u3", "source": src, "extra": "", "jd": "", "match_hits": 1, "city_hit": False}]


def main():
    checks = []

    # 1) 城市归一
    cases = [("南京市", "南京"), ("江苏南京", "南京"), ("魔都", "上海"),
             ("remote", "远程"), ("  苏州 ", "苏州")]
    ok = all(js.norm_city(a) == b for a, b in cases)
    checks.append(("城市归一（南京市/江苏南京/魔都/remote/带空格）", ok))
    checks.append(("多城市拆分 南京 上海 remote",
                   js.want_cities("南京 上海 remote") == ["南京", "上海", "远程"]))

    # 2) 城市命中判断（含多城市字段与远程）
    hits = [js.city_hit("南京", ["南京"]) is True,
            js.city_hit("南京/上海", ["上海"]) is True,
            js.city_hit("深圳", ["南京"]) is False,
            js.city_hit("Anywhere", ["远程"]) is True,
            js.city_hit("", ["南京"]) is False,
            js.city_hit("深圳", []) is True]        # 不填城市 = 全都要
    checks.append(("城市命中判断 6 个边界", all(hits)))

    # 3) 严格模式：真的过滤掉不匹配的（这是用户最在意的那条）
    js.search = fake_search
    r = js.search_all("AI", "南京", sources=["甲平台", "乙平台"], strict_city=True)
    got = [(j["source"], j["city"]) for j in r["jobs"]]
    checks.append(("严格模式只留南京（%s）" % got, got == [("甲平台", "南京")]))
    checks.append(("记录被过滤数量（%s）" % r["relaxed"], r["relaxed"].get("甲平台") == 1))
    checks.append(("记录「该平台没有此城市」（%s）" % r["city_miss"], r["city_miss"].get("乙平台") == 1))

    # 4) 放宽模式：城市仍排在前面，但不丢数据
    r2 = js.search_all("AI", "南京", sources=["甲平台", "乙平台"], strict_city=False)
    checks.append(("放宽模式保留全部（%d 条）且南京排第一" % len(r2["jobs"]),
                   len(r2["jobs"]) == 3 and r2["jobs"][0]["city"] == "南京"))

    # 5) 所有来源都没有该城市 → 自动放宽并标记
    r3 = js.search_all("AI", "拉萨", sources=["甲平台", "乙平台"], strict_city=True)
    checks.append(("全无命中时自动放宽并标记（relaxed_all=%s, %d 条）"
                   % (r3["relaxed_all"], len(r3["jobs"])), r3["relaxed_all"] and len(r3["jobs"]) == 3))

    # 6) 来源清单：免登录的都在，且默认就是它们
    checks.append(("默认来源都是免登录的（%s）" % js.NO_LOGIN_SOURCES,
                   all(s in js.SOURCES for s in js.NO_LOGIN_SOURCES)
                   and "BOSS直聘" not in js.NO_LOGIN_SOURCES))

    # 7) 去重口径（实测证据：同公司同名岗位分布在 10 个城市，按"名+公司"去重会把 280 条砍成 79 条）
    a = {"title": "AI应用开发", "company": "墨泊可士", "city": "南京", "url": "u1"}
    b = {"title": "AI应用开发", "company": "墨泊可士", "city": "杭州", "url": "u2"}
    c2 = {"title": "AI应用开发", "company": "墨泊可士", "city": "南京", "url": "u3"}
    checks.append(("去重：同城同公司同岗位合并、不同城市各留一条",
                   js.dedup_key(a) == js.dedup_key(c2) and js.dedup_key(a) != js.dedup_key(b)))
    n1 = {"title": "AI应用开发", "company": "", "city": "南京", "url": "x1"}
    n2 = {"title": "AI应用开发", "company": "", "city": "南京", "url": "x2"}
    checks.append(("去重：公司名缺失时按 URL 兜底、不误合并同名岗位",
                   js.dedup_key(n1) != js.dedup_key(n2)))

    ok_n = sum(1 for _, v in checks if v)
    for name, good in checks:
        print(("✅ " if good else "❌ ") + name)
    print("\n%d/%d 通过" % (ok_n, len(checks)))
    return 0 if ok_n == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
