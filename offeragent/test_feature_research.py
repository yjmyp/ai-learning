# -*- coding: utf-8 -*-
"""扒一扒同类求职工具都有什么功能，给"还能加什么"做参考。"""
import base64
import re
import time
import urllib.parse

import requests

H = {"User-Agent": "codex"}

QUERIES = [
    "job application tracker", "AI interview prep", "resume tailoring LLM",
    "job search automation agent", "求职 管理 系统",
]


def search(q, n=4):
    u = ("https://api.github.com/search/repositories?q="
         + urllib.parse.quote(q) + f"&sort=stars&per_page={n}")
    try:
        return requests.get(u, headers=H, timeout=30).json().get("items", [])
    except Exception:
        return []


def readme(repo):
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/readme",
                         headers=H, timeout=30).json()
        return base64.b64decode(r["content"].replace("\n", "")).decode("utf-8", "ignore")
    except Exception:
        return ""


def features(text, limit=14):
    """从 README 里挑出像功能点儿的行。"""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith(("- ", "* ", "• ")):
            continue
        s = re.sub(r"[*`_]", "", s[2:]).strip()
        if not (6 <= len(s) <= 90):
            continue
        if re.search(r"(install|npm|pip|docker|clone|yarn|http|license|目录)", s, re.I):
            continue
        out.append(s)
        if len(out) >= limit:
            break
    return out


if __name__ == "__main__":
    seen = set()
    for q in QUERIES:
        print("=" * 72)
        print("搜索：", q)
        for it in search(q):
            full = it["full_name"]
            if full in seen:
                continue
            seen.add(full)
            print(f"\n▌{full}  ({it.get('stargazers_count')}⭐)")
            print(f"  {it.get('description') or ''}"[:110])
            for f in features(readme(full), 10):
                print("   ·", f)
            time.sleep(0.5)
