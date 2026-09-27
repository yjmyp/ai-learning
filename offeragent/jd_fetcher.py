# -*- coding: utf-8 -*-
"""
jd_fetcher · 岗位 JD 联网抓取模块
=================================
抓取招聘页文本并自动提取 JD 关键区。
策略：直连优先（国内站点快）；失败再用 r.jina.ai 代理（反爬友好）。
"""
import html as html_mod
import re

import requests

CONNECT_TIMEOUT = 8
READ_TIMEOUT = 30
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# JD 关键区锚点：命中任一即开始提取正文
START_ANCHORS = [
    "岗位职责", "职位描述", "工作内容", "岗位要求", "任职要求",
    "任职资格", "职位要求", "工作职责", "我们希望你", "你将负责",
    "职位介绍", "岗位描述", "职责描述", "Job Description",
]
# 噪音锚点：命中即停止（正文尾部）
END_ANCHORS = [
    "公司介绍", "公司简介", "关于我们", "投递方式", "工作地址",
    "上班地址", "工作地点", "福利待遇", "薪资待遇", "公司信息",
    "欢迎投递", "期待你的加入",
]


def looks_like_html(text: str) -> bool:
    return bool(re.search(r"<[a-zA-Z/!][^>]*>", text[:2000]))


def html_to_text(html: str) -> str:
    """HTML → 可读文本：去脚本样式标签、块级标签换行、实体解码。"""
    html = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ",
                  html, flags=re.S | re.I)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    html = re.sub(r"</(p|div|li|h[1-6]|tr|section|article)>", "\n",
                  html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    text = html_mod.unescape(html)
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def fetch_page_text(url: str, use_proxy: bool = True) -> str:
    """抓取页面文本。直连优先，反爬失败时用 r.jina.ai 代理。
    返回清洗后的文本；全部失败抛异常。
    """
    # 1) 直连
    try:
        r = requests.get(url, headers={"User-Agent": UA},
                         timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        if r.status_code == 200 and len(r.text) > 100:
            t = r.text
            if looks_like_html(t):
                t = html_to_text(t)
            if len(t.strip()) > 80:
                return t
    except Exception:
        pass
    # 2) r.jina.ai 代理（可选，防反爬）
    if use_proxy:
        try:
            r = requests.get("https://r.jina.ai/" + url,
                             headers={"User-Agent": UA},
                             timeout=(CONNECT_TIMEOUT, READ_TIMEOUT + 10))
            if r.status_code == 200 and r.text and len(r.text.strip()) > 50:
                return r.text
        except Exception:
            pass
    raise RuntimeError("无法抓取该页面：可能反爬或需登录。可换手机版链接，或浏览器打开后复制文本粘贴。")


def extract_jd(raw_text: str) -> str:
    """从页面文本中提取 JD 主体：从起始锚点到结束锚点。"""
    if not raw_text:
        return ""
    text = raw_text.replace("\r", "")
    lines = [ln.strip() for ln in text.split("\n")]
    start = None
    for i, ln in enumerate(lines):
        if ln and any(ln.startswith(a) or a in ln[:20] for a in START_ANCHORS):
            start = i
            break
    if start is None:
        start = int(len(lines) * 0.25)  # 兜底：跳过导航区
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j] and any(a in lines[j] for a in END_ANCHORS):
            end = j
            break
    body = "\n".join(lines[start:end])
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def guess_job_name(url: str, raw_text: str = "") -> str:
    """从页面文本或 URL 猜岗位名。"""
    m = re.search(r"(?:岗位|职位|招聘)[：:]\s*([\u4e00-\u9fa5A-Za-z0-9（）()·\-\s]{2,30})",
                  raw_text)
    if m:
        return m.group(1).strip()
    m = re.search(r"/([\w\-]+?)(?:\.s?html?)?$", url.rstrip("/"))
    if m:
        return m.group(1)
    return "url_job"


def fetch_jd(url: str) -> dict:
    """一键：抓 URL → 提取 JD → 猜岗位名。
    返回 {"name": 岗位名, "jd": JD 文本, "source_url": url}。
    """
    if not url or not url.startswith(("http://", "https://")):
        raise ValueError("请输入合法的网址（http:// 或 https:// 开头）")
    raw = fetch_page_text(url)
    jd = extract_jd(raw)
    if len(jd) < 80:
        raise ValueError("提取的 JD 内容过短，可能是登录墙/验证码页。"
                         "可换手机版链接，或浏览器打开后复制文本手动粘贴。")
    name = guess_job_name(url, raw)
    return {"name": name, "jd": jd, "source_url": url}
