# -*- coding: utf-8 -*-
"""RAG 引擎：入库 / 检索 / 问答串起来，供 API 与网页版共用"""
import hashlib
import time

from chunker import chunk_text
from config import (
    CHROMA_DIR, CHUNK_OVERLAP, CHUNK_SIZE, COLLECTION_NAME,
    DOCS_DIRS, get_api_key,
)
from embedder import Embedder
from loader import load_documents
from qa import ask_deepseek
from retriever import Retriever
from store import VectorStore

_engine = None


def _chunk_id(index, source):
    return hashlib.md5(f"{index}|{source}".encode("utf-8")).hexdigest()[:32]


class RAGEngine:
    def __init__(self):
        self.embedder = Embedder()
        self.store = VectorStore(CHROMA_DIR, COLLECTION_NAME)
        self.retriever = Retriever(self.store, self.embedder)
        self.ensure_index()

    def ensure_index(self, force=False):
        """索引为空或 force=True 时重建"""
        if force or self.store.count() == 0:
            self._build()

    def _build(self):
        docs = load_documents(DOCS_DIRS)
        chunks = []
        for d in docs:
            chunks.extend(
                chunk_text(d["text"], d["source"], CHUNK_SIZE, CHUNK_OVERLAP)
            )
        if not chunks:
            raise RuntimeError("没有找到可入库的资料，请检查 DOCS_DIRS")

        ids, texts, metas = [], [], []
        for i, c in enumerate(chunks):
            ids.append(_chunk_id(i, c["source"]))
            texts.append(c["text"])
            metas.append({"source": c["source"]})

        t0 = time.time()
        embeddings = self.embedder.encode(texts)
        self.store.reset()
        self.store.add(ids, texts, metas, embeddings)
        print(f"[rag2] 入库完成：{len(chunks)} 块 / {len(docs)} 篇 "
              f"/ 耗时 {time.time() - t0:.1f}s")

    def retrieve(self, question, top_k=4, use_rerank=True):
        return self.retriever.retrieve(question, top_k, use_rerank)

    def ask(self, question, top_k=4, use_rerank=True, api_key=None):
        """完整问答：检索 + 生成，返回回答与来源"""
        chunks = self.retrieve(question, top_k, use_rerank)
        key = api_key or get_api_key()
        if not key:
            raise RuntimeError("未找到 DEEPSEEK_API_KEY")
        answer = ask_deepseek(question, chunks, key)
        return {"answer": answer, "sources": chunks}


def get_engine():
    global _engine
    if _engine is None:
        _engine = RAGEngine()
    return _engine
