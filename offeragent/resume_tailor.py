# -*- coding: utf-8 -*-
"""
resume_tailor · 按 JD 定制简历 + ATS 关键词覆盖检查
====================================================
两步：
  1. 用大模型从 JD 里抽关键词（技术 / 职责 / 加分），然后**在本地**检查简历覆盖情况
     —— 覆盖检查是字符串比对，不让模型判断，避免它"觉得"覆盖了
  2. 让模型给重排与改写建议，但**写死"只能用简历里已有的经历和数字"**，
     JD 要求而简历没有的，必须写"缺失，需用户确认"，不许替他补
"""
import re

KEYWORD_PROMPT = """从下面的岗位 JD 里抽关键词，分三类，每类最多 12 个，用顿号分隔：
技术：编程语言、框架、工具、平台名（如 Python、RAG、Chroma、FastAPI）
职责：要做的事（如 检索优化、数据清洗、接口开发、效果评估）
加分：明显是加分的项（如 论文复现、开源贡献、英文文档、大模型微调）

严格按三行输出，格式：
技术：xxx、xxx
职责：xxx、xxx
加分：xxx、xxx
不要解释，不要多余文字。

岗位 JD：
"""

TAILOR_PROMPT = """你在帮一个学生按目标岗位调整简历。下面是他的简历和目标 JD。

硬性要求（违反即失败）：
1. 只能使用简历里已经出现的经历、项目和数字。不许新增经历、不许夸大、不许编造。
2. 你给的是"重排和改写建议"，不是在写新简历。
3. JD 要求但简历里没有的，必须明确写"简历缺这块，需要你确认是否真的有"，不要替他补。
4. 每条建议都要引用依据（简历里的哪句话 / JD 里的哪句话）。

严格按下面三个分隔符输出，分隔符单独一行：

=== cover.md ===
用表格列出 JD 关键词的覆盖情况，三列：关键词 | 状态（已覆盖/部分覆盖/缺失）| 依据

=== reorder.md ===
简历条目的重排建议：按与这个 JD 的相关度给建议顺序，每条格式：条目名 → 建议位置 → 理由

=== bullets.md ===
挑最相关的 2 到 3 条经历，给改写后的 bullet 建议（每条不超过 25 字）。
只重排已有信息、突出与 JD 呼应的部分；每条后面用括号注明"原文依据：xxx"。

【简历】
"""


def extract_keywords(jd: str, ask_model) -> dict:
    """从 JD 抽关键词。返回 {"技术": [...], "职责": [...], "加分": [...]}"""
    out = ask_model(KEYWORD_PROMPT + jd) or ""
    result = {"技术": [], "职责": [], "加分": []}
    for line in out.splitlines():
        line = line.strip().lstrip("*-· ").strip()
        for key in result:
            if line.startswith(key):
                raw = re.sub(r"^" + key + r"[：:]\s*", "", line)
                items = [x.strip() for x in re.split(r"[、,，/]", raw) if x.strip()]
                result[key] = items[:12]
    return result


def check_coverage(resume: str, keywords: dict) -> list:
    """本地检查覆盖情况（纯字符串比对，不交给模型判断）。"""
    low = resume.lower()
    rows = []
    for cat, words in keywords.items():
        for w in words:
            wl = w.lower().strip()
            if not wl:
                continue
            if wl in low:
                status = "已覆盖"
            elif any(part in low for part in re.split(r"[\s/、]+", wl) if len(part) >= 3):
                status = "部分覆盖"
            else:
                status = "缺失"
            rows.append({"keyword": w, "category": cat, "status": status})
    return rows


def coverage_rate(rows: list) -> float:
    """已覆盖 + 部分覆盖算半分，返回百分比。"""
    if not rows:
        return 0.0
    score = sum(1.0 if r["status"] == "已覆盖" else
                (0.5 if r["status"] == "部分覆盖" else 0.0) for r in rows)
    return round(score / len(rows) * 100, 1)


def split_three(text: str) -> dict:
    """按 === xxx === 切三段。"""
    names = ["cover.md", "reorder.md", "bullets.md"]
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("===") and s.endswith("==="):
            if cur:
                out[cur] = "\n".join(buf).strip()
            inner = s.strip("= ").strip()
            cur = inner if inner in names else None
            buf = []
            continue
        if cur:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf).strip()
    return out


def tailor(resume: str, jd: str, ask_model) -> dict:
    """跑一次定制，返回 {"keywords", "coverage", "rate", "advice"}"""
    keywords = extract_keywords(jd, ask_model)
    coverage = check_coverage(resume, keywords)
    text = ask_model(TAILOR_PROMPT + resume + "\n\n【目标 JD】\n" + jd) or ""
    return {
        "keywords": keywords,
        "coverage": coverage,
        "rate": coverage_rate(coverage),
        "advice": split_three(text),
    }
