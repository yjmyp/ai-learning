# -*- coding: utf-8 -*-
"""
第 4 步：向量存进库 → 用问题去查

要看的：库里存了什么、查出来是什么、距离怎么变成相似度。
怎么做：python learn_rag\learn_4_store.py
"""
import os
import sys

RAG2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rag2"))
sys.path.insert(0, RAG2_DIR)

from config import CHROMA_DIR, COLLECTION_NAME  # noqa: E402
from embedder import Embedder                   # noqa: E402
from store import VectorStore                   # noqa: E402

store = VectorStore(CHROMA_DIR, COLLECTION_NAME)
print(f"库里现在有 {store.count()} 块")

question = "什么是 RAG？"
print(f"\n拿这个问题去查：{question}")

qvec = Embedder().encode([question])[0]
res = store.query(qvec, n_results=3)

# query 返回的是"平行列表"：第 i 条结果 = documents[0][i] + metadatas[0][i] + distances[0][i]
print("\n查出来最像的 3 块：")
for i in range(len(res["ids"][0])):
    dist = res["distances"][0][i]
    meta = res["metadatas"][0][i] or {}
    text = res["documents"][0][i]
    print(f"[{i + 1}] 距离 {dist:.4f} → 相似度 {1 - dist:.4f}　来源 {meta.get('source', '?')}")
    print("    " + text[:70].replace("\n", " "))

print("\n—— 改动实验 ——")
print("1. 把 n_results=3 改成 5，看是不是多出两块")
print("2. 把 question 换成『今天天气』，看距离是不是变大（相似度变小）")
