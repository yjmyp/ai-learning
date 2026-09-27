# -*- coding: utf-8 -*-
"""看实习僧 / 牛客 的页面里，岗位数据藏在哪个 JSON 里。"""
import json
import re

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
H = {"User-Agent": UA}


def peek(d, depth=0, path="$"):
    if depth > 3:
        return
    if isinstance(d, dict):
        for k, v in list(d.items())[:8]:
            if isinstance(v, (dict, list)):
                print("    " + "  " * depth + f"{path}.{k} ({type(v).__name__}, {len(v)})")
                peek(v, depth + 1, f"{path}.{k}")
            else:
                print("    " + "  " * depth + f"{path}.{k} = {str(v)[:40]}")
    elif isinstance(d, list) and d:
        peek(d[0], depth + 1, f"{path}[0]")


def show(name, url, patterns):
    print("=" * 70)
    print(name)
    try:
        r = requests.get(url, headers=H, timeout=25)
        text = r.text
    except Exception as e:
        print("  请求失败:", type(e).__name__)
        return
    for label, pat in patterns:
        m = re.search(pat, text, re.S)
        if not m:
            print(f"  [{label}] 没找到")
            continue
        raw = m.group(1)
        print(f"  [{label}] 命中，长度 {len(raw)}")
        try:
            peek(json.loads(raw))
        except Exception as e:
            print("    JSON 解析失败:", str(e)[:80])
            print("    预览:", raw[:200])


if __name__ == "__main__":
    # 牛客：看岗位字段结构
    print("=" * 70)
    print("牛客 jobList 第一条的字段")
    try:
        r = requests.get("https://www.nowcoder.com/jobs/intern/center",
                         headers=H, timeout=25)
        m = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;', r.text, re.S)
        data = json.loads(m.group(1))
        jobs = data["store"]["interCenter"]["jobList"]
        print(f"  共 {len(jobs)} 条，第一条字段：")
        for k, v in jobs[0].items():
            print(f"    {k} = {str(v)[:60]}")
        print("\n  前三条标题：")
        for j in jobs[:3]:
            print("   -", j.get("jobName"), "|", j.get("companyName"), "|",
                  j.get("cityName"), "|", j.get("salaryDesc") or j.get("salaryMin"))
    except Exception as e:
        print("  失败:", type(e).__name__, str(e)[:100])

    # 实习僧：找链接和 JSON 脚本
    print("\n" + "=" * 70)
    print("实习僧页面结构探测")
    try:
        r = requests.get("https://www.shixiseng.com/interns?keyword=AI&city=%E5%8D%97%E4%BA%AC",
                         headers=H, timeout=25)
        t = r.text
        print("  状态", r.status_code, "长度", len(t))
        ids = re.findall(r'<script[^>]*id="([^"]+)"', t)
        print("  script id：", ids[:10])
        hrefs = re.findall(r'href="(/intern/[^"]+)"', t)
        print(f"  /intern/ 链接数：{len(hrefs)}，前三个：{hrefs[:3]}")
        if not hrefs:
            hrefs2 = re.findall(r'href="([^"]*intern[^"]*)"', t)
            print(f"  含 intern 的链接数：{len(hrefs2)}，前三个：{hrefs2[:3]}")
    except Exception as e:
        print("  失败:", type(e).__name__, str(e)[:100])
