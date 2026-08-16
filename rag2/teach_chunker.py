# -*- coding: utf-8 -*-
"""教学脚本：看 chunker 一步步切块（跑：python rag2/teach_chunker.py）"""
import re


def _split_long(paragraph, chunk_size):
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


def chunk_text_debug(text, chunk_size, overlap):
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, buf, buf_len = [], [], 0
    print("分段结果：")
    for i, p in enumerate(paragraphs, 1):
        print(f"  段{i}：'{p}'（{len(p)} 字）")
    print()

    for idx, para in enumerate(paragraphs, 1):
        print(f"=== 处理第 {idx} 段：'{para}'（{len(para)} 字）===")
        if len(para) > chunk_size:
            print(f"  -> 超长段（>{chunk_size}字），走独立切分")
            if buf:
                print(f"  ① 先封口：块 = {buf}")
                chunks.append("\n".join(buf))
                buf, buf_len = [], 0
            pieces = _split_long(para, chunk_size)
            print(f"  ② _split_long 切成 {len(pieces)} 块：{pieces}")
            for sub in pieces:
                chunks.append(sub)
            print(f"  ③ 当前已存块数：{len(chunks)}")
            print()
            continue

        if buf and buf_len + len(para) + 1 > chunk_size:
            print(f"  -> 篮子({buf_len}字) + 本段({len(para)}字) + 1 超过 {chunk_size}，封口")
            print(f"  ① 存块：{buf}")
            chunks.append("\n".join(buf))
            tail = buf[-1] if buf else ""
            tail = tail[-overlap:] if len(tail) > overlap else tail
            print(f"  ② 新篮子带上尾巴：'{tail}'（{len(tail)} 字）")
            buf, buf_len = ([tail] if tail else []), len(tail)
        buf.append(para)
        buf_len += len(para) + 1
        print(f"  -> 放进篮子：{buf}，篮子字数={buf_len}")
        print()

    if buf:
        print("=== 结束：篮子还有货，封口 ===")
        chunks.append("\n".join(buf))

    print()
    print("========== 最终结果 ==========")
    for i, c in enumerate(chunks, 1):
        print(f"块{i}（{len(c)}字）：{c}")


if __name__ == "__main__":
    demo = "今天天气很好。\n\n我们一起去公园。\n\n公园里有花有树。\n\n还有一条小河。"
    chunk_text_debug(demo, chunk_size=12, overlap=4)
