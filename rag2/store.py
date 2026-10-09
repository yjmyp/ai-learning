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

    def delete_by_source(self, source):
        """按来源删除（增量更新：先删旧块再加新块）。返回删除条数。

        匹配规则：精确相等，或"以给定名字结尾"（按文件名删也能命中）。
        为什么要放宽：索引里存的 source 是相对路径（实测是 `..\\学习笔记\\xxx.md` 这种），
        调用方按文件名 `xxx.md` 删除时精确匹配删不掉 → 表现为"删了 0 块"，
        而用户看到的却是文档还在被检索到。踩过一次，别再踩。
        """
        try:
            before = self.collection.count()
            self.collection.delete(where={"source": source})
            n = before - self.collection.count()
            if n:
                return n
            # 回退：按**文件名**匹配。
            # 踩过的坑：全量建库写进索引的 source 是 `rag\notes\x.md`，
            # 而增量时 load_documents 给的是 `..\rag\notes\x.md`——两条路径指向同一个文件，
            # 精确匹配删不掉，于是同一篇文档被重复写进索引（库里 4 块变 8 块，
            # 检索时同一段内容命中两次）。所以这里按 basename 兜底。
            import os as _os
            want = _os.path.basename(str(source or "").replace("/", "\\").strip().lower())
            if not want:
                return 0
            data = self.get_all()
            targets = set()
            for m in data.get("metadatas") or []:
                s = str((m or {}).get("source", ""))
                if _os.path.basename(s.replace("/", "\\").strip().lower()) == want:
                    targets.add(s)
            for s in targets:
                self.collection.delete(where={"source": s})
            return before - self.collection.count()
        except Exception:
            return 0

    def duplicate_sources(self):
        """找出"同一个文件被存成多种 source 形式"的重复项（增量索引写错时会出现）。

        返回 {文件名: [source1, source2, ...]}，只列出重复的。
        """
        import os as _os
        data = self.get_all()
        groups = {}
        for m in data.get("metadatas") or []:
            s = str((m or {}).get("source", ""))
            key = _os.path.basename(s.replace("/", "\\").strip().lower())
            groups.setdefault(key, set()).add(s)
        return {k: sorted(v) for k, v in groups.items() if len(v) > 1}
