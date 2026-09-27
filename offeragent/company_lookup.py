# -*- coding: utf-8 -*-
"""
company_lookup · 公司速查
=========================
拿到一个公司名，帮你在投递前先看一眼：这公司大概什么情况、投它有啥风险。

**重要：这个模块的输出可信度比其它功能低，必须在界面上显著标注。**
原因：
  1. 数据来源是公开网页抓取 + 模型总结，可能过时或不完整
  2. 工商信息、融资、口碑这类信息没有权威免费接口，我们拿不到准数
  3. 所以这里的结论只能当"线索"，不能当"事实"，尤其不能拿它去下结论说某公司不好

输出分两块：
  · 从抓到的一手页面文本里摘出的**原文片段**（可核查）
  · 模型的**推断**（明确标注为推断）
"""
import re

EXTRACT_PROMPT = """下面是从公开网页抓到的关于某家公司的文本。请严格分两块输出。

=== 原文线索 ===
只抄文本里**确实出现**的句子或短语，最多 5 条，每条注明这属于什么（主营业务/规模/融资/招聘信息/其他）。
文本里没有的就不要写，不要凭印象补。

=== 推断 ===
基于上面的线索做有限推断，最多 3 条。每条必须写成"可能 / 看起来"这种带不确定性的说法，
并注明推断依据是哪条线索。信息不足就直接写"信息不足，无法判断"。

严禁写：公司好不好、值不值得去、是不是骗子这类评价性结论。

公司名：
"""


def _clean(t: str) -> str:
    import html as _h
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = _h.unescape(t)
    t = re.sub(r"[ \t\u3000]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


def fetch_pages(company: str, use_browser: bool = True, limit: int = 3) -> list:
    """抓几个公开页面（招聘站搜索页 + 官网候选）。返回 [(url, 文本)]"""
    from urllib.parse import quote
    urls = [
        f"https://www.nowcoder.com/search?query={quote(company)}",
        f"https://www.shixiseng.com/interns?keyword={quote(company)}",
    ]
    out = []
    for u in urls[:limit]:
        text = ""
        if use_browser:
            try:
                import browser_fetch as bf
                text = _clean(bf.fetch_html(u, wait=5))
            except Exception:
                text = ""
        if len(text) < 400:
            try:
                import requests
                r = requests.get(u, timeout=20, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                text = _clean(r.text)
            except Exception:
                text = ""
        if len(text) > 200:
            out.append((u, text[:8000]))
    return out


def lookup(company: str, ask_model, use_browser: bool = True) -> dict:
    """查一家公司。返回 {sources: [(url, 文本)], report: str}"""
    pages = fetch_pages(company, use_browser=use_browser)
    if not pages:
        return {"sources": [], "report": ""}
    merged = "\n\n".join(f"【来源 {i + 1}】{u}\n{t}" for i, (u, t) in enumerate(pages))
    report = ask_model(EXTRACT_PROMPT + company + "\n\n" + merged[:12000]) or ""
    return {"sources": pages, "report": report}
