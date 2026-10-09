# -*- coding: utf-8 -*-
"""向量库封装：Chroma 持久化（余弦距离）"""
from chromadb import PersistentClient
from chromadb.config import Settings


def source_key(source) -> str:
    """把 source 归一成"只看文件名"的键，用于跨平台匹配。

    为什么不用 os.path.basename：索引里存的 source 时而是 `rag/notes/x.md`（Linux 全量建库），
    时而是 `..\\rag\\notes\\x.md`（Windows 增量），还有 `..\\rag/notes\\x.md` 这种混合形态。
    os.path.basename 只认当前平台的分隔符，所以：
      · 在 Windows 上把 "/" 换成 "\\" 再 basename 能work；
      · 在 Linux 上这么写反而把 "/" 换没了，basename 拿到整串 → 匹配失败 → 重复入库。
    这个函数（手动按两种分隔符切）在两边都对。CI 上就是因为这个平台差异挂过。
    """
    s = str(source or "").strip().lower().replace("\\", "/").rstrip("/")
    return s.rsplit("/", 1)[-1]


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
            # 回退：按**文件名**匹配（跨平台，见 source_key 的说明）。
            # 踩过的坑：全量建库写进索引的 source 与增量时算出的 source 不是同一个字符串，
            # 精确匹配删不掉旧块，于是同一篇文档被重复写进索引（检索时同一段内容命中两次）。
            want = source_key(source)
            if not want:
                return 0
            data = self.get_all()
            targets = set()
            for m in data.get("metadatas") or []:
                s = str((m or {}).get("source", ""))
                if source_key(s) == want:
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
        data = self.get_all()
        groups = {}
        for m in data.get("metadatas") or []:
            s = str((m or {}).get("source", ""))
            groups.setdefault(source_key(s), set()).add(s)
        return {k: sorted(v) for k, v in groups.items() if len(v) > 1}
