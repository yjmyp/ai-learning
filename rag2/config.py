# -*- coding: utf-8 -*-
"""RAG v2 全局配置（路径 / 模型 / 切分参数 / API key）"""
import os
import tempfile

# 离线优先：避免受限网络下 HuggingFace/Chroma 联网卡死（本地模型已缓存）
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BASE_DIR)

# 知识库资料目录：把 .txt/.md/.pdf/.docx 放进去即可入库
DOCS_DIRS = [
    os.path.join(REPO_ROOT, "学习笔记"),
    os.path.join(REPO_ROOT, "rag", "notes"),
]

# Chroma 持久化目录（云端可设 RAG2_CHROMA_DIR 指向可写目录）
if os.environ.get("RAG2_CHROMA_DIR"):
    CHROMA_DIR = os.environ["RAG2_CHROMA_DIR"]
else:
    CHROMA_DIR = os.path.join(BASE_DIR, "data", "chroma")

COLLECTION_NAME = "study_notes_v2"

# 嵌入模型（本地已缓存 bge-small-zh-v1.5，无需联网下载）
EMBED_MODEL = "BAAI/bge-small-zh-v1.5"

# 切分参数
CHUNK_SIZE = 300      # 每块大约字数
CHUNK_OVERLAP = 50    # 相邻块重叠字数（保留上下文）

# LLM
LLM_MODEL = "deepseek-chat"
LLM_URL = "https://api.deepseek.com/chat/completions"

# 检索
DEFAULT_TOP_K = 4
RERANK_TOP_K = 8      # 先召回更多候选，再重排取前 top_k


def get_api_key():
    """按优先级找 key：环境变量 → local_key.py → .streamlit/secrets.toml → st.secrets"""
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key

    local_key_path = os.path.join(REPO_ROOT, "local_key.py")
    if os.path.exists(local_key_path):
        try:
            ns = {}
            with open(local_key_path, encoding="utf-8") as f:
                exec(f.read(), ns)
            if ns.get("API_KEY"):
                return str(ns["API_KEY"]).strip()
        except Exception:
            pass

    secrets_path = os.path.join(REPO_ROOT, ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import tomli as tomllib  # Python 3.10
        try:
            with open(secrets_path, "rb") as f:
                data = tomllib.load(f)
            if data.get("DEEPSEEK_API_KEY"):
                return str(data["DEEPSEEK_API_KEY"]).strip()
        except Exception:
            pass

    try:
        import streamlit as st
        return st.secrets.get("DEEPSEEK_API_KEY", "")
    except Exception:
        return ""
