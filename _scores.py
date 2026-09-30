# -*- coding: utf-8 -*-
"""汇总岗位库所有 meta.json 的匹配分与状态。"""
import json, os

d = r"C:\Users\29947\Documents\Codex\ai-learning\offeragent\data\jds"
rows = []
for f in sorted(os.listdir(d)):
    if f.endswith(".meta.json"):
        try:
            m = json.load(open(os.path.join(d, f), encoding="utf-8"))
        except Exception:
            continue
        rows.append((m.get("match_score"), m.get("company") or m.get("name") or f, m.get("status", ""), f))
rows.sort(key=lambda x: -(x[0] if isinstance(x[0], (int, float)) else -1))
out = []
for score, company, status, f in rows:
    out.append(f"{score if score is not None else 'None':>4}  {company:<12} {status:<6} {f}")
open(r"C:\Users\29947\Documents\Codex\ai-learning\_scores.txt", "w", encoding="utf-8").write("\n".join(out))
