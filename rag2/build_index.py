# -*- coding: utf-8 -*-
"""重建索引：python rag2/build_index.py"""
from engine import get_engine


if __name__ == "__main__":
    engine = get_engine()
    print("开始重建索引 ...")
    engine.ensure_index(force=True)
    print("完成，当前块数：", engine.store.count())
