# -*- coding: utf-8 -*-
"""
resume_clean · 简历文本清洗
===========================
解决的问题：简历里混进本地文件路径的乱码，例如
    file:///C:/Users/29947/Documents/Codex/ai-learning/%E7%AE%80%E5%8E%86/%E4%BD%99%E5%89%91-%E7%AE%80%E5%8E%86-AI%E5%B...
这种串是「把本地文件拖进浏览器/编辑器」时生成的，对人没有意义，出现在简历里只会显得不专业。

清洗规则（只删明显无意义的，不动正文）：
  1. file:///... 整条链接删掉
  2. Windows 绝对路径 C:\\Users\\... 或 C:/Users/... 删掉
  3. 孤立的百分号编码串（%E7%AE%80 这类连续 3 组以上）删掉
  4. 零宽字符、控制字符、连续 4 个以上空行清理

用法：
    from resume_clean import clean
    text, report = clean(text)      # report 列出都删了什么，方便提示用户
"""
import re

RE_FILE_URL = re.compile(r"file:///\S+")
RE_WIN_PATH = re.compile(r"[A-Za-z]:[\\/](?:[^\s，。；)】\]]+[\\/])*[^\s，。；)】\]]*")
RE_PCT_RUN = re.compile(r"(?:%[0-9A-Fa-f]{2}){3,}")
RE_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]")
RE_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
RE_BLANK_RUN = re.compile(r"\n{4,}")


def clean(text: str) -> tuple:
    """返回 (清洗后的文本, [(规则名, 命中次数, 样例)])。"""
    if not text:
        return text or "", []
    report = []

    def _sub(pattern, text_in, name):
        hits = pattern.findall(text_in)
        if hits:
            report.append((name, len(hits), str(hits[0])[:60]))
            text_in = pattern.sub("", text_in)
        return text_in

    out = _sub(RE_FILE_URL, text, "本地文件链接 file:///")
    out = _sub(RE_WIN_PATH, out, "本机绝对路径（C:\\…）")
    out = _sub(RE_PCT_RUN, out, "百分号编码乱码（%E7%AE%80…）")
    out = _sub(RE_ZERO_WIDTH, out, "零宽字符")
    out = _sub(RE_CTRL, out, "控制字符")

    blank_hits = len(RE_BLANK_RUN.findall(out))
    if blank_hits:
        report.append(("多余空行", blank_hits, ""))
        out = RE_BLANK_RUN.sub("\n\n\n", out)

    out = "\n".join(line.rstrip() for line in out.splitlines())
    out = re.sub(r"\n[ \t]*[-*]\s*\n", "\n", out)
    return out, report


def has_junk(text: str) -> bool:
    """快速判断有没有需要清洗的东西。"""
    if not text:
        return False
    return bool(RE_FILE_URL.search(text) or RE_WIN_PATH.search(text)
                or RE_PCT_RUN.search(text) or RE_ZERO_WIDTH.search(text)
                or RE_CTRL.search(text))
