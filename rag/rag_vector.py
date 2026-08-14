# rag_vector.py —— 向量版 RAG 检索（本地中文模型，不需要 API Key）
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"  # 国内镜像，下载模型用

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# 第一次运行会下载模型（约 470MB），耐心等 3~10 分钟
print("正在加载中文向量模型（第一次会下载，请耐心等待）...")
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
print("模型加载完成！")

chunks = [
    "RAG是检索增强生成，让大模型先查资料再回答。",
    "Token（词元）是大模型处理文本的最小单位。",
    "Agent是能自己规划和调用工具的AI。",
    "今天的天气很好，适合出去玩。",
]

# 把每段资料变成向量（启动时转一次，存起来）
chunk_vecs = model.encode(chunks)

def search(query, top_k=3):
    """向量版检索：问题转向量 -> 算相似度 -> 取前3（结构和字符版一样）"""
    q_vec = model.encode([query])
    sims = cosine_similarity(q_vec, chunk_vecs)[0]
    top = sims.argsort()[-top_k:][::-1]
    return [(chunks[i], float(sims[i])) for i in top]

# 测试1：问法跟资料"字面不同"，但语义相同
query = "怎么让AI先查资料再回答？"
print("\n问题：", query)
print("-" * 40)
for i, (text, score) in enumerate(search(query)):
    print(f"  {i+1}. 相似度 {score:.3f} | {text}")

# 测试2
query = "什么是词元？"
print("\n问题：", query)
print("-" * 40)
for i, (text, score) in enumerate(search(query)):
    print(f"  {i+1}. 相似度 {score:.3f} | {text}")
