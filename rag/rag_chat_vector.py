# rag_chat_vector.py —— 完整向量版 RAG 问答（bge 中文模型 + DeepSeek）
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"   # 国内镜像，下载模型用

import glob
import requests
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

API_KEY = "sk-75255e06772248569871fdb19977fab4"

url = "https://api.deepseek.com/chat/completions"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

print("加载中文向量模型（第一次会下载，耐心等）...")
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
print("模型加载完成！")


def load_notes(folder="notes"):
    """读资料、切段（老朋友，和 rag_chat.py 一样）"""
    chunks = []
    for path in glob.glob(os.path.join(folder, "*.txt")):
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
        for para in text.split("\n\n"):
            para = para.strip()
            if len(para) >= 20:
                chunks.append(para)
    return chunks


def search(chunks, query, top_k=3):
    """向量版检索：问题转向量 -> 算相似度 -> 取前3（你刚验证过）"""
    # 注意：这里每次提问都把全部资料重新转一次向量，比较慢。
    # 正式系统会"提前算好存起来"——这就是向量数据库的由来（下一步学）
    chunk_vecs = model.encode(chunks)
    q_vec = model.encode([query])
    sims = cosine_similarity(q_vec, chunk_vecs)[0]
    top = sims.argsort()[-top_k:][::-1]
    return [(chunks[i], float(sims[i])) for i in top]


def ask(chunks, question):
    results = search(chunks, question)
    context = "\n\n".join(f"[资料{i+1}] {c}" for i, (c, s) in enumerate(results))
    prompt = (
        "请只根据下面提供的资料回答问题。"
        "如果资料里没有答案，就回答'资料里没找到相关答案'。\n\n"
        f"资料：\n{context}\n\n"
        f"问题：{question}"
    )
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
    }
    r = requests.post(url, headers=headers, json=data, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def main():
    chunks = load_notes()
    print(f"已加载 {len(chunks)} 段资料，开始问答（输入 exit 或 退出 结束）")
    print("-" * 40)
    while True:
        q = input("你：").strip()
        if not q:
            continue
        if q.lower() in ("exit", "退出"):
            print("再见！")
            break
        print(f"AI：{ask(chunks, q)}")
        print("-" * 40)


if __name__ == "__main__":
    main()
