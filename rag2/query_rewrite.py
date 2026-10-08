# -*- coding: utf-8 -*-
"""查询改写：把一个提问扩成多个检索式，再融合结果（Multi-Query / HyDE 简化版）

为什么需要：
  用户问"RAG 怎么保证不胡说"，资料里写的可能是"减少幻觉 / 强制依据资料回答"，
  字面几乎不重叠。单条查询召回不到，多改写几条就有一条能命中。
  这是提升检索质量最便宜的一招：一次 LLM 调用，换来 2~3 条互补检索式。

两种策略（离线没有 key 时都优雅降级为"原问题"）：
  · multi-query：生成 3 条不同措辞 / 不同切入点的检索式
  · hyde：先让模型写一段"假如答案存在会长什么样"的假答案，用假答案去检索
    （HyDE, Gao et al. 2022：假答案与真文档的向量距离通常比问题更近）
"""
import re

MULTI_QUERY_PROMPT = """你是检索助手。用户要在一个中文知识库里找资料，请把他的问题改写成 3 条不同的检索式。

要求：
1. 每条换一个说法或切入角度（同义词、上位概念、可能出现在资料里的术语）
2. 不要回答问题，只给检索式
3. 每行一条，不要编号，不要解释，不要引号

用户问题：{q}
"""

HYDE_PROMPT = """假如下面这个问题在资料里有答案，那段答案大概会怎么写？
请用 2-3 句话写出来（中文，像资料原文那样陈述）。不要提"资料""假设"，直接写内容。

问题：{q}
"""


def _clean_lines(raw, limit=3):
    out = []
    for line in (raw or "").splitlines():
        s = re.sub(r"^\s*[-*\d.、)）]+\s*", "", line).strip().strip('"“”')
        if 2 <= len(s) <= 80:
            out.append(s)
    seen, uniq = set(), []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq[:limit]


def multi_query(question, ask_model=None, n=3):
    """返回 [原问题, 改写1, 改写2, ...]；没有模型就只返回原问题。"""
    if ask_model is None:
        return [question]
    try:
        raw = ask_model(MULTI_QUERY_PROMPT.format(q=question))
    except Exception:
        return [question]
    extra = _clean_lines(raw, limit=n)
    return [question] + [q for q in extra if q != question]


def hyde(question, ask_model=None):
    """返回假答案文本；没有模型或失败就返回空串（调用方自动跳过）。"""
    if ask_model is None:
        return ""
    try:
        raw = (ask_model(HYDE_PROMPT.format(q=question)) or "").strip()
    except Exception:
        return ""
    return raw[:400]
