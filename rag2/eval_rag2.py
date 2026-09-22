# -*- coding: utf-8 -*-
"""检索评估：量化 top-k 命中率（基线数字），后续每次优化都跑它对比"""
from engine import get_engine

# 评估集：问题 + 期望命中的资料（source 包含片段 + 关键内容）
EVAL_SET = [
    {"q": "什么是 Token？", "source": "大模型入门.txt", "kw": "Token"},
    {"q": "大模型是怎么工作的？", "source": "大模型入门.txt", "kw": "超级预测器"},
    {"q": "什么是 Prompt？写 Prompt 有什么技巧？", "source": "大模型入门.txt", "kw": "Prompt"},
    {"q": "什么是上下文窗口？", "source": "大模型入门.txt", "kw": "上下文窗口"},
    {"q": "什么是 RAG？RAG 的流程是什么？", "source": "大模型入门.txt", "kw": "RAG"},
    {"q": "什么是 Embedding？", "source": "大模型入门.txt", "kw": "Embedding"},
    {"q": "什么是 Agent？", "source": "大模型入门.txt", "kw": "Agent"},
    {"q": "什么是 API？", "source": "大模型入门.txt", "kw": "API"},
    {"q": "chat.py 里请求和响应中的 content 分别是什么？", "source": "请求响应链路.md", "kw": "content"},
    {"q": "南京有哪些 AI 应用开发实习机会？", "source": "JD调研-南京AI应用开发实习.md", "kw": "Calix"},
    {"q": "AI 应用实习岗位要求哪些关键词？", "source": "JD调研-南京AI应用开发实习.md", "kw": "LangChain"},
    {"q": "RAG 里找最相关资料靠什么实现？", "source": "大模型入门.txt", "kw": "向量距离"},
]


def _hit(chunk, item):
    src = chunk.get("source", "")
    text = chunk.get("text", "")
    return item["source"] in src and item["kw"] in text


def run(mode="hybrid"):
    engine = get_engine()
    n = len(EVAL_SET)
    label = "向量 + BM25 混合" if mode == "hybrid" else "纯向量"
    print(f"[{label}] 评估集：{n} 条 | 向量库：{engine.store.count()} 块 | top-5 + 重排")
    stats = {1: 0, 3: 0, 5: 0}
    misses = []
    for item in EVAL_SET:
        chunks = engine.retrieve(item["q"], top_k=5, use_rerank=True, use_bm25=(mode == "hybrid"))
        hit_idx = [i for i, c in enumerate(chunks) if _hit(c, item)]
        top1 = 1 in [i + 1 for i in hit_idx if i == 0]
        top3 = any(i < 3 for i in hit_idx)
        top5 = bool(hit_idx)
        stats[1] += top1
        stats[3] += top3
        stats[5] += top5
        mark = "OK" if top3 else "X "
        print(f"  [{mark}] {item['q']}  top1={top1} top3={top3} top5={top5}"
              f"  best={hit_idx[0] + 1 if hit_idx else '-'}")
        if not top5:
            misses.append(item["q"])

    print(f"\n===== 命中率（{label}） =====")
    for k in (1, 3, 5):
        print(f"  top-{k}: {stats[k]}/{n} = {stats[k] / n * 100:.0f}%")
    if misses:
        print("top-5 未命中：", misses)
    print()
    return stats


def main():
    print("=" * 40)
    base = run("base")
    print("=" * 40)
    hybrid = run("hybrid")
    print("=" * 40)
    print("\n===== 对比（hybrid - base） =====")
    for k in (1, 3, 5):
        diff = hybrid[k] - base[k]
        print(f"  top-{k}: {base[k]} → {hybrid[k]}（{'+' if diff >= 0 else ''}{diff}）")
    print("\n结论看这里：混合检索是否提升了命中率，尤其'什么是 Agent？'那条。")


if __name__ == "__main__":
    main()
