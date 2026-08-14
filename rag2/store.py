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
