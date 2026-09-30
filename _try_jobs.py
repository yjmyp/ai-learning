# -*- coding: utf-8 -*-
"""第1周运营·试搜岗：牛客 + 实习僧（公开页面）。"""
import sys, io
sys.path.insert(0, r"C:\Users\29947\Documents\Codex\ai-learning")
sys.path.insert(0, r"C:\Users\29947\Documents\Codex\ai-learning\offeragent")
from job_sources import search

out = []
for source in ["牛客", "实习僧"]:
    try:
        jobs = search(source, "AI 应用开发", city="南京")
        out.append(f"== {source}: 抓到 {len(jobs)} 条 ==")
        for j in jobs[:8]:
            out.append(f"  - {j}")
    except Exception as e:
        out.append(f"== {source}: 失败 {type(e).__name__}: {str(e)[:200]} ==")
io.open(r"C:\Users\29947\Documents\Codex\ai-learning\_jobs_out.txt", "w", encoding="utf-8").write("\n".join(out))
