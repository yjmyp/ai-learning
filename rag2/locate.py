# -*- coding: utf-8 -*-
"""段落级引用定位：从命中的块里再挑出"真正回答问题的那句话"

为什么不能只给整块（chunk 级引用）：
  一块 300 字里有 4-5 句话，用户/面试官点开引用想核对的是**具体依据**，
  给一整块等于"自己去找"。句子级引用才是能核对的引用。

做法（纯本地、零依赖）：
  1. 把块按句末标点切句
  2. 每句按"和问题的词面重合度 / 句长惩罚 / 是否含数字与专有词"打分
  3. 返回最高分那句 + 它在块内的字符偏移（前端可以定位高亮）

和 rerank 的区别：rerank 决定"哪块"，locate 决定"块里哪句"——两级下钻。
"""
import re

from bm25 import tokenize

SENT_SPLIT = re.compile(r"(?<=[。！？!?；;])|(?<=\.\s)|(?<=\n)")
FACT_PAT = re.compile(r"\d")


def split_sentences(text):
    """切句并保留每句在原文中的偏移。"""
    out, pos = [], 0
    for piece in SENT_SPLIT.split(text or ""):
        if not piece:
            continue
        s = piece.strip()
        if not s:
            pos += len(piece)
            continue
        start = text.find(s, pos) if pos < len(text) else -1
        if start < 0:
            start = pos
        out.append({"text": s, "offset": start})
        pos = start + len(s)
    return out


def score_sentence(question, sentence):
    """句子对问题的支撑度：词面覆盖为主，长度和数字做微调。"""
    q = set(tokenize(question))
    s = set(tokenize(sentence))
    if not q or not s:
        return 0.0
    cover = len(q & s) / len(q)                 # 问题里的词有多少出现在这句
    length_pen = min(len(sentence), 120) / 120  # 太短的信息量低，太长的可能掺水
    fact_bonus = 0.15 if FACT_PAT.search(sentence) else 0.0   # 带数字的句子常常是依据
    return round(cover * 0.75 + length_pen * 0.10 + fact_bonus, 4)


def locate(question, chunk_text, min_score=0.25):
    """返回 {"quote", "offset", "score"}；都太低就返回整块的开头。"""
    sents = split_sentences(chunk_text)
    if not sents:
        return {"quote": (chunk_text or "")[:120], "offset": 0, "score": 0.0}
    best, best_score = sents[0], -1.0
    for s in sents:
        sc = score_sentence(question, s["text"])
        if sc > best_score:
            best, best_score = s, sc
    if best_score < min_score:
        return {"quote": (chunk_text or "")[:120], "offset": 0, "score": best_score}
    return {"quote": best["text"], "offset": best["offset"], "score": best_score}
