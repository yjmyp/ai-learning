# -*- coding: utf-8 -*-
"""文档解析：支持 .txt/.md/.pdf/.docx/.html/.htm/.csv/.xlsx，返回 [{text, source}]

多格式实现说明（都不引新依赖）：
  · html/htm：标准库 HTMLParser 剥标签，保留段落换行
  · csv     ：标准库 csv（优先 pandas，装了就用）
  · xlsx    ：**手写解析**——xlsx 本质是 zip + XML（sharedStrings.xml + sheet1.xml），
              用 zipfile + ElementTree 读，不依赖 openpyxl（本机没装）
"""
import csv
import io
import os
import re
import zipfile
from html.parser import HTMLParser
from xml.etree import ElementTree as ET

from pypdf import PdfReader
from docx import Document

SUPPORTED_EXT = {".txt", ".md", ".pdf", ".docx", ".html", ".htm", ".csv", ".xlsx"}


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


class _TextExtractor(HTMLParser):
    """把 HTML 转成纯文本：块级标签后补换行，丢掉 script/style。"""

    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6",
             "section", "article", "table", "ul", "ol", "blockquote", "pre"}
    DROP = {"script", "style", "noscript", "head"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._drop_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.DROP:
            self._drop_depth += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.DROP and self._drop_depth:
            self._drop_depth -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self._drop_depth and data.strip():
            self.parts.append(data.strip())

    def text(self):
        return "".join(self.parts)


def _read_html(path):
    raw = _read_text(path)
    p = _TextExtractor()
    p.feed(raw)
    return p.text()


def _read_csv(path):
    raw = _read_text(path)
    rows = list(csv.reader(io.StringIO(raw)))
    if not rows:
        return ""
    header = rows[0]
    lines = ["、".join(h for h in header if h.strip())]
    for r in rows[1:]:
        if not any(c.strip() for c in r):
            continue
        lines.append("；".join("%s：%s" % (header[i] if i < len(header) else "列%d" % i,
                                        c) for i, c in enumerate(r) if c.strip()))
    return "\n".join(lines)


def _read_xlsx(path):
    """手写 xlsx 解析：zip → sharedStrings.xml + sheet1.xml → 行列文本。

    只读第一个工作表；合并单元格、公式缓存值不保证完整，够问答入库用。
    """
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall("%ssi" % ns):
                shared.append("".join(t.text or "" for t in si.iter("%st" % ns)))
        sheets = [n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n)]
        if not sheets:
            return ""
        root = ET.fromstring(z.read(sorted(sheets)[0]))
        lines = []
        for row in root.iter("%srow" % ns):
            cells, max_col = {}, 0
            for c in row.findall("%sc" % ns):
                ref = c.get("r") or ""
                col_letters = re.match(r"([A-Z]+)", ref)
                col = 0
                for ch in (col_letters.group(1) if col_letters else "A"):
                    col = col * 26 + (ord(ch) - 64)
                max_col = max(max_col, col)
                v = c.find("%sv" % ns)
                val = v.text if v is not None and v.text else ""
                if c.get("t") == "s" and val.isdigit():
                    idx = int(val)
                    val = shared[idx] if idx < len(shared) else val
                elif c.get("t") == "inlineStr":
                    # 有些工具（含 LibreOffice 导出）把文本内联写，不走 sharedStrings
                    is_node = c.find("%sis" % ns)
                    if is_node is not None:
                        val = "".join(t.text or "" for t in is_node.iter("%st" % ns))
                cells[col] = (val or "").strip()
            if any(cells.values()):
                lines.append("；".join("%s" % cells.get(i, "") for i in range(1, max_col + 1)
                                       if cells.get(i)))
        return "\n".join(lines)


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
                    elif ext in (".html", ".htm"):
                        text = _read_html(path)
                    elif ext == ".csv":
                        text = _read_csv(path)
                    elif ext == ".xlsx":
                        text = _read_xlsx(path)
                    else:
                        text = _read_docx(path)
                except Exception as exc:
                    print(f"[warn] 解析失败 {path}: {exc}")
                    continue
                text = _normalize(text).strip()
                if text:
                    docs.append({"text": text, "source": os.path.relpath(path)})
    return docs
