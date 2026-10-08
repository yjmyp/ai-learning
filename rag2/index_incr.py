# -*- coding: utf-8 -*-
"""增量索引：改一篇文档不用重建整库

为什么需要：v2 的 `engine.ensure_index(force=True)` 是"全量重建"——
28 篇要 40 多秒，几百篇就要几分钟，线上不可能这么干。
这里按"来源"做增量：删掉这篇文档的旧块 → 重新切分 → 只向量化这篇 →
写入 Chroma。改 1 篇的成本只跟这篇的长度有关，和库的大小无关。

用法：
    python index_incr.py ../学习笔记/新文档.md     # 加/更新一篇
    python index_incr.py --remove 新文档.md        # 删一篇（按 source 匹配）
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from chunker import chunk_text
from config import CHUNK_OVERLAP, CHUNK_SIZE
from engine import _chunk_id, get_engine
from loader import load_documents


def add_file(path, verbose=True):
    """加/更新一个文件；返回写入的块数。"""
    engine = get_engine()
    docs = load_documents([os.path.dirname(os.path.abspath(path))])
    target = os.path.basename(path)
    doc = next((d for d in docs if os.path.basename(d["source"]) == target), None)
    if doc is None:
        raise SystemExit("没读到这个文件（支持 .txt/.md/.pdf/.docx）：%s" % path)
    source = doc["source"]
    t0 = time.time()
    removed = engine.store.delete_by_source(source)     # 先删旧块
    chunks = chunk_text(doc["text"], source, CHUNK_SIZE, CHUNK_OVERLAP)
    ids = [_chunk_id(i, source) for i in range(len(chunks))]
    texts = [c["text"] for c in chunks]
    metas = [{"source": source} for _ in chunks]
    embs = engine.embedder.encode(texts)
    engine.store.add(ids, texts, metas, embs)
    if verbose:
        print("[增量索引] %s：删旧块 %d → 写入 %d 块，耗时 %.1fs（库内共 %d 块）"
              % (source, removed, len(chunks), time.time() - t0, engine.store.count()))
    return len(chunks)


def remove_source(source):
    engine = get_engine()
    n = engine.store.delete_by_source(source)
    print("[增量索引] 删除 %s 的 %d 个块（库内剩 %d 块）"
          % (source, n, engine.store.count()))
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="要加入/更新的文件")
    ap.add_argument("--remove", default="", help="按 source 删除")
    args = ap.parse_args()
    if args.remove:
        remove_source(args.remove)
    elif args.path:
        add_file(args.path)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
