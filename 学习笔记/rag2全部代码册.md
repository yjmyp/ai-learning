# rag2 全部代码册（2026-08-17）

> 用法：按下面顺序从头读到尾，读的时候**只看代码和注释**，不要急着想"为什么"——先建立全景，再逐个文件深挖。
> 阅读顺序 = 数据流顺序：配置 → 切分 → 向量化 → 解析 → 入库 → 检索(BM25) → 重排 → 问答 → 串联 → 接口/页面 → 工具脚本。

## rag2\__init__.py — 入口说明：这个目录是干什么的

```python
# RAG v2：从零重构版（解析 → 切分 → 向量化 → Chroma → 召回 → 重排 → 问答）
```

## rag2\config.py — 全局配置：路径/模型/切分参数/API key 读取 —— 所有参数都在这

```python
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
HYBRID_TOPK = 20      # 混合检索：向量和 BM25 各取前 20 再融合
BM25_WEIGHT = 0.3     # 混合权重：总分 = (1-w)*向量 + w*BM25（w=0.3 即 0.7:0.3）


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
```

## rag2\chunker.py — 切分：把文章切成 300 字块、50 字重叠（你已学过）

```python
# -*- coding: utf-8 -*-
"""文本切分：按段落贪心打包成块，块间带重叠，保留来源"""
import re


def _split_long(paragraph, chunk_size):
    """超长段落按句末标点切开，必要时硬切"""
    parts = re.split(r"(?<=[。！？；])", paragraph)
    pieces, cur = [], ""
    for part in parts:
        if len(part) > chunk_size:
            if cur:
                pieces.append(cur)
                cur = ""
            for i in range(0, len(part), chunk_size):
                pieces.append(part[i:i + chunk_size])
        elif cur and len(cur) + len(part) > chunk_size:
            pieces.append(cur)
            cur = part
        else:
            cur += part
    if cur:
        pieces.append(cur)
    return pieces


def chunk_text(text, source, chunk_size=300, overlap=50):
    """把一篇文档切成块，每块约 chunk_size 字，相邻块保留 overlap 字重叠。
    策略：空行分段 → 贪心合并段落 → 块满后把上一段尾巴带进下一块。"""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, buf, buf_len = [], [], 0

    for para in paragraphs:
        if len(para) > chunk_size:
            if buf:
                chunks.append("\n".join(buf))
                buf, buf_len = [], 0
            for sub in _split_long(para, chunk_size):
                chunks.append(sub)
            continue

        if buf and buf_len + len(para) + 1 > chunk_size:
            chunks.append("\n".join(buf))
            tail = buf[-1] if buf else ""
            tail = tail[-overlap:] if len(tail) > overlap else tail
            buf, buf_len = ([tail] if tail else []), len(tail)

        buf.append(para)
        buf_len += len(para) + 1

    if buf:
        chunks.append("\n".join(buf))

    return [{"text": c, "source": source} for c in chunks if c.strip()]
```

## rag2\embedder.py — 向量化：bge 模型把文字变成数字向量

```python
# -*- coding: utf-8 -*-
"""向量化：BGE 中文小模型（本地已缓存，懒加载）"""
from functools import lru_cache


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer
    from config import EMBED_MODEL
    return SentenceTransformer(EMBED_MODEL, device="cpu")


class Embedder:
    """统一入口：encode([...]) → [[float, ...], ...]（已归一化）"""

    def encode(self, texts):
        model = _model()
        vectors = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=32,
        )
        return [v.tolist() for v in vectors]
```

## rag2\loader.py — 解析：读 txt/md/pdf/docx，统一成 [{text, source}]

```python
# -*- coding: utf-8 -*-
"""文档解析：支持 .txt/.md/.pdf/.docx，返回 [{text, source}]"""
import os

from pypdf import PdfReader
from docx import Document

SUPPORTED_EXT = {".txt", ".md", ".pdf", ".docx"}


def _read_text(path):
    """txt/md 按 UTF-8 优先读取，失败再试 GBK"""
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _read_pdf(path):
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _read_docx(path):
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _normalize(text):
    """统一换行、去掉行尾空白，保留段落结构"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines)


def load_documents(dirs):
    """扫描多个目录（含子目录），返回 [{text, source}]。
    source 存相对路径，方便问答时溯源。"""
    docs = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for root, _subdirs, files in os.walk(d):
            for fn in sorted(files):
                ext = os.path.splitext(fn)[1].lower()
                if ext not in SUPPORTED_EXT:
                    continue
                path = os.path.join(root, fn)
                try:
                    if ext in (".txt", ".md"):
                        text = _read_text(path)
                    elif ext == ".pdf":
                        text = _read_pdf(path)
                    else:
                        text = _read_docx(path)
                except Exception as exc:
                    print(f"[warn] 解析失败 {path}: {exc}")
                    continue
                text = _normalize(text).strip()
                if text:
                    docs.append({"text": text, "source": os.path.relpath(path)})
    return docs
```

## rag2\store.py — 入库：Chroma 向量库封装（含 get_all 给 BM25 用）

```python
# -*- coding: utf-8 -*-
"""向量库封装：Chroma 持久化（余弦距离）"""
from chromadb import PersistentClient
from chromadb.config import Settings


class VectorStore:
    def __init__(self, path, collection_name):
        self.client = PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self):
        return self.collection.count()

    def get_all(self):
        """取回全部文档（构建 BM25 关键词索引用）。"""
        return self.collection.get(include=["documents", "metadatas"])

    def add(self, ids, texts, metadatas, embeddings):
        self.collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(self, embedding, n_results):
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    def reset(self):
        """清空并重建集合（重建索引用）"""
        name = self.collection.name
        meta = self.collection.metadata
        try:
            self.client.delete_collection(name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(name=name, metadata=meta)
```

## rag2\bm25.py — 【今日新增·示范】BM25 关键词检索（学完 retriever 再看，别先纠结）

```python
# -*- coding: utf-8 -*-
"""BM25 检索器（从零实现，中文友好，无第三方依赖）

BM25 是关键词检索的经典算法：
- 词频（TF）越高越相关，但有上限（k1 控制饱和）；
- 稀有词权重更大（IDF，逆文档频率）；
- 文档长度越长，分数适当惩罚（b 控制长度归一化强度）。

和向量检索互补：向量管"语义相近"，BM25 管"词面精确命中"。
"""
import math
import re

_WORD_RE = re.compile(r"[a-z0-9_]+")
_CN_RE = re.compile(r"[\u4e00-\u9fff]+")


def tokenize(text):
    """英文/数字按单词，中文按相邻双字（bigram）切分。"""
    text = text.lower()
    tokens = []
    for m in _WORD_RE.finditer(text):
        tokens.append(m.group(0))
    for run in _CN_RE.findall(text):
        n = len(run)
        if n == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i:i + 2] for i in range(n - 1))
    return tokens


class BM25:
    def __init__(self, corpus, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(doc) for doc in corpus]
        self.doc_len = [len(t) for t in self.doc_tokens]
        self.n_docs = len(self.doc_len)
        self.avg_len = sum(self.doc_len) / max(self.n_docs, 1)

        # 文档频率 df → 逆文档频率 idf
        self.df = {}
        for tokens in self.doc_tokens:
            for term in set(tokens):
                self.df[term] = self.df.get(term, 0) + 1
        self.idf = {
            term: math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))
            for term, df in self.df.items()
        }

    def score(self, query, doc_idx):
        """单个文档对查询的 BM25 分数。"""
        tokens = self.doc_tokens[doc_idx]
        dl = self.doc_len[doc_idx]
        tf_map = {}
        for t in tokens:
            tf_map[t] = tf_map.get(t, 0) + 1

        total = 0.0
        for term in set(tokenize(query)):
            tf = tf_map.get(term, 0)
            if tf == 0 or term not in self.idf:
                continue
            # 长度归一化分母
            norm = self.k1 * (1 - self.b + self.b * dl / max(self.avg_len, 1e-9))
            total += self.idf[term] * tf * (self.k1 + 1) / (tf + norm)
        return total

    def search(self, query, top_k):
        """返回 [(文档下标, 分数)]，按分数降序。"""
        scored = [(i, self.score(query, i)) for i in range(self.n_docs)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
```

## rag2\retriever.py — 召回：向量 top-N → 可选 BM25 混合 → 可选重排 → top_k

```python
# -*- coding: utf-8 -*-
"""检索：向量召回 →（可选 BM25 混合）→ 可选重排 → 返回前 top_k"""
from config import BM25_WEIGHT, DEFAULT_TOP_K, HYBRID_TOPK, RERANK_TOP_K
from bm25 import BM25
from reranker import Reranker


class Retriever:
    def __init__(self, store, embedder, rerank_top_k=RERANK_TOP_K):
        self.store = store
        self.embedder = embedder
        self.rerank_top_k = rerank_top_k
        self.reranker = Reranker()
        self.bm25 = None
        self.bm25_ids = None
        self.bm25_texts = None
        self.bm25_metas = None

    def _ensure_bm25(self):
        """懒加载 BM25 索引（首次使用时构建一次）。"""
        if self.bm25 is None:
            data = self.store.get_all()
            self.bm25_ids = data["ids"]
            self.bm25_texts = data["documents"]
            self.bm25_metas = data["metadatas"]
            self.bm25 = BM25(self.bm25_texts)
        return self.bm25

    def retrieve(self, question, top_k=DEFAULT_TOP_K, use_rerank=True, use_bm25=True):
        query_vec = self.embedder.encode([question])[0]
        n_vec = max(top_k, HYBRID_TOPK) if use_bm25 else max(top_k, self.rerank_top_k) if use_rerank else top_k
        res = self.store.query(query_vec, n_results=n_vec)

        hits = []
        ids = res["ids"][0]
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        dists = res["distances"][0]
        for i in range(len(ids)):
            hits.append({
                "id": ids[i],
                "text": docs[i],
                "source": (metas[i] or {}).get("source", ""),
                "vector_score": round(1 - dists[i], 4),  # 余弦相似度
            })

        if use_bm25:
            hits = self._hybrid(question, hits)

        if use_rerank and len(hits) > 1:
            hits = self.reranker.rerank(question, hits)
        return hits[:top_k]

    def _hybrid(self, question, vec_hits):
        """向量与 BM25 双路召回 → 各自归一化 → 加权融合。"""
        bm25 = self._ensure_bm25()
        cand = {}
        for h in vec_hits:
            cand[h["id"]] = {
                "vec": h["vector_score"], "bm25": 0.0,
                "text": h["text"], "source": h["source"],
            }
        for idx, score in bm25.search(question, HYBRID_TOPK):
            cid = self.bm25_ids[idx]
            if cid in cand:
                cand[cid]["bm25"] = score
            else:
                meta = self.bm25_metas[idx] or {}
                cand[cid] = {
                    "vec": 0.0, "bm25": score,
                    "text": self.bm25_texts[idx],
                    "source": meta.get("source", ""),
                }

        ids_list = list(cand.keys())
        vec_vals = [cand[i]["vec"] for i in ids_list]
        bm_vals = [cand[i]["bm25"] for i in ids_list]
        vec_norm = self._minmax(vec_vals)
        bm_norm = self._minmax(bm_vals)

        fused = []
        for pos, cid in enumerate(ids_list):
            c = cand[cid]
            fused.append({
                "id": cid,
                "text": c["text"],
                "source": c["source"],
                "vector_score": round(c["vec"], 4),
                "bm25_score": round(c["bm25"], 4),
                "hybrid_score": round(
                    (1 - BM25_WEIGHT) * vec_norm[pos] + BM25_WEIGHT * bm_norm[pos], 4
                ),
            })
        fused.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return fused

    @staticmethod
    def _minmax(vals):
        """最小-最大归一化到 [0,1]；全相等时给 0.5 避免除零。"""
        lo, hi = min(vals), max(vals)
        if hi - lo < 1e-9:
            return [0.5] * len(vals)
        return [(v - lo) / (hi - lo) for v in vals]
```

## rag2\reranker.py — 重排：TF-IDF 字符 n-gram 二次排序

```python
# -*- coding: utf-8 -*-
"""轻量重排：TF-IDF 字符 n-gram 相关性（离线可用，不依赖大模型下载）"""
from sklearn.feature_extraction.text import TfidfVectorizer


class Reranker:
    def __init__(self, ngram=(2, 3)):
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=ngram,
            max_features=20000,
            sublinear_tf=True,
        )

    def rerank(self, question, chunks):
        """对候选块按与问题的字符级相似度重排，返回带 rerank_score 的新列表"""
        if len(chunks) <= 1:
            return chunks
        texts = [c["text"] for c in chunks]
        matrix = self.vectorizer.fit_transform(texts + [question])
        question_vec = matrix[-1]
        doc_vecs = matrix[:-1]
        sims = (doc_vecs @ question_vec.T).toarray().ravel()
        order = sorted(range(len(chunks)), key=lambda i: (-sims[i], i))
        ranked = []
        for i in order:
            item = dict(chunks[i])
            item["rerank_score"] = round(float(sims[i]), 4)
            ranked.append(item)
        return ranked
```

## rag2\qa.py — 问答：检索结果拼 Prompt → 调 DeepSeek → 带引用回答

```python
# -*- coding: utf-8 -*-
"""问答：把检索结果拼进 Prompt，调 DeepSeek 生成带引用的回答"""
import requests

from config import LLM_MODEL, LLM_URL


def build_prompt(question, chunks):
    lines = ["你是学习助手。请严格只根据下面提供的资料回答，", 
             "资料里没有的内容，直接回答“资料里没有相关内容”。",
             "回答中引用资料处，用 [编号] 标注（例如 [1]）。", "", "资料："]
    for i, c in enumerate(chunks):
        src = c.get("source", "未知来源")
        lines.append(f"[{i + 1}] 来源：{src}\n{c['text']}")
    lines.append("")
    lines.append(f"问题：{question}")
    return "\n\n".join(lines)


def ask_deepseek(question, chunks, api_key, temperature=0.3, max_tokens=1024):
    """调 DeepSeek 生成回答；chunks 来自 retriever.retrieve()"""
    messages = [
        {"role": "system", "content": "你是学习助手，回答要简洁、准确、可溯源。"},
        {"role": "user", "content": build_prompt(question, chunks)},
    ]
    resp = requests.post(
        LLM_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
```

## rag2\engine.py — 串联：RAGEngine 把入库/检索/问答串起来（入口）

```python
# -*- coding: utf-8 -*-
"""RAG 引擎：入库 / 检索 / 问答串起来，供 API 与网页版共用"""
import hashlib
import time

from chunker import chunk_text
from config import (
    CHROMA_DIR, CHUNK_OVERLAP, CHUNK_SIZE, COLLECTION_NAME,
    DOCS_DIRS, EMBED_MODEL, get_api_key,
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
        print(f"[rag2] 解析到 {len(docs)} 篇资料", flush=True)
        chunks = []
        for d in docs:
            chunks.extend(
                chunk_text(d["text"], d["source"], CHUNK_SIZE, CHUNK_OVERLAP)
            )
        if not chunks:
            raise RuntimeError("没有找到可入库的资料，请检查 DOCS_DIRS")
        print(f"[rag2] 切分成 {len(chunks)} 块（{CHUNK_SIZE}字/块，重叠 {CHUNK_OVERLAP}）", flush=True)

        ids, texts, metas = [], [], []
        for i, c in enumerate(chunks):
            ids.append(_chunk_id(i, c["source"]))
            texts.append(c["text"])
            metas.append({"source": c["source"]})

        t0 = time.time()
        print(f"[rag2] 向量化中（模型 {EMBED_MODEL}，离线缓存）...", flush=True)
        embeddings = self.embedder.encode(texts)
        print("[rag2] 向量化完成，写入 Chroma ...", flush=True)
        self.store.reset()
        self.store.add(ids, texts, metas, embeddings)
        print(f"[rag2] 入库完成：{len(chunks)} 块 / {len(docs)} 篇 "
              f"/ 耗时 {time.time() - t0:.1f}s")

    def retrieve(self, question, top_k=4, use_rerank=True, use_bm25=True):
        return self.retriever.retrieve(question, top_k, use_rerank, use_bm25)

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
```

## rag2\api.py — FastAPI 接口层：/health /retrieve /ask

```python
# -*- coding: utf-8 -*-
"""FastAPI 接口层：uvicorn rag2.api:app --reload"""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import get_api_key
from engine import get_engine
from qa import ask_deepseek


@asynccontextmanager
async def lifespan(_app):
    get_engine().ensure_index()
    yield


app = FastAPI(title="AI 学习知识库 RAG v2 API", version="2.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(4, ge=1, le=10)
    use_rerank: bool = True


class AskResponse(BaseModel):
    answer: str
    sources: list
    elapsed_ms: int


@app.get("/health")
def health():
    engine = get_engine()
    return {"status": "ok", "chunks": engine.store.count()}


@app.get("/retrieve")
def retrieve(question: str, top_k: int = 4, use_rerank: bool = True):
    engine = get_engine()
    chunks = engine.retrieve(question, top_k, use_rerank)
    return {"question": question, "chunks": chunks}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    engine = get_engine()
    t0 = time.time()
    chunks = engine.retrieve(req.question, req.top_k, req.use_rerank)
    answer = ask_deepseek(req.question, chunks, get_api_key())
    return AskResponse(
        answer=answer,
        sources=chunks,
        elapsed_ms=int((time.time() - t0) * 1000),
    )
```

## rag2\app.py — Streamlit 网页版：问答页 + 检索调试页

```python
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
```

## rag2\build_index.py — 命令行：重建索引入口

```python
# -*- coding: utf-8 -*-
"""重建索引：python rag2/build_index.py"""
from engine import get_engine


if __name__ == "__main__":
    engine = get_engine()
    print("开始重建索引 ...")
    engine.ensure_index(force=True)
    print("完成，当前块数：", engine.store.count())
```

## rag2\test_rag2.py — 命令行：检索 + 问答验证

```python
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
```

## rag2\eval_rag2.py — 评估：纯向量 vs BM25 混合 对比实验

```python
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
```

## rag2\teach_chunker.py — 教学脚本：chunker 一步步演示（你之前跑过）

```python
# -*- coding: utf-8 -*-
"""教学脚本：看 chunker 一步步切块（跑：python rag2/teach_chunker.py）"""
import re


def _split_long(paragraph, chunk_size):
    parts = re.split(r"(?<=[。！？；])", paragraph)
    pieces, cur = [], ""
    for part in parts:
        if len(part) > chunk_size:
            if cur:
                pieces.append(cur)
                cur = ""
            for i in range(0, len(part), chunk_size):
                pieces.append(part[i:i + chunk_size])
        elif cur and len(cur) + len(part) > chunk_size:
            pieces.append(cur)
            cur = part
        else:
            cur += part
    if cur:
        pieces.append(cur)
    return pieces


def chunk_text_debug(text, chunk_size, overlap):
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, buf, buf_len = [], [], 0
    print("分段结果：")
    for i, p in enumerate(paragraphs, 1):
        print(f"  段{i}：'{p}'（{len(p)} 字）")
    print()

    for idx, para in enumerate(paragraphs, 1):
        print(f"=== 处理第 {idx} 段：'{para}'（{len(para)} 字）===")
        if len(para) > chunk_size:
            print(f"  -> 超长段（>{chunk_size}字），走独立切分")
            if buf:
                print(f"  ① 先封口：块 = {buf}")
                chunks.append("\n".join(buf))
                buf, buf_len = [], 0
            pieces = _split_long(para, chunk_size)
            print(f"  ② _split_long 切成 {len(pieces)} 块：{pieces}")
            for sub in pieces:
                chunks.append(sub)
            print(f"  ③ 当前已存块数：{len(chunks)}")
            print()
            continue

        if buf and buf_len + len(para) + 1 > chunk_size:
            print(f"  -> 篮子({buf_len}字) + 本段({len(para)}字) + 1 超过 {chunk_size}，封口")
            print(f"  ① 存块：{buf}")
            chunks.append("\n".join(buf))
            tail = buf[-1] if buf else ""
            tail = tail[-overlap:] if len(tail) > overlap else tail
            print(f"  ② 新篮子带上尾巴：'{tail}'（{len(tail)} 字）")
            buf, buf_len = ([tail] if tail else []), len(tail)
        buf.append(para)
        buf_len += len(para) + 1
        print(f"  -> 放进篮子：{buf}，篮子字数={buf_len}")
        print()

    if buf:
        print("=== 结束：篮子还有货，封口 ===")
        chunks.append("\n".join(buf))

    print()
    print("========== 最终结果 ==========")
    for i, c in enumerate(chunks, 1):
        print(f"块{i}（{len(c)}字）：{c}")


if __name__ == "__main__":
    demo = "今天天气很好。\n\n我们一起去公园。\n\n公园里有花有树。\n\n还有一条小河。"
    chunk_text_debug(demo, chunk_size=12, overlap=4)
```

## run_rag2.ps1 — 一键脚本：build → test → eval 三步连跑

```powershell
# RAG v2 one-click verify (build index -> retrieve test -> QA test)
$ErrorActionPreference = 'Stop'
Set-Location 'C:\Users\29947\Documents\Codex\ai-learning'

Write-Host ''
Write-Host '========== 1/2 build index ==========' -ForegroundColor Cyan
python rag2\build_index.py

Write-Host ''
Write-Host '========== 2/2 retrieve + QA test ==========' -ForegroundColor Cyan
python rag2\test_rag2.py

Write-Host ''
Write-Host '========== 3/3 eval (hit-rate baseline) ==========' -ForegroundColor Cyan
python rag2\eval_rag2.py

Write-Host ''
Write-Host 'DONE!' -ForegroundColor Green
Read-Host 'Press Enter to close'
```

## requirements.txt — 依赖清单

```text
streamlit>=1.28
requests>=2.31
sentence-transformers>=2.2.2
scikit-learn>=1.3
chromadb>=1.5
fastapi>=0.110
uvicorn>=0.29
pypdf>=4.0
python-docx>=1.1
```


