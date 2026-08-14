# -*- coding: utf-8 -*-
"""RAG v2 网页版：streamlit run rag2/app.py"""
import streamlit as st

from config import CHUNK_OVERLAP, CHUNK_SIZE, DEFAULT_TOP_K, EMBED_MODEL, LLM_MODEL, get_api_key
from engine import get_engine
from qa import ask_deepseek

st.set_page_config(page_title="AI 学习知识库 v2", page_icon="📚", layout="wide")


@st.cache_resource(show_spinner="加载知识库（首次会构建索引）...")
def load_engine():
    return get_engine()


engine = load_engine()

st.title("📚 AI 学习知识库 v2")
st.caption(
    f"RAG 重构版：Embedding({EMBED_MODEL}) + Chroma + DeepSeek({LLM_MODEL})　|　"
    f"当前资料 {engine.store.count()} 块　|　切分 {CHUNK_SIZE} 字/块、重叠 {CHUNK_OVERLAP} 字"
)

with st.sidebar:
    st.header("⚙️ 设置")
    top_k = st.slider("召回条数 top_k", 1, 8, DEFAULT_TOP_K, help="返回给模型的资料块数")
    use_rerank = st.toggle("启用重排（TF-IDF）", value=True, help="先召回更多，再按字符相似度重排")
    if st.button("🔄 重建索引", type="primary"):
        with st.spinner("正在重新解析资料并入库..."):
            engine.ensure_index(force=True)
        st.success(f"重建完成，共 {engine.store.count()} 块")
        st.rerun()

tab_ask, tab_debug = st.tabs(["💬 问答", "🔍 检索调试"])

with tab_ask:
    question = st.text_area("输入你的问题", height=90, placeholder="例如：什么是 RAG？")
    if st.button("🚀 提问", type="primary"):
        if not question.strip():
            st.warning("先输入问题")
        elif not get_api_key():
            st.error("未找到 DEEPSEEK_API_KEY（检查 local_key.py 或 .streamlit/secrets.toml）")
        else:
            with st.spinner("检索资料 + 生成回答中..."):
                chunks = engine.retrieve(question, top_k, use_rerank)
                answer = ask_deepseek(question, chunks, get_api_key())
            st.markdown("### 回答")
            st.markdown(answer)
            st.markdown("### 引用来源")
            for i, c in enumerate(chunks):
                with st.expander(f"[{i + 1}] {c['source']}（相似度 {c.get('vector_score', '-')}）"):
                    st.markdown(c["text"])

with tab_debug:
    dbg_q = st.text_input("输入问题，只看检索结果（不调用大模型）", placeholder="例如：什么是 Token？")
    if st.button("🔎 检索"):
        if not dbg_q.strip():
            st.warning("先输入问题")
        else:
            chunks = engine.retrieve(dbg_q, top_k, use_rerank)
            st.write(f"共召回 {len(chunks)} 块：")
            for c in chunks:
                st.markdown(f"**{c['source']}**　向量分 {c.get('vector_score', '-')}　重排分 {c.get('rerank_score', '-')}")
                st.markdown(f"> {c['text'][:200]}")
                st.divider()
