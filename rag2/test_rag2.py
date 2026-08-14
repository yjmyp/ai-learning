# -*- coding: utf-8 -*-
"""本地验证：python rag2/test_rag2.py"""
from config import get_api_key
from engine import get_engine
from qa import ask_deepseek


def main():
    engine = get_engine()
    print("资料块数：", engine.store.count())

    print("\n===== 检索测试 =====")
    for q in ["什么是 RAG？", "大模型是怎么工作的？", "DeepSeek 的 API key 应该放在哪里？"]:
        chunks = engine.retrieve(q, top_k=3, use_rerank=True)
        print(f"\nQ: {q}")
        for c in chunks:
            print(f"  - [{c['source']}] 向量分 {c.get('vector_score')} "
                  f"重排分 {c.get('rerank_score')} :: {c['text'][:36].replace(chr(10), ' ')}")

    print("\n===== LLM 问答测试（真实调用 DeepSeek）=====")
    q = "什么是 RAG？它有什么好处？"
    chunks = engine.retrieve(q, top_k=3, use_rerank=True)
    print("Q:", q)
    print("A:", ask_deepseek(q, chunks, get_api_key()))


if __name__ == "__main__":
    main()
