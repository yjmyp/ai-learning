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
