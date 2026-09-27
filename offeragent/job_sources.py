# -*- coding: utf-8 -*-
"""
job_sources · 岗位来源（联网搜岗）
==================================
三个源，各用最合适的抓法：

  nowcoder   牛客实习中心 —— 页面里有结构化 JSON，直接解析，不用大模型（最快最稳）
  shixiseng  实习僧       —— 抓页面文本，交给大模型抽成岗位列表
  boss       BOSS直聘     —— 强反爬，走真实浏览器（browser_fetch 复用你的登录态），
                            再交给大模型抽成岗位列表

统一返回：[{title, company, city, salary, url, extra, source}]
"""
import json
import re
import time
from urllib.parse import quote

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
H = {"User-Agent": UA}

BOSS_CITY_CODES = {
    "全国": "100010000", "北京": "101010100", "上海": "101020100",
    "广州": "101280100", "深圳": "101280600", "杭州": "101210100",
    "南京": "101190100", "苏州": "101190400", "成都": "101270100",
    "武汉": "101200100", "西安": "101110100", "长沙": "101250100",
}

SOURCES = ["牛客", "实习僧", "BOSS直聘"]


def html_to_text(html: str) -> str:
    """HTML → 纯文本（给大模型看）。"""
    import html as _h
    html = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html,
                  flags=re.S | re.I)
    html = re.sub(r"</(p|div|li|h[1-6]|tr|section|article|a)>", "\n", html,
                  flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    text = _h.unescape(html)
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


# ============================================================
# 1) 牛客：结构化解析（不用大模型，最快最稳）
# ============================================================
def search_nowcoder(keyword: str = "", city: str = "") -> list:
    url = "https://www.nowcoder.com/jobs/intern/center"
    pat = r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;"
    text = ""
    # 牛客这个页面偶尔不带结构化数据（CDN 差异），所以重试 3 次，再不行就上浏览器
    for _ in range(3):
        try:
            text = requests.get(url, headers=H, timeout=25).text
        except Exception:
            text = ""
        if re.search(pat, text, re.S):
            break
        time.sleep(1)
    m = re.search(pat, text, re.S)
    if not m:
        try:  # 兜底：用真实浏览器渲染后再取一次
            import browser_fetch as bf
            text = bf.fetch_html(url, wait=5)
            m = re.search(pat, text, re.S)
        except Exception:
            m = None
    if not m:
        raise RuntimeError("牛客这个页面没返回结构化数据（试了 3 次 + 浏览器渲染）。"
                           "可以换个来源，或稍后再试")
    state = json.loads(m.group(1))
    raw_jobs = state.get("store", {}).get("interCenter", {}).get("jobList", [])

    jobs = []
    for j in raw_jobs:
        title = (j.get("jobName") or "").strip()
        jcity = j.get("jobCity") or ""
        keys = j.get("jobKeys") or ""
        blob = f"{title} {keys} {jcity}"
        if keyword and keyword.lower() not in blob.lower():
            continue
        if city and city not in blob:
            continue
        salary = ""
        if j.get("salaryMin") and j.get("salaryMax"):
            salary = f"{j['salaryMin']}-{j['salaryMax']}/天"
        extra_bits = []
        if keys:
            extra_bits.append(f"技能 {keys}")
        if j.get("graduationYear"):
            extra_bits.append(str(j["graduationYear"]))
        if j.get("durationMonths"):
            extra_bits.append(f"实习 {j['durationMonths']} 个月")
        # 牛客的结构化数据里带要求原文，直接拿来当 JD（不用再抓详情页）
        ext = j.get("ext") or {}
        if isinstance(ext, str):
            try:
                ext = json.loads(ext)
            except Exception:
                ext = {}
        jd_parts = []
        if ext.get("requirements"):
            jd_parts.append("任职要求：\n" + str(ext["requirements"]).strip())
        if ext.get("jobDuty") or ext.get("duty"):
            jd_parts.append("岗位职责：\n" + str(ext.get("jobDuty") or ext.get("duty")).strip())
        job_jd = "\n\n".join(jd_parts)
        jobs.append({
            "title": title,
            "company": j.get("companyName") or f"company#{j.get('companyId', '')}",
            "city": jcity,
            "salary": salary,
            "url": f"https://www.nowcoder.com/job/center/{j.get('id')}",
            "extra": " | ".join(extra_bits),
            "source": "牛客",
            "jd": job_jd,
        })
    return jobs


# ============================================================
# 2) 通用：页面文本 → 让大模型抽成岗位列表
# ============================================================
EXTRACT_PROMPT = """下面是一个招聘网站的页面文本。请把里面的岗位列表抽成 JSON 数组。

每个岗位的字段：
- title：岗位名称
- company：公司名（页面里没有就写空字符串）
- city：城市
- salary：薪资原文（没有就写空字符串）
- url：岗位详情链接（完整 URL；没有就写空字符串）

要求：
1. 只输出 JSON 数组，不要解释、不要 markdown 代码块
2. 最多 20 条
3. 导航、广告、页脚这类内容不要抽
4. 看不清的字段留空，不要编

页面文本：
"""


# 明显不是岗位名的词（导航、按钮、栏目名），抽出来就直接丢掉
JUNK_TITLES = {
    "实习", "招聘", "岗位", "职位", "更多", "详情", "申请", "投递", "收藏",
    "动画", "开发者", "助理", "系统", "工程师", "设计师", "运营", "产品",
    "首页", "登录", "注册", "搜索", "全部", "推荐", "热门", "最新",
}


def _is_real_job(title: str) -> bool:
    """粗筛：太短、或命中垃圾词表的，都不当岗位。"""
    t = (title or "").strip()
    if len(t) < 4:
        return False
    if t in JUNK_TITLES:
        return False
    return True


def extract_jobs(page_text: str, ask_model, source: str = "") -> list:
    text = page_text[:12000]
    out = (ask_model(EXTRACT_PROMPT + text) or "").strip()
    m = re.search(r"\[.*\]", out, re.S)
    if not m:
        return []
    try:
        rows = json.loads(m.group(0))
    except Exception:
        return []
    jobs = []
    seen = set()
    for r in (rows if isinstance(rows, list) else []):
        if not isinstance(r, dict):
            continue
        title = (r.get("title") or "").strip()
        if not _is_real_job(title):
            continue
        key = re.sub(r"\s+", "", title.lower())
        if key in seen:
            continue
        seen.add(key)
        jobs.append({
            "title": title,
            "company": (r.get("company") or "").strip(),
            "city": (r.get("city") or "").strip(),
            "salary": (r.get("salary") or "").strip(),
            "url": (r.get("url") or "").strip(),
            "extra": "",
            "source": source,
            "jd": "",
        })
    return jobs


JD_PROMPT = """下面是一个招聘岗位详情页的文本。请提取这个岗位的 JD，按下面格式输出：

岗位职责：
（逐条，原文照抄或轻微整理，不要编）

任职要求：
（逐条，原文照抄或轻微整理，不要编）

如果页面里没有对应内容，就写"页面未提供"。只输出上面两部分，不要别的解释。

页面文本：
"""


def fetch_job_detail(url: str, ask_model=None, use_browser: bool = True) -> str:
    """抓一个岗位详情页，提取 JD。抓不到就返回空字符串（不编）。"""
    if not url:
        return ""
    html = ""
    if use_browser:
        try:
            import browser_fetch as bf
            html = bf.fetch_html(url, wait=5)
        except Exception:
            html = ""
    if len(html) < 3000:
        try:
            html = requests.get(url, headers=H, timeout=25).text
        except Exception:
            pass
    if not html:
        return ""
    text = html_to_text(html)
    if not ask_model:
        return text[:3000]
    out = (ask_model(JD_PROMPT + text[:10000]) or "").strip()
    return out if len(out) > 30 else ""


# ============================================================
# 3) 实习僧：requests 抓页面 → 大模型抽
# ============================================================
def search_shixiseng(keyword: str, city: str = "南京", ask_model=None) -> list:
    if not ask_model:
        raise RuntimeError("这个源需要 ask_model 才能解析")
    url = (f"https://www.shixiseng.com/interns?keyword={quote(keyword)}"
           f"&city={quote(city)}")
    html = ""
    try:  # 先试浏览器渲染（实习僧是前端渲染，直连拿到的文本很糙）
        import browser_fetch as bf
        html = bf.fetch_html(url, wait=6)
    except Exception:
        html = ""
    if len(html) < 5000:  # 浏览器没成功就退回直连
        try:
            html = requests.get(url, headers=H, timeout=25).text
        except Exception:
            pass
    if not html:
        raise RuntimeError("实习僧页面没抓到")
    return extract_jobs(html_to_text(html), ask_model, source="实习僧")


# ============================================================
# 4) BOSS：真实浏览器（复用登录态）→ 大模型抽
# ============================================================
def search_boss(keyword: str, city: str = "南京", ask_model=None) -> list:
    """走 browser_fetch（Edge 调试窗口）。需要先跑一次 setup 登录 BOSS。"""
    if not ask_model:
        raise RuntimeError("这个源需要 ask_model 才能解析")
    import browser_fetch as bf
    ok, why = bf.desktop_available()
    if not ok:
        raise RuntimeError(why)
    city_code = BOSS_CITY_CODES.get(city, "101190100")
    url = (f"https://www.zhipin.com/web/geek/job?query={quote(keyword)}"
           f"&city={city_code}")
    html = bf.fetch_html(url, wait=6)
    text = html_to_text(html)
    head = text[:1000]
    if "登录" in head and "职位" not in text:
        raise RuntimeError("BOSS 返回的像登录页。先跑一次 "
                           "python -m browser_fetch --setup，在弹出窗口里登录 BOSS 再试")
    return extract_jobs(text, ask_model, source="BOSS")


def search(source: str, keyword: str, city: str = "", ask_model=None) -> list:
    """统一入口。"""
    if source == "牛客":
        return search_nowcoder(keyword, city)
    if source == "实习僧":
        return search_shixiseng(keyword, city or "南京", ask_model)
    if source == "BOSS直聘":
        return search_boss(keyword, city or "南京", ask_model)
    raise ValueError(f"未知来源：{source}")


# ============================================================
# 5) 多平台合并搜岗
# ============================================================
ALL_SOURCES = "全部平台（合并去重）"


def boss_available() -> tuple:
    """BOSS 能不能用：返回 (bool, 原因)。云端/没浏览器时为 False。"""
    try:
        import browser_fetch as bf
        return bf.desktop_available()
    except Exception as e:
        return False, f"浏览器抓取模块不可用：{str(e)[:120]}"


def search_all(keyword: str, city: str = "南京", ask_model=None,
               sources: list = None) -> dict:
    """一次搜索，把多个平台的结果合并去重。

    返回 {
      "jobs": [...],                 # 合并去重后的岗位，牛客优先、其余按平台顺序
      "by_source": {"牛客": 5, ...},  # 每个平台拿到几条
      "errors": {"BOSS": "需要先登录"}, # 哪个平台失败、为什么
    }
    """
    targets = sources or ["牛客", "实习僧", "BOSS直聘"]
    merged, seen, by_source, errors = [], set(), {}, {}

    # BOSS 需要本机浏览器；云端直接跳过，并把原因写清楚
    try:
        import browser_fetch as bf
        _ok, _why = bf.desktop_available()
    except Exception as e:
        _ok, _why = False, str(e)[:120]
    if not _ok and "BOSS直聘" in targets:
        targets = [t for t in targets if t != "BOSS直聘"]
        errors["BOSS直聘"] = _why

    for src in targets:
        try:
            rows = search(src, keyword, city, ask_model)
            by_source[src] = len(rows)
        except Exception as e:
            by_source[src] = 0
            errors[src] = str(e)[:200]
            continue
        for j in rows:
            # 去重键：岗位名 + 公司（都去空格和小写），防止同一岗位跨平台重复
            key = re.sub(r"\s+", "",
                         f"{(j.get('title') or '').lower()}|"
                         f"{(j.get('company') or '').lower()}")
            if key in seen:
                continue
            seen.add(key)
            merged.append(j)

    # 城市不是必填；给了城市就把明显不含该城市的排后面，但不丢弃
    if city:
        merged.sort(key=lambda j: 0 if city in (j.get("city") or "") else 1)
    return {"jobs": merged, "by_source": by_source, "errors": errors}
