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
