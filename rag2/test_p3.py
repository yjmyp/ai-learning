# -*- coding: utf-8 -*-
"""RAG P3 验收：多格式解析（html/csv/xlsx）+ 句级引用定位

跑法：python test_p3.py      （在 rag2 目录下）
"""
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import loader
import locate

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_p3tmp")


def make_files():
    os.makedirs(TMP, exist_ok=True)
    with open(os.path.join(TMP, "a.html"), "w", encoding="utf-8") as f:
        f.write("<html><head><style>p{}</style></head><body><h1>RAG 简介</h1>"
                "<p>RAG 是检索增强生成。</p><script>var x=1;</script>"
                "<p>它先检索再生成，能减少幻觉。</p></body></html>")
    with open(os.path.join(TMP, "b.csv"), "w", encoding="utf-8") as f:
        f.write("岗位,城市,要求\nAI应用开发,南京,RAG+Agent\n大模型算法,北京,硕士\n")
    shared = ('<?xml version="1.0"?><sst xmlns="%s"><si><t>技能</t></si>'
              '<si><t>RAG</t></si><si><t>命中率</t></si><si><t>92%%</t></si></sst>' % NS)
    sheet = ('<?xml version="1.0"?><worksheet xmlns="%s"><sheetData>'
             '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>2</v></c></row>'
             '<row r="2"><c r="A2" t="s"><v>1</v></c><c r="B2" t="s"><v>3</v></c></row>'
             '</sheetData></worksheet>' % NS)
    with zipfile.ZipFile(os.path.join(TMP, "c.xlsx"), "w") as z:
        z.writestr("xl/sharedStrings.xml", shared)
        z.writestr("xl/worksheets/sheet1.xml", sheet)


def main():
    make_files()
    docs = {os.path.basename(d["source"]): d["text"] for d in loader.load_documents([TMP])}
    checks = [
        ("html 剥标签且去掉 script", "RAG 是检索增强生成。" in docs.get("a.html", "")
         and "var x" not in docs.get("a.html", "")),
        ("csv 变成 列名：值 的可读文本", "岗位：AI应用开发" in docs.get("b.csv", "")),
        ("xlsx 手写解析出表格文本（无需 openpyxl）",
         "技能" in docs.get("c.xlsx", "") and "92%" in docs.get("c.xlsx", "")),
    ]
    chunk = ("RAG 是检索增强生成。它先把文档切块并向量化。"
             "检索时用向量距离找最相关的块，再把它们放进提示词。这样能减少模型幻觉。")
    loc = locate.locate("RAG 里怎么找最相关资料？", chunk)
    checks += [
        ("句级定位挑出最支撑的那句", "向量距离" in loc["quote"]),
        ("引文是原文子串（能核对）", loc["quote"] in chunk),
        ("带字符偏移（前端可高亮）", isinstance(loc["offset"], int) and loc["offset"] > 0),
    ]
    # 引用结构（不依赖模型的纯函数部分）
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from qa_v3 import citations
    cits = citations("如何减少幻觉？", [{"text": chunk, "source": "x.md",
                                        "id": "1", "rerank_score": 0.5}])
    checks.append(("citations 带 quote/offset/locate_score",
                   all(k in cits[0] for k in ("quote", "offset", "locate_score"))))

    import shutil
    shutil.rmtree(TMP, ignore_errors=True)
    ok = 0
    for name, good in checks:
        print(("✅ " if good else "❌ ") + name)
        ok += 1 if good else 0
    print("\n%d/%d 通过" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
