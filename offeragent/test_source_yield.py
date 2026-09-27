# -*- coding: utf-8 -*-
"""岗位数为什么这么少？——用真实抓取对比「改造前 / 改造后」的过滤逻辑。

跑法：python offeragent/test_source_yield.py
说明：需要联网。牛客不需要登录；BOSS 需要本机登录过（没登录会报未登录，属正常）。
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import job_sources as js  # noqa: E402


def old_logic_count(rows, kw, city):
    """旧逻辑：关键词或城市不命中就直接丢掉。"""
    kws = [k.lower() for k in js.split_terms(kw)]
    cities = js.split_terms(city)
    kept = []
    for r in rows:
        blob = f"{r.get('title', '')} {r.get('extra', '')} {r.get('city', '')}".lower()
        if kws and not any(k in blob for k in kws):
            continue
        if cities and not any(c in blob for c in cities):
            continue
        kept.append(r)
    return kept


def probe(kw, city):
    d = {}
    t0 = time.time()
    try:
        rows = js.search_nowcoder(kw, city, diag=d)
    except Exception as e:
        print(f"关键词={kw!r} 城市={city!r} → 抓取失败：{type(e).__name__} {str(e)[:80]}")
        return
    old = old_logic_count(rows, kw, city)
    print(f"关键词={kw!r} 城市={city!r}")
    print(f"   页面结构化岗位 {d.get('raw')} 条 → 现在返回 {len(rows)} 条"
          f"（旧逻辑只剩 {len(old)} 条）｜用时 {time.time() - t0:.1f}s")
    for r in rows[:3]:
        print(f"     · {r['title'][:22]:<24} {r['city']:<8} 命中 {r.get('match_hits')}")


def main():
    print("== 牛客：同一份数据，新旧过滤逻辑对比 ==")
    probe("AI", "南京")
    probe("AI", "")
    probe("AI 算法 大模型", "南京 上海")
    print()
    print("== 三个源合起来跑一遍（看 by_source / diag） ==")
    res = js.search_all("AI", "南京", ask_model=None)
    print("各平台条数：", res["by_source"])
    print("失败原因：", res["errors"])
    print("诊断：", res["diag"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
