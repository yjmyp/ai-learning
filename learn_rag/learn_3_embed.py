# -*- coding: utf-8 -*-
"""
第 3 步：文本 → 向量（数字数组）

要看的：为什么"向量相近 = 意思相近"。
怎么做：python learn_rag\learn_3_embed.py
"""
import os
import sys

RAG2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rag2"))
sys.path.insert(0, RAG2_DIR)

# 顺序很重要：先导 config（打开离线开关），再导 embedder。
# 反了的话，加载模型时会去连 HuggingFace，网络不通就卡死（踩过的坑）。
from config import EMBED_MODEL  # noqa: E402,F401
from embedder import Embedder   # noqa: E402

texts = [
    "什么是 RAG？",
    "RAG 是什么东西",
    "今天南京天气不错",
]

emb = Embedder()
vecs = emb.encode(texts)

print(f"输入 {len(texts)} 段文字，得到 {len(vecs)} 个向量")
print(f"每个向量多少维：{len(vecs[0])}")
print(f"第一个向量前 5 个数：{[round(v, 3) for v in vecs[0][:5]]}\n")


def cosine(a, b):
    """向量已归一化，所以点积就是余弦相似度"""
    return sum(x * y for x, y in zip(a, b))


print("—— 关键对比 ——")
print(f"『什么是 RAG？』 vs 『RAG 是什么东西』   相似度 {cosine(vecs[0], vecs[1]):.4f}")
print(f"『什么是 RAG？』 vs 『今天南京天气不错』 相似度 {cosine(vecs[0], vecs[2]):.4f}")

print("\n—— 改动实验 ——")
print("把第三句换成另一句和 RAG 无关的话，看相似度是不是仍然很低")
print("再把第二句换成完全一样的『什么是 RAG？』，看相似度是不是 1.0")
