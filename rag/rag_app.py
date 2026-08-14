# rag_app.py —— RAG 问答网页版（Streamlit 界面）
import os

import glob
import requests
import streamlit as st
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

try:
    API_KEY = st.secrets["DEEPSEEK_API_KEY"]
except Exception:
    API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
url = "https://api.deepseek.com/chat/completions"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


# Streamlit 每次操作都会重跑脚本，这个缓存让模型只加载一次
@st.cache_resource
def load_model():
    return SentenceTransformer("BAAI/bge-small-zh-v1.5")


NOTES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes")

def load_notes(folder=NOTES_DIR):
    """读资料、切段（老朋友）"""
    chunks = []
    for path in glob.glob(os.path.join(folder, "*.txt")):
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
        for para in text.split("\n\n"):
            para = para.strip()
            if len(para) >= 20:
                chunks.append(para)
    return chunks


def search(model, chunks, query, top_k=3):
    """向量版检索（老朋友，只是多了个 model 参数）"""
    chunk_vecs = model.encode(chunks)
    q_vec = model.encode([query])
    sims = cosine_similarity(q_vec, chunk_vecs)[0]
    top = sims.argsort()[-top_k:][::-1]
    return [(chunks[i], float(sims[i])) for i in top]


def ask(model, chunks, question):
    results = search(model, chunks, question)
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
    answer = r.json()["choices"][0]["message"]["content"]
    return answer, results


# ===== 网页界面（从这里开始是 Streamlit 的活） =====
st.set_page_config(page_title="我的知识库问答", page_icon="📚")
st.title("📚 我的知识库问答")
st.caption("基于 bge 向量检索 + DeepSeek 的 RAG 问答系统")

with st.spinner("正在加载模型和资料（第一次较慢）..."):
    model = load_model()
    chunks = load_notes()

st.success(f"已加载 {len(chunks)} 段资料，可以提问了！")

question = st.text_input("输入你的问题：")
if st.button("提问") and question.strip():
    with st.spinner("检索 + 生成中..."):
        answer, results = ask(model, chunks, question)
    st.markdown("**回答：**")
    st.write(answer)
    with st.expander("📄 查看检索到的资料（可溯源）"):
        for i, (text, score) in enumerate(results):
            st.write(f"**{i+1}.** 相似度 {score:.2f}｜{text}")
