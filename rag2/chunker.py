# -*- coding: utf-8 -*-
"""文本切分：按段落贪心打包成块，块间带重叠，保留来源"""
import re


def _split_long(paragraph, chunk_size):
    """超长段落按句末标点切开，必要时硬切"""
    parts = re.split(r"(?<=[。！？；])", paragraph)
    pieces, cur = [], ""
    for part in parts:
        if len(part) > chunk_size:
            if cur:
                pieces.append(cur)
                cur = ""
            for i in range(0, len(part), chunk_size):
                pieces.append(part[i:i + chunk_size])
        elif cur and len(cur) + len(part) > chunk_size:
            pieces.append(cur)
            cur = part
        else:
            cur += part
    if cur:
        pieces.append(cur)
    return pieces


def chunk_text(text, source, chunk_size=300, overlap=50):
    """把一篇文档切成块，每块约 chunk_size 字，相邻块保留 overlap 字重叠。
    策略：空行分段 → 贪心合并段落 → 块满后把上一段尾巴带进下一块。"""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, buf, buf_len = [], [], 0

    for para in paragraphs:
        if len(para) > chunk_size:
            if buf:
                chunks.append("\n".join(buf))
                buf, buf_len = [], 0
            for sub in _split_long(para, chunk_size):
                chunks.append(sub)
            continue

        if buf and buf_len + len(para) + 1 > chunk_size:
            chunks.append("\n".join(buf))
            tail = buf[-1] if buf else ""
            tail = tail[-overlap:] if len(tail) > overlap else tail
            buf, buf_len = ([tail] if tail else []), len(tail)

        buf.append(para)
        buf_len += len(para) + 1

    if buf:
        chunks.append("\n".join(buf))

    return [{"text": c, "source": source} for c in chunks if c.strip()]
