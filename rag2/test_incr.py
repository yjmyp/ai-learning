# -*- coding: utf-8 -*-
"""增量索引验收：改一篇只重算这一篇，块数不膨胀，删得掉。

为什么要有这个测试：「增量重建」是简历里写出去的能力，必须有可复现的验证；
而且"删旧块再写新块"如果写错，会出现同一篇文档在库里有两份（检索时重复命中），
这种错很隐蔽，只能靠测。

跑法：python test_incr.py（会临时往索引里加一篇测试文档，结束前删掉）
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import config
import index_incr

FIXTURE = os.path.join(config.DOCS_DIRS[0], "_增量索引测试文档.md")


def write(body):
    with open(FIXTURE, "w", encoding="utf-8") as f:
        f.write(body)


def main():
    checks = []
    engine = None
    src = os.path.basename(FIXTURE)
    try:
        # 跨平台归一：索引里的 source 有 `/`、`\`、混合三种形态，
        # 归不到同一个 key 就会出现"删不掉旧块 → 同一篇文档入库两次"。
        # 这条是 CI 在 Linux 上抓出来的（Windows 本地怎么写都对，Linux 全不对）。
        from store import source_key
        forms = ["rag/notes/x.md", "..\\rag\\notes\\x.md", "..\\rag/notes\\x.md",
                 "/home/runner/rag/notes/x.md", "x.md"]
        keys = {source_key(f) for f in forms}
        checks.append(("source 归一化：5 种形态归到 1 个 key（%s）" % ",".join(keys), len(keys) == 1))

        write("# 增量索引测试\n\n第一版内容：只讲一个很简单的主题，用来验证切块数量。\n" * 8)
        base = index_incr.get_engine().store.count()
        n1 = index_incr.add_file(FIXTURE, verbose=False)
        total1 = index_incr.get_engine().store.count()
        checks.append(("加入一篇后块数增加（+%d）" % (total1 - base), total1 > base and n1 > 0))

        # 改内容后再加一次：应该"先删旧块"，而不是叠一份
        write("# 增量索引测试\n\n第二版内容：换了完全不同的主题，用来验证旧块被删掉。\n" * 4)
        n2 = index_incr.add_file(FIXTURE, verbose=False)
        total2 = index_incr.get_engine().store.count()
        checks.append(("改一篇后再加入：总块数不膨胀（%d → %d）" % (total1, total2),
                       total2 == base + n2))
        checks.append(("该来源只保留一份（%d 块 = 第二版块数）" % n2, n2 == total2 - base))

        # 检索应命中新内容、不应命中旧内容
        from retriever_v3 import RetrieverV3
        eng = index_incr.get_engine()
        ret = RetrieverV3(eng.store, eng.embedder)
        res = ret.retrieve("第二版内容 换了完全不同的主题", top_k=3, mode="hybrid")
        texts = " ".join((h.get("text") or "") for h in res["hits"])
        checks.append(("检索能命中新版内容", "第二版" in texts))
        checks.append(("检索不再命中已被替换的旧版内容", "第一版" not in texts))

        # 删除
        removed = index_incr.remove_source(src)
        total3 = index_incr.get_engine().store.count()
        checks.append(("按来源删除干净（删 %d 块，回到 %d）" % (removed, total3), total3 == base))
        # 防回归：绝不允许多个 source 形式指向同一个文件（全量建库与增量写入的路径形式不同，
        # 曾经因此把同一篇文档在库里存了两份，检索时命中两次）
        dup = index_incr.get_engine().store.duplicate_sources()
        checks.append(("库内没有「同一文件多种 source 形式」的重复项（%s）"
                       % (list(dup)[:3] if dup else "无"), not dup))
    finally:
        try:
            if os.path.exists(FIXTURE):
                index_incr.remove_source(src)
        except Exception:
            pass
        try:
            os.remove(FIXTURE)
        except Exception:
            pass

    ok = sum(1 for _, v in checks if v)
    for name, good in checks:
        print(("✅ " if good else "❌ ") + name)
    print("\n%d/%d 通过" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
