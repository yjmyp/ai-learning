# -*- coding: utf-8 -*-
"""测试几个公开岗位源能不能抓（判断阶段 4 该接哪些源）。"""
import re
import sys

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
H = {"User-Agent": UA}

SOURCES = [
    ("实习僧", "https://www.shixiseng.com/interns?keyword=AI&city=%E5%8D%97%E4%BA%AC"),
    ("应届生求职网", "https://s.yingjiesheng.com/search.php?word=AI&sort=score"),
    ("牛客实习中心", "https://www.nowcoder.com/jobs/intern/center"),
    ("BOSS直聘搜索", "https://www.zhipin.com/web/geek/job?query=AI&city=101190100"),
    ("南大就业网", "https://job.nju.edu.cn/"),
    ("南邮就业网", "https://jiuye.njupt.edu.cn/"),
]


def probe(name: str, url: str):
    try:
        r = requests.get(url, headers=H, timeout=20)
        text = r.text
        has_kw = "实习" in text or "招聘" in text
        # 粗略数一下有没有像岗位链接的东西
        links = len(re.findall(r'href="[^"]*(?:job|intern|position)[^"]*"', text, re.I))
        print(f"{name:<14} HTTP {r.status_code} | {len(text):>7} 字节 | "
              f"含关键词 {has_kw} | 疑似岗位链接 {links}")
        return r.status_code == 200 and links > 0
    except Exception as e:
        print(f"{name:<14} 失败: {type(e).__name__}: {str(e)[:60]}")
        return False


if __name__ == "__main__":
    print("探测公开岗位源（能不能直接抓）：\n")
    ok = []
    for name, url in SOURCES:
        if probe(name, url):
            ok.append(name)
    print("\n可直接抓的源：", ok if ok else "无")
