# -*- coding: utf-8 -*-
"""第1周运营：牛客搜岗 → 筛选（南京 + AI应用/Agent + 非嵌入式）→ 入库。"""
import sys, io
sys.path.insert(0, r"C:\Users\29947\Documents\Codex\ai-learning")
sys.path.insert(0, r"C:\Users\29947\Documents\Codex\ai-learning\offeragent")
from job_sources import search
from store import save_new_job, list_jobs

out = []
jobs = search("牛客", "AI 应用开发", city="南京")
out.append(f"牛客抓到 {len(jobs)} 条")

seen = set()
added = []
for j in jobs:
    title = j.get("title", "")
    city = j.get("city", "")
    url = j.get("url", "")
    jd = j.get("jd", "")
    # 筛选：南京 + 排除嵌入式/硬件向
    if city != "南京":
        continue
    if "嵌入式" in jd or "单片机" in jd or "PCB" in jd:
        continue
    if url in seen:
        continue
    seen.add(url)
    # 岗位名唯一：title + url 数字后缀
    jid = url.rstrip("/").split("/")[-1]
    name = f"{title}-{jid}"
    company = j.get("company", "")
    salary = j.get("salary", "")
    extra = {"company": company, "salary": salary, "source": "牛客",
             "title_raw": title, "extra": j.get("extra", "")}
    msg = save_new_job(name, city, jd, source_url=url, extra=extra)
    added.append(f"  + {name}  {salary}  {url}")
    out.append(f"  {msg} | {salary} | {url}")

out.append(f"\n本次新增 {len(added)} 个岗位；岗位库现有 {len(list_jobs())} 个")
io.open(r"C:\Users\29947\Documents\Codex\ai-learning\_import_jobs.txt", "w", encoding="utf-8").write("\n".join(out))
