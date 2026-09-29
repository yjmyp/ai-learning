# -*- coding: utf-8 -*-
"""
第 1 步：读文件 → 变成文本

要看的：一篇文档进来，出来是什么形状。
怎么做：python learn_rag\learn_1_load.py
"""
import os
import sys

# 让 Python 能找到 rag2 里的模块（config.py / loader.py 都在那）
RAG2_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rag2"))
sys.path.insert(0, RAG2_DIR)

from config import DOCS_DIRS          # noqa: E402
from loader import load_documents     # noqa: E402

# 只读第一个目录（学习笔记），跑得快
docs = load_documents([DOCS_DIRS[0]])

print(f"读到了 {len(docs)} 篇文档")
print(f"返回类型：{type(docs).__name__}，里面每个元素是字典\n")

first = docs[0]
print("第一篇：")
print(f"  来源（source）= {first['source']}")
print(f"  文本长度      = {len(first['text'])} 个字符")
print("  开头 80 字：")
print("  " + first["text"][:80].replace("\n", " "))

print("\n—— 改动实验 ——")
print("1. 把 [DOCS_DIRS[0]] 改成 DOCS_DIRS（两个目录都读），看篇数变多少")
print("2. 随便挑一篇，看 source 是不是相对路径（这就是回答里显示'来源'的东西）")
