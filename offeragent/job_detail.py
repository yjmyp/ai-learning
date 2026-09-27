# -*- coding: utf-8 -*-
"""
job_detail · 岗位档案与筛选依据（可解释性）
============================================
商业化产品的一个硬指标：**用户要能看懂"为什么这个岗位出现在我的列表里"。**

这个模块把一件事说清楚，分三段：
  1. 它是怎么进来的（来源平台、搜索关键词、命中原因、入库时间）
  2. 它为什么被保留 / 被排除（质量检查逐项 + 排除规则命中的原文）
  3. 它到底要什么人（岗位职责 / 任职要求 结构化展示，不是一坨文本）
"""
import re

DUTY_ANCHORS = ["岗位职责", "职位描述", "工作内容", "工作职责", "你将负责",
                "职位介绍", "岗位描述", "职责描述", "Job Description"]
REQ_ANCHORS = ["任职要求", "任职资格", "岗位要求", "职位要求", "我们希望你",
               "任职条件", "资格要求", "Requirements"]


def split_jd(jd: str) -> dict:
    """把 JD 文本按锚点切成 职责 / 要求 / 其他 三块。"""
    text = (jd or "").replace("\r", "")
    lines = text.split("\n")
    sections = {"duty": [], "req": [], "other": []}
    cur = "other"
    for line in lines:
        s = line.strip()
        head = s[:12]
        if any(a in head for a in DUTY_ANCHORS):
            cur = "duty"
            rest = re.sub("|".join(DUTY_ANCHORS), "", s).lstrip("：: ")
            if rest:
                sections[cur].append(rest)
            continue
        if any(a in head for a in REQ_ANCHORS):
            cur = "req"
            rest = re.sub("|".join(REQ_ANCHORS), "", s).lstrip("：: ")
            if rest:
                sections[cur].append(rest)
            continue
        if s:
            sections[cur].append(s)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def entry_reasons(meta: dict) -> list:
    """这个岗位是怎么进来的。返回 [ {label, detail} ]"""
    out = []
    src = meta.get("source") or "手动导入"
    out.append({"label": "来源", "detail": src})
    if meta.get("search_query"):
        kw = meta["search_query"]
        hit = []
        if kw.lower() in (meta.get("title") or "").lower():
            hit.append("岗位名里有这个关键词")
        if kw.lower() in (meta.get("skills") or "").lower():
            hit.append("技能标签命中")
        if kw in (meta.get("city") or ""):
            hit.append("城市命中")
        out.append({"label": "搜索关键词", "detail": kw})
        out.append({"label": "命中原因",
                    "detail": "；".join(hit) if hit else "平台搜索结果里返回了它（未做本地二次过滤）"})
    if meta.get("created_at"):
        out.append({"label": "入库时间", "detail": str(meta["created_at"])})
    if meta.get("source_url"):
        out.append({"label": "原始链接", "detail": str(meta["source_url"])})
    return out


def keep_or_drop(meta: dict) -> list:
    """为什么保留 / 为什么排除。返回 [ {label, detail, ok} ]"""
    out = []
    if meta.get("status") == "排除":
        out.append({"label": "排除原因",
                    "detail": meta.get("excluded_reason") or "手动排除",
                    "ok": False})
        ev = meta.get("excluded_evidence")
        if ev:
            out.append({"label": "命中原文",
                        "detail": f"「{ev}」", "ok": False})
    q = meta.get("quality")
    if isinstance(q, dict):
        out.append({"label": "岗位质量分",
                    "detail": f"{q.get('score')} 分 · {q.get('verdict')}", "ok": True})
        for f in q.get("flags", []):
            out.append({"label": f"扣分项：{f.get('problem')}",
                        "detail": f"{f.get('evidence')}（-{f.get('penalty')} 分）",
                        "ok": False})
        if not q.get("flags"):
            out.append({"label": "质量检查", "detail": "7 项检查都没发现问题", "ok": True})
    else:
        out.append({"label": "岗位质量", "detail": "还没跑过质量检查", "ok": None})
    if meta.get("match_score") is not None:
        out.append({"label": "匹配度", "detail": f"{meta['match_score']}%", "ok": True})
    return out
