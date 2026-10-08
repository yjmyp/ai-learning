# -*- coding: utf-8 -*-
"""答案级自检：检索到的不等于能回答

为什么需要（评估集实测出来的）：
  "Calix 2025 年营收是多少"这种**难负例**，覆盖率门禁拦不住——问题里的
  "Calix"确实出现在资料里，词面覆盖率不低；但资料里**没有营收数字**。
  纯统计信号区分不了"词都命中但答案不存在"，只能让模型读一遍片段做判断。

做法：把 top-k 片段给模型，只问一个问题——"这些片段里有没有能回答该问题的内容？"
要求它输出 JSON（answerable / evidence / missing），
  · answerable=false → 上层直接拒答（不生成答案，避免编）
  · answerable=true  → 顺带拿到 evidence 句子，可以直接当引用展示

代价：每问一次多 1 次 LLM 调用（约 1 秒）。所以它放在"统计门禁通过之后"，
只对**已经召回成功**的问题做，属于最后一道质量闸门。
"""
import json
import re

# 只对"要具体事实/数值"的问题做自检 —— 这类问题最容易"词都命中但答案不存在"。
# 概念解释类问题（什么是 X / 怎么用）很少出现这种失败，自检只会白白增加误拒和调用。
FACT_PAT = re.compile(
    r"多少|几[个号年月天次家]|哪年|哪一年|什么时候|几点|价格|薪资|月薪|营收|"
    r"收入|参数|多大|多久|几天|数量|排名|第几|比例|百分比|几个百分点"
)


def needs_check(question):
    """这个问题值不值得花一次 LLM 调用做答案级自检。"""
    return bool(FACT_PAT.search(question or ""))


CHECK_PROMPT = """下面有若干资料片段，和一个用户问题。请判断：**这些片段里是否包含能回答问题所需的信息**。

只输出 JSON，不要解释、不要代码块：
{{"answerable": true 或 false, "evidence": "如果 true，抄一句能直接支撑答案的原文；否则空串", "missing": "如果 false，用一句话说缺什么信息；否则空串"}}

用户问题：{q}

资料片段：
{ctx}
"""


def assess(question, hits, ask_model, max_chars=1200):
    """返回 (answerable, evidence, missing)。调用失败时按"可回答"放行（宁可多答也别错杀）。"""
    if not hits or ask_model is None:
        return True, "", ""
    if not needs_check(question):
        return True, "", ""          # 概念类问题跳过自检：省一次调用、也不误杀
    ctx = "\n".join("[%d] %s" % (i, (h.get("text") or "")[:400])
                    for i, h in enumerate(hits[:4], start=1))[:max_chars]
    try:
        raw = ask_model(CHECK_PROMPT.format(q=question, ctx=ctx)) or ""
    except Exception:
        return True, "", ""
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return True, "", ""
    try:
        d = json.loads(m.group(0))
    except Exception:
        return True, "", ""
    return bool(d.get("answerable", True)), str(d.get("evidence", "")), \
        str(d.get("missing", ""))
