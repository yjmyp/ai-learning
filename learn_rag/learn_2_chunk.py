# -*- coding: utf-8 -*-
"""
第 2 步：长文本 → 切成块（带重叠）

要看的：一篇几千字的文档，怎么变成一堆 300 字的块。
怎么做：python learn_rag\learn_2_chunk.py
"""
import os
import sys

RAG2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rag2"))
sys.path.insert(0, RAG2_DIR)

from chunker import chunk_text                          # noqa: E402
from config import CHUNK_OVERLAP, CHUNK_SIZE, DOCS_DIRS  # noqa: E402
from loader import load_documents                        # noqa: E402

docs = load_documents([DOCS_DIRS[0]])
doc = docs[0]
chunks = chunk_text(doc["text"], doc["source"], CHUNK_SIZE, CHUNK_OVERLAP)

print(f"一篇 {len(doc['text'])} 字的文档")
print(f"切成 {len(chunks)} 块（每块约 {CHUNK_SIZE} 字，重叠 {CHUNK_OVERLAP} 字）")
print(f"每块的字段：{list(chunks[0].keys())}\n")

for i, c in enumerate(chunks[:3]):
    print(f"--- 第 {i + 1} 块（{len(c['text'])} 字）---")
    print(c["text"][:90].replace("\n", " "))
    print()

# 亲眼验证"重叠"：上一块的尾巴，会出现在下一块的开头
a, b = chunks[0]["text"], chunks[1]["text"]
print("—— 验证重叠 ——")
print(f"第 1 块最后 {CHUNK_OVERLAP} 字：{a[-CHUNK_OVERLAP:]}")
print(f"第 2 块开头 {CHUNK_OVERLAP} 字：{b[:CHUNK_OVERLAP]}")
print("两边一样吗？", a[-CHUNK_OVERLAP:] == b[:CHUNK_OVERLAP])

print("\n—— 改动实验 ——")
print("把 CHUNK_SIZE 临时改成 150，先猜块数会变多还是变少，再跑一次")
