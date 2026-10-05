# 代码包：求职链路核心（搜岗 → 打分 → 门禁 → 投递）

> 内容包括：搜岗多源入库、找工作/投递页面、话术生成（禁用词防 AI 腔）、岗位质量分、岗位详情、公司查询、ATS 关键词覆盖、面试拷问、流程条。目标是让 AI 讲透「搜岗→匹配→投递」数据链路。

## 怎么喂
把本文件全文复制给 DeepSeek，开头加一句：
> 「先读完全文代码，再按我的水平逐块讲解，一次一小步，先框架后填空，不直接给完整答案。」

## 包含的文件

| 文件 | 行数 | 说明 |
|---|---|---|
| `offeragent/job_sources.py` | 549 | 见下方代码 |
| `offeragent/pages_work.py` | 496 | 见下方代码 |
| `offeragent/pages_apply.py` | 150 | 见下方代码 |
| `offeragent/apply_assist.py` | 106 | 见下方代码 |
| `offeragent/interview_drill.py` | 114 | 见下方代码 |
| `offeragent/job_quality.py` | 73 | 见下方代码 |
| `offeragent/job_detail.py` | 96 | 见下方代码 |
| `offeragent/company_lookup.py` | 82 | 见下方代码 |
| `offeragent/pipeline.py` | 79 | 见下方代码 |
| `offeragent/resume_tailor.py` | 124 | 见下方代码 |
| `offeragent/browser_fetch.py` | 305 | 见下方代码 |
| `offeragent/jd_fetcher.py` | 127 | 见下方代码 |

**合计 2301 行**（约 8KB），在 DeepSeek 上下文内。

---

## ===== offeragent/job_sources.py（549 行）=====

```python
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


def split_terms(s: str) -> list:
    """把「AI, 大模型 算法」这种输入拆成多个关键词 / 城市（空格、逗号、分号都行）。"""
    return [t for t in re.split(r"[,，;；、\s]+", (s or "").strip()) if t]


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
def search_nowcoder(keyword: str = "", city: str = "", strict: bool = False,
                    diag: dict = None) -> list:
    """牛客实习中心。

    注意：以前是「关键词/城市不命中就直接丢掉」，结果是岗位数少得离谱
    （标题里没写「AI」的算法岗、写成「江苏南京」的城市都会被误杀）。
    现在默认**只排序不丢弃**：命中的排前面，其余照常返回，由你自己在列表里勾选。
    strict=True 才回到硬过滤。

    还有一层：首页只带 20 条（页面里的 totalCount 其实是 145+）。所以这里先调
    牛客自己的搜索接口**翻页取几页**（20 → 60~100 条），接口不通才退回首页解析。
    """
    items, api_diag = _nowcoder_api(keyword, NOWCODER_PAGES)
    if items:
        if diag is not None:
            diag.update(api_diag)
        jobs = _nowcoder_map(items, keyword, city, diag, strict=strict)
        if jobs:
            return jobs

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
    if diag is not None:
        diag.update({"raw": len(raw_jobs)})
    return _nowcoder_map(raw_jobs, keyword, city, diag,
                         strict=strict, already_flat=True)


NOWCODER_API = "/np-api/u/job/square-search"
NOWCODER_PAGES = 5          # 每页 20 条，5 页 ≈ 100 条（接口总量通常 150-300）


def _nowcoder_api(keyword: str, pages: int = NOWCODER_PAGES):
    """在浏览器页面里调牛客自己的搜索接口，翻页取多几页。

    为什么不在 Python 里直接 requests：这个接口对请求头/cookie 挑剔，直连经常
    返回「服务器错误」；让页面里的 fetch 去发就一定是对的。
    """
    kws = split_terms(keyword)
    q = f"&query={quote(kws[0])}" if kws else ""
    # 先试直连（加了 Referer/Origin 就不会被挡；这条路云端也能用，最快）
    items, err = _nowcoder_api_requests(q, pages)
    if items:
        return items, err

    js = """
    (async function(){
      var out = [], total = 0, done = 0;
      for (var p = 1; p <= %d; p++) {
        var body = 'requestFrom=1&page=' + p +
                   '&pageSize=20&recruitType=2&pageSource=5001%s';
        try {
          var r = await fetch('%s', {method: 'POST', credentials: 'include',
            headers: {'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'},
            body: body});
          var d = await r.json();
          var dd = (d && d.data) || {};
          if (dd.totalCount) { total = dd.totalCount; }
          if (dd.datas && dd.datas.length) { out = out.concat(dd.datas); done = p; }
          else { break; }
          if (dd.totalPage && p >= dd.totalPage) { break; }
        } catch (e) { break; }
        await new Promise(function(res){ setTimeout(res, 300); });
      }
      return JSON.stringify({items: out, total: total, pages: done});
    })()
    """ % (pages, q, NOWCODER_API)
    try:
        import browser_fetch as bf
        ok, why = bf.desktop_available()
        if not ok:
            return [], {"api_skipped": why[:120]}
        raw = bf.js_on_page("https://www.nowcoder.com/jobs/intern/center", js,
                            wait=6, timeout=90)
        data = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception as e:
        return [], {"api_error": str(e)[:160]}
    return (data.get("items") or []), {"api_total": data.get("total"),
                                       "api_pages": data.get("pages")}


NOWCODER_HEADERS = {
    "User-Agent": UA,
    "Referer": "https://www.nowcoder.com/jobs/intern/center",
    "Origin": "https://www.nowcoder.com",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
}


def _nowcoder_api_requests(q: str, pages: int):
    """直连接口翻页。缺了 Referer / Origin 会被判成爬虫（返回"服务器错误"）。"""
    body_tpl = ("requestFrom=1&page={p}&pageSize=20&recruitType=2"
                "&pageSource=5001" + q)
    items, total, done, err = [], 0, 0, ""
    for p in range(1, pages + 1):
        url = (f"https://www.nowcoder.com{NOWCODER_API}"
               f"?_={int(time.time() * 1000)}")
        try:
            r = requests.post(url, data=body_tpl.format(p=p),
                              headers=NOWCODER_HEADERS, timeout=20)
            d = r.json()
        except Exception as e:
            err = str(e)[:120]
            break
        dd = d.get("data") if isinstance(d.get("data"), dict) else {}
        datas = dd.get("datas") or []
        if d.get("code") != 0 or not datas:
            err = str(d.get("msg") or "")[:60]
            break
        total = dd.get("totalCount") or total
        items += datas
        done = p
        if dd.get("totalPage") and p >= dd["totalPage"]:
            break
    if items:
        diag = {"api_total": total, "api_pages": done, "api_via": "requests"}
        if err:
            diag["api_note"] = err
        return items, diag
    return [], {"api_error": err or "直连接口没返回数据"}


def _nowcoder_map(raw_jobs: list, keyword: str, city: str, diag=None,
                  strict: bool = False, already_flat: bool = False) -> list:
    """把牛客的岗位记录（接口版 / 首页版两种 schema）统一成我们的字段。"""
    kws = [k.lower() for k in split_terms(keyword)]
    cities = split_terms(city)
    jobs = []
    for j in raw_jobs:
        rec = j if already_flat else (j.get("data") or j)
        title = (rec.get("jobTitle") or rec.get("jobName") or "").strip()
        if not title:
            continue
        jcity = rec.get("city") or rec.get("jobCity") or ""
        keys = rec.get("skills") or rec.get("jobKeys") or ""
        blob = f"{title} {keys} {jcity}"
        hits = sum(1 for k in kws if k in blob.lower()) if kws else 0
        city_hit = (not cities) or any(c in blob for c in cities)
        if strict:
            if kws and not hits:
                continue
            if cities and not city_hit:
                continue
        salary = ""
        if rec.get("salary"):
            salary = str(rec["salary"])
        elif rec.get("salaryMin") and rec.get("salaryMax"):
            salary = f"{rec['salaryMin']}-{rec['salaryMax']}/天"
        extra_bits = []
        if keys:
            extra_bits.append(f"技能 {keys}")
        if rec.get("graduationYear"):
            extra_bits.append(str(rec["graduationYear"]))
        if rec.get("durationMonths"):
            extra_bits.append(f"实习 {rec['durationMonths']} 个月")
        if rec.get("companyName"):
            extra_bits.append(str(rec["companyName"]))
        # 牛客的结构化数据里带要求原文，直接拿来当 JD（不用再抓详情页）
        jd_parts = []
        if rec.get("description"):
            jd_parts.append(str(rec["description"]).strip())
        ext = rec.get("ext") or {}
        if isinstance(ext, str):
            try:
                ext = json.loads(ext)
            except Exception:
                ext = {}
        if isinstance(ext, dict) and ext.get("requirements"):
            jd_parts.append("任职要求：\n" + str(ext["requirements"]).strip())
        if isinstance(ext, dict):
            duty = ext.get("jobDuty") or ext.get("duty") or ext.get("infos")
            if duty:
                jd_parts.append("岗位职责：\n" + str(duty).strip())
        job_jd = "\n\n".join(jd_parts)
        jid = rec.get("jobId") or rec.get("id")
        jobs.append({
            "title": title,
            "company": rec.get("companyName") or f"company#{rec.get('companyId', '')}",
            "city": jcity,
            "salary": salary,
            "url": (f"https://www.nowcoder.com/job/center/{jid}" if jid else ""),
            "extra": " | ".join(extra_bits),
            "source": "牛客",
            "jd": job_jd,
            "match_hits": hits,
            "city_hit": city_hit,
        })
    # 命中的排前面（城市命中也加分），不丢数据
    jobs.sort(key=lambda x: (-x.get("match_hits", 0), not x.get("city_hit", True)))
    if diag is not None:
        diag["kept"] = len(jobs)
        diag["keywords"] = kws
        diag["cities"] = cities
    return jobs


# ============================================================
# 2) 通用：页面文本 → 让大模型抽成岗位列表
# ============================================================
EXTRACT_PROMPT = """下面是一个招聘网站的页面文本（可能是长页面的一段）。请把里面的岗位列表抽成 JSON 数组。

每个岗位的字段：
- title：岗位名称
- company：公司名（页面里没有就写空字符串）
- city：城市
- salary：薪资原文（没有就写空字符串）
- url：岗位详情链接（完整 URL；没有就写空字符串）

要求：
1. 只输出 JSON 数组，不要解释、不要 markdown 代码块
2. 最多 {max_jobs} 条；页面里有几个就抽几个，不要把不同的岗位合并
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


CHUNK_SIZE = 12000      # 每块喂给模型的字符数
MAX_CHUNKS = 5          # 一个页面最多看几块（≈6 万字）


def extract_jobs(page_text: str, ask_model, source: str = "",
                 max_jobs: int = 25, diag: dict = None) -> list:
    """页面文本 → 岗位列表。

    改动原因：以前只把前 12000 字喂给模型（招聘页顶部全是导航/广告，
    真正岗位常被截断），而且提示词写死"最多 20 条"。现在**分块抽 + 跨块去重**，
    一个页面能捞到的岗位数明显变多。
    """
    text = page_text or ""
    chunks = [text[i:i + CHUNK_SIZE]
              for i in range(0, min(len(text), CHUNK_SIZE * MAX_CHUNKS), CHUNK_SIZE)]
    if diag is not None:
        diag.update({"text_len": len(text), "chunks": len(chunks)})

    jobs, seen = [], set()
    for ck in chunks:
        prompt = EXTRACT_PROMPT.replace("{max_jobs}", str(max_jobs)) + ck
        try:
            out = (ask_model(prompt) or "").strip()
        except Exception as e:
            if diag is not None:
                diag.setdefault("errors", []).append(str(e)[:120])
            continue
        m = re.search(r"\[.*\]", out, re.S)
        if not m:
            continue
        try:
            rows = json.loads(m.group(0))
        except Exception:
            continue
        for r in (rows if isinstance(rows, list) else []):
            if not isinstance(r, dict):
                continue
            title = (r.get("title") or "").strip()
            if not _is_real_job(title):
                continue
            key = re.sub(r"\s+", "",
                         f"{title.lower()}|{(r.get('company') or '').lower()}")
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
    if diag is not None:
        diag["kept"] = len(jobs)
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
def search_shixiseng(keyword: str, city: str = "南京", ask_model=None,
                     diag: dict = None) -> list:
    if not ask_model:
        raise RuntimeError("这个源需要 ask_model 才能解析")
    kw_first = split_terms(keyword)[0] if split_terms(keyword) else ""
    city_first = split_terms(city)[0] if split_terms(city) else ""
    url = (f"https://www.shixiseng.com/interns?keyword={quote(kw_first)}"
           f"&city={quote(city_first)}")
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
    return extract_jobs(html_to_text(html), ask_model, source="实习僧", diag=diag)


# ============================================================
# 4) BOSS：真实浏览器（复用登录态）→ 大模型抽
# ============================================================
def search_boss(keyword: str, city: str = "南京", ask_model=None,
                diag: dict = None) -> list:
    """走 browser_fetch（Edge 调试窗口）。需要先跑一次 setup 登录 BOSS。"""
    if not ask_model:
        raise RuntimeError("这个源需要 ask_model 才能解析")
    import browser_fetch as bf
    ok, why = bf.desktop_available()
    if not ok:
        raise RuntimeError(why)
    kw_first = split_terms(keyword)[0] if split_terms(keyword) else ""
    city_first = split_terms(city)[0] if split_terms(city) else "南京"
    city_code = BOSS_CITY_CODES.get(city_first, "101190100")
    url = (f"https://www.zhipin.com/web/geek/job?query={quote(kw_first)}"
           f"&city={city_code}")
    html = bf.fetch_html(url, wait=6)
    text = html_to_text(html)
    head = text[:1000]
    if "登录" in head and "职位" not in text:
        raise RuntimeError("BOSS 返回的像登录页。先跑一次 "
                           "python -m browser_fetch --setup，在弹出窗口里登录 BOSS 再试")
    return extract_jobs(text, ask_model, source="BOSS", diag=diag)


def search(source: str, keyword: str, city: str = "", ask_model=None,
           diag: dict = None) -> list:
    """统一入口。"""
    if source == "牛客":
        return search_nowcoder(keyword, city, diag=diag)
    if source == "实习僧":
        return search_shixiseng(keyword, city or "南京", ask_model, diag=diag)
    if source == "BOSS直聘":
        return search_boss(keyword, city or "南京", ask_model, diag=diag)
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
      "diag": {...},                 # 抓取诊断：原始条数 / 页面长度 / 关键词拆分
    }
    """
    targets = sources or ["牛客", "实习僧", "BOSS直聘"]
    merged, seen, by_source, errors, diag = [], set(), {}, {}, {}

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
        d = {}
        try:
            rows = search(src, keyword, city, ask_model, diag=d)
            by_source[src] = len(rows)
            diag[src] = d
        except Exception as e:
            by_source[src] = 0
            errors[src] = str(e)[:200]
            diag[src] = d
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
    diag["keywords"] = split_terms(keyword)
    diag["cities"] = split_terms(city)
    return {"jobs": merged, "by_source": by_source, "errors": errors,
            "diag": diag}
```

## ===== offeragent/pages_work.py（496 行）=====

```python
# -*- coding: utf-8 -*-
"""画像与岗位库 —— OfferAgent 页面域模块（2026-09-29 从 offer_agent_app.py 拆出）"""
import json
import os
import re
import time
from pathlib import Path

import streamlit as st

# 分层公共层 + 业务子模块（宽 import 兜底，页面函数保持原名调用）
from store import *
from prompts import PROMPT_PROFILE, PROMPT_MATCH
from jd_fetcher import fetch_jd
from llm import *
from ui_kit import *
import apply_assist
import digital_twin
import distill
import job_sources
import theme
import job_quality
import resume_tailor
import interview_drill
import pipeline
import inbox_parse
import v41
import company_lookup
import job_detail
import doc_io
import resume_builder
import resume_clean
import resume_templates

def page_profile():
    hero("我的画像", "Self-Distill：先认识自己，再做匹配")
    ensure_dirs()
    me_text = read_text(ME_PATH)
    tab_distill, tab1, tab2 = st.tabs(["🧬 自我蒸馏（推荐）", "✏️ 编辑素材", "⚡ 直接生成画像"])

    with tab_distill:
        st.caption("分 5 轮 15 题，用提问的方式把你蒸馏成 6 份档案："
                   "画像 / 亮点库 / 面试答案 / 差距清单 / **工作与学习模式说明书** / **数字分身说明书**。"
                   "可以随时中断，关了页面下次接着填。")
        state = distill.load_state()
        done, total, pct = distill.progress(state)
        st.progress(pct / 100, text=f"已填 {done}/{total} 题（{pct}%）")

        for i, (round_name, hint, qs) in enumerate(distill.ROUNDS):
            answered = sum(1 for k, _ in qs if state["answers"].get(k, "").strip())
            with st.expander(f"第 {i + 1} 轮 · {round_name}（{answered}/{len(qs)}）",
                             expanded=(answered < len(qs))):
                st.caption(hint)
                for key, q in qs:
                    val = st.text_area(q, state["answers"].get(key, ""), key=f"da_{key}", height=90)
                    if val != state["answers"].get(key, ""):
                        state["answers"][key] = val
                        distill.save_state(state)

                if st.button(f"🤔 让我追问一句（第 {i + 1} 轮）", key=f"fu_{i}"):
                    with st.spinner("看看哪句最含糊…"):
                        fu = distill.make_followup(state, i, lambda p: ask_chat(p))
                    if fu and "够了" not in fu:
                        st.session_state[f"fu_text_{i}"] = fu
                    else:
                        st.session_state[f"fu_text_{i}"] = ""
                if st.session_state.get(f"fu_text_{i}"):
                    st.info("追问：" + st.session_state[f"fu_text_{i}"])
                    reply = st.text_area("回答这个追问", key=f"fur_{i}", height=80)
                    if reply.strip() and st.button("💾 存下这条补充", key=f"fus_{i}"):
                        state.setdefault("followups", {})[f"第{i + 1}轮"] = reply.strip()
                        distill.save_state(state)
                        st.success("已存下")

        st.divider()
        if pct < 100:
            st.warning(f"还有 {total - done} 题没填。填完再生成，档案质量差很多；"
                       "实在写不出可以先跳过，但生成时那部分会是空的。")
        if st.button("🧬 生成 6 份档案（调用 DeepSeek）", type="primary"):
            with st.spinner("蒸馏中…"):
                try:
                    outputs = distill.distill(state, lambda p: ask_chat(p))
                    st.success("已生成：" + "、".join(outputs.keys()))
                    for name, content in outputs.items():
                        with st.expander(f"看 {name}"):
                            st.markdown(content)
                except Exception as e:
                    st.error(str(e))
        if (DATA_DIR / "profile.md").exists():
            st.caption("生成后的 profile.md 会自动被「匹配分析」使用；"
                       "highlights.md 会被「投递话术」参考；"
                       "clone_brief.md 是数字分身说明书（面试讲 Self-Distill 时直接用这个）。")

    with tab1:
        st.caption("维护你的原始素材（me.txt）：会什么、做过什么、硬约束。每次改动自动保存。")
        new_text = st.text_area("me.txt 原始素材", me_text, height=420, key="me_editor")
        if st.button("💾 保存素材", type="primary"):
            write_text(ME_PATH, new_text)
            st.success("素材已保存")
    with tab2:
        st.caption("基于素材生成结构化画像 profile.md（匹配分析的输入）。")
        if st.button("🧬 生成画像（调用 DeepSeek）", type="primary"):
            with st.spinner("生成中…"):
                try:
                    profile = ask_chat(PROMPT_PROFILE, new_text or me_text)
                    write_text(PROFILE_PATH, profile)
                    st.success("画像已生成并保存")
                    st.markdown(profile)
                except Exception as e:
                    st.error(str(e))
        current = read_text(PROFILE_PATH)
        if current:
            with st.expander("查看当前 profile.md"):
                st.markdown(current)


# ============================================================
# 页面：岗位库（v2 · 支持 URL 一键导入）
# ============================================================
def page_jobs():
    hero("岗位库", "关键词一键搜岗 / 粘 URL 抓 JD / 手动粘贴；自动识别排除规则")
    ensure_dirs()
    tab_search, tab1, tab2 = st.tabs(["🔎 关键词搜岗（联网）", "🔗 URL 导入", "✍️ 手动粘贴"])

    # ---- 关键词搜岗 ----
    with tab_search:
        st.caption("给关键词和城市，程序自己去多个招聘站搜岗位并合并去重，勾选后一键入库。"
                   "默认走「全部平台」，一次把牛客＋实习僧＋BOSS 的结果全捞回来。")
        c1, c2, c3 = st.columns([2, 2, 2])
        kw = c1.text_input("关键词（可以写多个，用空格或逗号分开）", value="AI",
                           key="src_kw",
                           placeholder="AI 大模型 算法 / Agent,RAG")
        city = c2.text_input("城市（也可以写多个）", value="南京", key="src_city",
                             placeholder="南京 上海 / 远程")
        _boss_ok, _boss_why = job_sources.boss_available()
        _src_opts = [job_sources.ALL_SOURCES] + [
            s for s in job_sources.SOURCES if s != "BOSS直聘" or _boss_ok]
        src = c3.selectbox("来源", _src_opts, key="src_name")
        st.caption("牛客最快最稳；实习僧是实验性（偶尔拿不到详情）。")
        if _boss_ok:
            st.caption("BOSS 直聘走你**本机已登录的浏览器**：第一次要在终端跑一次 "
                       "`python -m browser_fetch --setup`，在弹出的窗口里登录 BOSS。")
            if st.button("🪟 帮我打开 BOSS 登录窗口（本机）", key="boss_setup"):
                import browser_fetch as _bf
                if _bf.launch(headless=False):
                    st.success("已打开调试窗口：在里面登录 BOSS 直聘，登录后**别关这个窗口**，"
                               "回来点「开始搜岗」即可。")
                else:
                    st.error("窗口启动失败：" + _bf.no_browser_message()[:200])
        else:
            st.warning("BOSS 直聘这次用不了，原因：" + str(_boss_why)[:300])
        if st.button("🔍 开始搜岗", type="primary", key="do_search"):
            with st.spinner(f"正在搜「{kw}」…（多平台要等十几秒）"):
                try:
                    if src == job_sources.ALL_SOURCES:
                        res = job_sources.search_all(
                            kw.strip(), city.strip(),
                            ask_model=lambda p: ask_chat(p))
                        st.session_state["src_results"] = res["jobs"]
                        st.session_state["src_stats"] = res["by_source"]
                        st.session_state["src_errors"] = res["errors"]
                        st.session_state["src_diag"] = res.get("diag", {})
                    else:
                        _d = {}
                        found = job_sources.search(
                            src, kw.strip(), city.strip(),
                            ask_model=lambda p: ask_chat(p), diag=_d)
                        st.session_state["src_results"] = found
                        st.session_state["src_stats"] = {src: len(found)}
                        st.session_state["src_errors"] = {}
                        st.session_state["src_diag"] = {src: _d}
                except Exception as e:
                    st.session_state["src_results"] = []
                    st.error(str(e))
        stats = st.session_state.get("src_stats") or {}
        errors = st.session_state.get("src_errors") or {}
        if stats:
            st.caption("各平台结果：" + "　".join(f"{k} {v} 条" for k, v in stats.items()))
        _diag = st.session_state.get("src_diag") or {}
        if _diag:
            with st.expander("🔬 抓取诊断（岗位为什么只有这些？）"):
                st.caption("这里是每个平台「页面里有多少条 → 抽出来多少条」。"
                           "数量少通常是下面几个原因，不是程序坏了：")
                for _s, _d in _diag.items():
                    if not isinstance(_d, dict):
                        continue
                    bits = []
                    if _d.get("api_total"):
                        bits.append(f"站点接口共 {_d['api_total']} 条，"
                                    f"抓了 {_d.get('api_pages')} 页")
                    if _d.get("raw") is not None:
                        bits.append(f"页面结构化岗位 {_d['raw']} 条")
                    if _d.get("text_len"):
                        bits.append(f"页面文本 {_d['text_len']} 字，分 {_d.get('chunks')} 块抽取")
                    if _d.get("keywords"):
                        bits.append("关键词 " + "、".join(_d["keywords"]))
                    if _d.get("kept") is not None:
                        bits.append(f"最终保留 {_d['kept']} 条")
                    if _d.get("api_error"):
                        bits.append("接口没通：" + str(_d["api_error"])[:60])
                    if _d.get("api_skipped"):
                        bits.append("没走接口：" + str(_d["api_skipped"])[:60])
                    st.markdown(f"- **{_s}**：" + "；".join(bits) if bits
                                else f"- **{_s}**：没有诊断数据")
                st.markdown(
                    "**想让结果更多，按这个顺序试：**\n"
                    "1. **换 BOSS 直聘**——岗位量最大，但要先在本机登录一次"
                    "（上面那个一键登录按钮），云端用不了；\n"
                    "2. **关键词写多个**：`AI 大模型 算法 数据` 这样，命中的都算；\n"
                    "3. **城市放宽**：`南京 上海 远程`，或者干脆留空搜全国；\n"
                    "4. **牛客是校招实习社区**，本身岗位就比 BOSS 少一个量级，"
                    "它的作用是稳、快、数据干净；\n"
                    "5. 单个岗位想看得更细，用「🔗 URL 导入」把链接粘进来单独抓。")
        for k, v in errors.items():
            st.warning(f"{k} 没成功：{v}")
        results = st.session_state.get("src_results", [])
        if results:
            st.success(f"合并后共 {len(results)} 条（已去重）。勾选要入库的，然后点下面的按钮。")
            picked = []
            for i, j in enumerate(results):
                q = job_quality.assess(j)
                label = (f"[{j['source']}] {j['title']} · {j['company']} · {j['city']}"
                         f"{' · ' + j['salary'] if j['salary'] else ''}"
                         f" · {job_quality.summarize(q)}")
                if st.checkbox(label, key=f"pick_{i}"):
                    picked.append(j)
                if q["flags"]:
                    with st.expander(f"　└ 质量明细：{j['title'][:24]}"):
                        for f in q["flags"]:
                            st.markdown(f"- **{f['problem']}**：{f['evidence']}"
                                        f"（-{f['penalty']} 分）")
            if picked and st.button(f"📥 把选中的 {len(picked)} 条加入岗位库",
                                    type="primary", key="save_src"):
                added = 0
                bar = st.progress(0.0, text="准备入库…")
                for idx, j in enumerate(picked):
                    name = re.sub(r"[^\w\u4e00-\u9fa5]+", "_",
                                  f"{j['source']}_{j['company']}_{j['title']}")[:60]
                    if (JDS_DIR / f"{name}.txt").exists():
                        bar.progress((idx + 1) / len(picked),
                                     text=f"跳过已存在的 {j['title']}")
                        continue
                    head = (f"岗位：{j['title']}\n公司：{j['company']}\n"
                            f"城市：{j['city']}\n薪资：{j['salary']}\n"
                            f"来源：{j['source']}\n链接：{j['url']}\n")
                    if j.get("extra"):
                        head += f"其他：{j['extra']}\n"
                    body = (j.get("jd") or "").strip()
                    if not body and j.get("url"):
                        bar.progress((idx + 0.5) / len(picked),
                                     text=f"抓取 JD：{j['title']}")
                        try:
                            body = job_sources.fetch_job_detail(
                                j["url"], ask_model=lambda p: ask_chat(p))
                        except Exception:
                            body = ""
                    if not body:
                        body = "（没抓到 JD 原文。可打开链接手动补，或直接跑匹配试试）"
                    jd_text = head + "\n" + body
                    save_new_job(name, j["city"], jd_text, j["url"], extra={
                        "source": j.get("source", ""),
                        "title": j.get("title", ""),
                        "company": j.get("company", ""),
                        "salary": j.get("salary", ""),
                        "skills": j.get("extra", ""),
                        "search_query": kw.strip(),
                        "quality": job_quality.assess(j),
                    })
                    added += 1
                    bar.progress((idx + 1) / len(picked), text=f"已入库 {j['title']}")
                bar.progress(1.0, text="完成")
                st.success(f"入库 {added} 条（含 JD 原文，重复的已跳过）。"
                           "去「匹配分析」跑一下就能看到匹配度。")
                if added:
                    next_step("saved_job")
        elif results == [] and st.session_state.get("do_search_done"):
            st.warning("没搜到结果。换个关键词或来源试试；BOSS 记得先登录。")
        st.session_state["do_search_done"] = bool(results) or st.session_state.get("do_search_done")

    # ---- URL 导入 ----
    with tab1:
        if not FETCHER_OK:
            st.error("jd_fetcher 模块未加载，URL 导入不可用")
        else:
            st.caption("把 BOSS直聘 / 猎聘 / 智联 / 官网的岗位链接粘贴进来，自动抓取 JD 并提取。")
            url = st.text_input("岗位 URL", key="fetch_url",
                                placeholder="https://www.zhipin.com/job_detail/… 或 https://www.liepin.com/job/…")
            if st.button("🌐 抓取并预览", key="do_fetch"):
                if not url.strip():
                    st.warning("请先粘贴岗位 URL")
                else:
                    with st.spinner("正在抓取页面…（约 5-30 秒）"):
                        try:
                            fetched = fetch_jd(url.strip())
                            st.session_state["fetched"] = fetched
                        except Exception as e:
                            st.error(str(e))
            fetched = st.session_state.get("fetched")
            if fetched:
                st.success(f"抓取成功：识别到岗位「{fetched['name']}」，JD {len(fetched['jd'])} 字")
                c1, c2, c3 = st.columns([2, 1, 1])
                fname = c1.text_input("岗位名（可改）", value=fetched["name"], key="fetched_name")
                fcity = c2.text_input("城市", key="fetched_city", placeholder="南京")
                fcomp = c3.text_input("公司", key="fetched_company", placeholder="选填")
                fjd = st.text_area("提取的 JD（可编辑后保存）", fetched["jd"], height=300, key="fetched_jd")
                if st.button("💾 保存入库", type="primary", key="save_fetched"):
                    msg = save_new_job(fname, fcity, fjd, source_url=url.strip(),
                                       extra={"company": fcomp.strip(),
                                              "source": "url_import"})
                    st.success(msg)
                    st.session_state.pop("fetched", None)
                    st.rerun()

    # ---- 手动粘贴 ----
    with tab2:
        c1, c2 = st.columns([2, 1])
        name = c1.text_input("岗位名（保存为文件名，如 weilan_ai）", key="job_name")
        city = c2.text_input("城市", key="job_city", placeholder="南京")
        jd_text = st.text_area("JD 全文（粘贴）", height=280, key="job_jd")
        if st.button("保存岗位", type="primary"):
            if not name:
                st.warning("请填写岗位名")
            elif len(jd_text.strip()) < 50:
                st.warning("JD 内容太短（至少 50 字），请粘贴完整 JD")
            else:
                st.success(save_new_job(name, city, jd_text))
                st.rerun()

    # ---- 岗位列表 ----
    jobs = list_jobs()
    if not jobs:
        st.info("暂无岗位")
        return
    _bm = st.session_state.pop("batch_msg", "")
    if _bm:
        st.success(_bm)
    _lm = st.session_state.pop("link_msg", None)
    if _lm:
        _kind, _text = _lm
        if _kind == "gone":
            st.error(_text)
        elif _kind == "warn":
            st.warning(_text)
        else:
            st.success(_text)
    st.markdown(f"#### 共 {len(jobs)} 个岗位")
    # ---- 批量操作（v4.1）----
    unmatched = [j for j in jobs if j[1]["status"] == "待投" and j[1].get("match_score") is None]
    bc1, bc2 = st.columns([2, 2])
    if bc1.button(f"⚡ 批量匹配（还有 {len(unmatched)} 个未评）",
                  type="primary", disabled=not unmatched, key="batch_match"):
        fprof = read_text(PROFILE_PATH) or read_text(ME_PATH)
        if not fprof.strip():
                                st.warning("先到「🧬 我的 → 自我蒸馏」生成画像")
        else:
            with st.spinner("批量匹配中…（每个岗位 20-60 秒）"):
                bar = st.progress(0.0, text="准备…")
                done = v41.batch_match(
                    PROMPT_MATCH, lambda p, *m: ask_chat(p, *m),
                    jobs, fprof, progress=bar)
                st.session_state["batch_msg"] = "批量匹配完成：" + "；".join(
                    f"{n} {s}%" if s is not None else f"{n} 失败" for n, s in done)
            st.rerun()
    if bc2.button("🔗 检查全部链接是否失效", key="batch_check_link"):
        with st.spinner("正在重访岗位链接…（每家最多 6 秒）"):
            res = v41.check_links(jobs)
        gone = [r for r in res if r[3] == "gone"]
        unreach = [r for r in res if r[3] == "unreachable"]
        nourl = [r for r in res if r[3] == "no_url"]
        msgs = []
        if gone:
            msgs.append(("gone", "以下岗位链接已失效（404/410），投递前请先确认：\n" +
                         "\n".join(f"- {c}（{n}）：{u}" for n, c, u, _ in gone)))
        if unreach:
            msgs.append(("warn", "以下岗位暂时连不上（网络/超时/反爬），建议投前人工确认：\n" +
                         "\n".join(f"- {c}（{n}）" for n, c, _, _ in unreach)))
        if nourl:
            msgs.append(("warn", f"{len(nourl)} 个岗位没保存链接（v1 手动粘贴的），无法自动检测。"))
        if not gone and not unreach and not nourl:
            msgs.append(("ok", f"链接检测完成：{len(res)} 个岗位链接全部可访问"))
        st.session_state["link_msg"] = msgs[0] if msgs else ("ok", "链接检测完成，无异常")
        st.rerun()
    for name, meta, jd in jobs:
        excl = meta["status"] == "排除"
        cols = st.columns([3, 1.2, 1.2, 1.2, 1])
        with cols[0]:
            st.markdown(f"**{meta['name']}**　<span style='color:#64748B;font-size:12px'>{meta['city']}</span>"
                        f"　{status_tag(meta['status'])}", unsafe_allow_html=True)
            if excl and meta.get("excluded_reason"):
                st.caption(f"⚠️ {meta['excluded_reason']}")
            if meta.get("match_score") is not None and not excl:
                st.caption(f"匹配度 {meta['match_score']}%")
            if meta.get("source_url"):
                st.caption(f"🔗 {meta['source_url'][:60]}")
            q = meta.get("quality")
            if isinstance(q, dict):
                tag = ("oa-tag-green" if q.get("verdict") == "正常"
                       else ("oa-tag-amber" if q.get("verdict") == "存疑" else "oa-tag-red"))
                st.markdown(f'<span class="oa-tag {tag}">岗位质量 {q.get("score")} · '
                            f'{q.get("verdict")}</span>', unsafe_allow_html=True)
            with st.expander("📄 岗位档案（为什么它在列表里 + 岗位要求）"):
                render_job_detail(name, meta, jd)
            with st.expander("⚡ 一站式：匹配 → ATS → 话术 → 已投（不用换页）"):
                if excl:
                    st.caption("这个岗位已被排除，流程停用。要恢复就在右边点回「待投」。")
                else:
                    fprof = read_text(PROFILE_PATH) or read_text(ME_PATH)
                    fsc = meta.get("match_score")
                    st.markdown("**① 匹配分析**　"
                                + (f"已完成：{fsc}%" if fsc is not None else "未做"))
                    if st.button("① 运行匹配", key=f"f1_{name}"):
                        if not fprof.strip():
                            st.warning("先到「🧬 我的 → 自我蒸馏」生成画像")
                        else:
                            with st.spinner("匹配中…（约 20-60 秒）"):
                                try:
                                    rep = ask_chat(PROMPT_MATCH, fprof, jd)
                                    write_text(MATCH_DIR / f"match_{name}.md", rep)
                                    s2 = extract_score(rep)
                                    if s2 is not None:
                                        meta["match_score"] = s2
                                        save_meta(name, meta)
                                    st.session_state["flow_msg"] = f"匹配完成：{s2}%"
                                    st.rerun()
                                except Exception as e:
                                    st.error(str(e))
                    if fsc is not None:
                        st.markdown("**② ATS 简历覆盖**")
                        if st.button("② 检查简历覆盖", key=f"f2_{name}"):
                            fres = load_my_resume()
                            if not fres.strip():
                                st.warning("先到「🎯 找工作 → 简历」准备一份简历")
                            else:
                                with st.spinner("本地比对中…"):
                                    try:
                                        st.session_state[f"flow_ats_{name}"] = \
                                            resume_tailor.tailor(fres, jd,
                                                                 lambda p: ask_chat(p))
                                    except Exception as e:
                                        st.error(str(e))
                        fout = st.session_state.get(f"flow_ats_{name}")
                        if fout:
                            fmiss = [r for r in fout["coverage"] if r["status"] == "缺失"]
                            st.caption(f"关键词覆盖率 {fout['rate']}%　·　"
                                       f"缺失 {len(fmiss)} 个")
                            if fmiss:
                                st.caption("缺失：" + "、".join(r["keyword"] for r in fmiss[:12]))
                        st.markdown("**③ 投递话术**")
                        st.caption("话术统一在「投递台」生成（避免两套代码）。"
                                   "这里点一下会跳过去，并已经帮你选中这家。")
                        if st.button("③ 去投递台写话术", key=f"f3_{name}"):
                            goto_page("apply", talk_pick=name)
                        st.markdown("**④ 标记已投**")
                        st.caption("发送由你自己按；这里只负责记录状态，之后 7 天没动静会自动进跟进提醒。")
                        if st.button("④ 我发出去了，标记已投", key=f"f4_{name}"):
                            meta["status"] = "已投"
                            meta["applied_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                            save_meta(name, meta)
                            apply_assist.log_application(
                                name, meta,
                                st.session_state.get(f"talk_{name}_boss", ""))
                            st.session_state["flow_done"] = name
                            next_step("applied", defer=True)
                            st.rerun()
                    if st.session_state.get("flow_msg"):
                        st.success(st.session_state.pop("flow_msg"))
                    if st.session_state.get("flow_done") == name:
                        st.caption("已标记已投（见页面底部提示）")
        with cols[1]:
            if not excl and st.button("🔍 匹配", key=f"m_{name}"):
                goto_page("match", match_pick=name)
        with cols[2]:
            if not excl and st.button("✅ 已投", key=f"d_{name}"):
                meta["status"] = "已投"
                save_meta(name, meta)
                st.rerun()
        with cols[3]:
            if not excl and st.button("🚫 排除", key=f"x_{name}"):
                meta["status"] = "排除"
                meta["excluded_reason"] = meta.get("excluded_reason") or "手动排除"
                save_meta(name, meta)
                st.rerun()
        with cols[4]:
            if st.button("🗑", key=f"del_{name}"):
                (JDS_DIR / f"{name}.txt").unlink(missing_ok=True)
                (JDS_DIR / (name + META_SUFFIX)).unlink(missing_ok=True)
                for f in MATCH_DIR.glob(f"match_{name}.md"):
                    f.unlink(missing_ok=True)
                st.rerun()
        st.divider()


# ============================================================
# 页面：匹配分析（v2 · URL 直配 + 卡片渲染）
# ============================================================
```

## ===== offeragent/pages_apply.py（150 行）=====

```python
# -*- coding: utf-8 -*-
"""批量投递台 —— OfferAgent 页面域模块（2026-09-29 从 offer_agent_app.py 拆出）"""
import json
import os
import re
import time
from pathlib import Path

import streamlit as st

# 分层公共层 + 业务子模块（宽 import 兜底，页面函数保持原名调用）
from store import *
from prompts import TALK_VARIANTS, generate_talk
from llm import *
from ui_kit import *
import apply_assist
import digital_twin
import distill
import job_sources
import theme
import job_quality
import resume_tailor
import interview_drill
import pipeline
import inbox_parse
import v41
import company_lookup
import job_detail
import doc_io
import resume_builder
import resume_clean
import resume_templates

# 跨模块页面（拆分后补 import）
from pages_home import page_distill_chat
from pages_work import page_profile
from pages_match import page_talk

def page_batch_apply(vkey: str = "boss"):
    st.caption("批量模式：一次给全部待投岗位生成话术 → 逐条确认 → 复制 / 打开 / 标记已投。"
               "发送那一下永远留给你（自动群发会被平台风控封号）。")
    jobs = [j for j in list_jobs() if j[1]["status"] == "待投"]
    if not jobs:
        st.info("当前没有待投岗位。去「找工作 → 岗位库」把岗位状态设为「待投」。")
        return
    st.markdown(f"待投 **{len(jobs)}** 家　·　今日已投 **{apply_assist.applied_today()}** 家")

    c1, c2 = st.columns([1, 3])
    if c1.button("⚡ 批量生成全部话术", type="primary", key="bg_gen"):
        fprof = read_text(PROFILE_PATH) or read_text(ME_PATH)
        if not fprof.strip():
            st.warning("先到「🧬 我的 → 自我蒸馏」生成画像")
        else:
            queue = {}
            with st.spinner(f"为 {len(jobs)} 家生成话术…（每家几秒）"):
                for n, m, jd in jobs:
                    try:
                        t, h = generate_talk(lambda p, *mm: ask_chat(p, *mm),
                                             vkey, fprof, jd or "")
                        queue[n] = {"talk": t, "hits": h}
                    except Exception as e:
                        queue[n] = {"talk": "", "hits": [str(e)[:80]]}
                write_text(TALKQ_PATH, json.dumps(queue, ensure_ascii=False, indent=2))
            st.session_state["bg_done"] = len(queue)
            st.rerun()
    if st.session_state.get("bg_done"):
        st.success(f"已生成 {st.session_state.pop('bg_done')} 条话术。下面逐条确认、复制、打开、标记。")
        st.caption("建议节奏：复制话术 → 打开岗位 → 粘贴发送 → 回来标记已投。")

    queue = {}
    try:
        queue = json.loads(read_text(TALKQ_PATH, "{}"))
    except Exception:
        queue = {}

    for n, m, jd in sorted(jobs, key=lambda x: -(x[1].get("match_score") or 0)):
        comp = m.get("company") or n
        score = m.get("match_score")
        sc = f" · 匹配 {score}%" if score is not None else ""
        with st.expander(f"{comp}　{m.get('city', '')}{sc}", expanded=False):
            if m.get("source_url"):
                st.caption(f"🔗 {m['source_url']}")
            q = queue.get(n, {})
            talk = st.text_area("话术（可改，改完点保存）", q.get("talk", ""),
                                key=f"bq_{n}", height=90)
            if q.get("hits"):
                st.warning(f"仍含可疑用语：{q['hits']}")
            cc = st.columns(4)
            if cc[0].button("📋 复制话术", key=f"bc_{n}"):
                ok = apply_assist.copy_to_clipboard(talk)
                st.toast("已复制到剪贴板" if ok else "复制失败", icon="✅" if ok else "⚠️")
            if cc[1].button("🌐 打开岗位", key=f"bo_{n}"):
                _gate = check_apply_allowed(n, m)
                if not _gate["allowed"]:
                    st.warning(_gate["reason"])
                else:
                    ok = apply_assist.open_url(m.get("source_url", ""))
                    st.toast("已在浏览器打开" if ok else "该岗位没有链接", icon="✅" if ok else "⚠️")
            if cc[2].button("✏️ 保存修改", key=f"bs_{n}"):
                queue[n] = {"talk": talk, "hits": q.get("hits", [])}
                write_text(TALKQ_PATH, json.dumps(queue, ensure_ascii=False, indent=2))
                st.toast("已保存", icon="✅")
            if cc[3].button("✅ 发出去了，标记已投", type="primary", key=f"bm_{n}"):
                _gate = check_apply_allowed(n, m)
                if not _gate["allowed"]:
                    st.warning(_gate["reason"])
                else:
                    mark_applied(n, m)
                    apply_assist.log_application(n, m, talk or q.get("talk", ""))
                    st.session_state["_pending_hint"] = f"已标记投递：{comp}"
                    st.rerun()



def distill_section():
    """自我蒸馏（问答式 / 填表式）。chat_input 必须在页面级，所以用 radio 切换。"""
    mode = st.radio("模式", ["💬 问答式（推荐）", "📋 填表式"],
                    horizontal=True, key="distill_mode")
    if "问答" in mode:
        page_distill_chat()
    else:
        page_profile()


def page_apply_desk():
    """投递台：全应用唯一生成投递话术的地方（单条精修 / 批量一次到位）。"""
    hero("投递台", "话术、岗位链接、投递三件套一次备好；发送那一下由你自己按")
    labels = [v[0] for v in TALK_VARIANTS.values()]
    vlabel = st.segmented_control("话术场景", labels, default=labels[0],
                                  key="desk_variant") or labels[0]
    vkey = list(TALK_VARIANTS.keys())[labels.index(vlabel)]
    mode = st.segmented_control(
        "工作方式", ["🗂 批量（一次处理全部待投）", "✍️ 单条精修（一家一版）"],
        default="🗂 批量（一次处理全部待投）", key="desk_mode") \
        or "🗂 批量（一次处理全部待投）"
    st.caption("批量：适合已经筛完、要一次性推进多家。"
               "单条：适合重点公司，想逐句改。两者都只**生成**话术，发送永远由你按。")
    if "单条" in mode:
        page_talk(embedded=True, vkey=vkey)
    else:
        page_batch_apply(vkey=vkey)




# ============================================================
# 公开数字人名片页（?twin=1）：考官/HR 知情访问
# 合规说明：AI 分身基于真实画像回答，不冒充本人，最终以真人沟通为准。
# ============================================================
```

## ===== offeragent/apply_assist.py（106 行）=====

```python
# -*- coding: utf-8 -*-
"""
apply_assist · 投递辅助
=======================
两种模式，由用户自己选：

  手动模式：只把话术给你，你自己复制、自己发送（零风险）
  半自动模式：程序帮你打开岗位页 + 把话术写进系统剪贴板，你粘贴后自己按发送

**不做全自动投递。** 发送前那一眼和那一下，永远由人来做。
所有投递记录写进 data/applications.jsonl，一行一条。
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
LOG_PATH = DATA_DIR / "applications.jsonl"


def copy_to_clipboard(text: str) -> bool:
    """把文本写进系统剪贴板。成功返回 True。"""
    try:  # 方案 1：tkinter（标准库自带）
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        pass
    try:  # 方案 2：pyperclip（如果装了）
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        pass
    try:  # 方案 3：Windows 的 clip 命令（UTF-16 避免中文乱码）
        if sys.platform == "win32":
            subprocess.run("clip", input=text.encode("utf-16le"),
                           shell=True, check=True, timeout=10)
            return True
    except Exception:
        pass
    return False


def open_url(url: str) -> bool:
    """用系统默认浏览器打开链接。"""
    if not url:
        return False
    try:
        if sys.platform == "win32":
            subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
        else:
            import webbrowser
            webbrowser.open(url)
        return True
    except Exception:
        return False


def log_application(name: str, meta: dict, talk: str = "", note: str = ""):
    """记录一次投递。一行一条 JSON，方便统计和复盘。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "date": time.strftime("%Y-%m-%d"),
        "job": name,
        "company": meta.get("company", ""),
        "city": meta.get("city", ""),
        "score": meta.get("match_score"),
        "url": meta.get("source_url", ""),
        "talk": talk,
        "note": note,
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def load_applications() -> list:
    """读回全部投递记录（新到旧）。"""
    if not LOG_PATH.exists():
        return []
    rows = []
    for line in LOG_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return list(reversed(rows))


def applied_today() -> int:
    today = time.strftime("%Y-%m-%d")
    return sum(1 for r in load_applications() if r.get("date") == today)
```

## ===== offeragent/interview_drill.py（114 行）=====

```python
# -*- coding: utf-8 -*-
"""
interview_drill · 面试拷问（AI 当面试官）
=========================================
用真实面试的强度问你，而不是给你一份题库让你背。

流程：
  1. 基于「画像 + 目标 JD」生成 10 个追问（分三类，每题标注考察点）
  2. 你逐个回答 → 每答一题给三段反馈：答得好在哪 / 缺什么 / 更好的答法
  3. 答完给一份总评（哪几题最危险）

硬性要求：点评只能基于你给的事实，不许替你编经历。
状态存 data/drill_{job}.json，可中断续答。
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"

QUESTION_PROMPT = """你是面试官，正在面一个应聘 AI 应用开发实习的学生。请出 10 个追问。

要求：
1. 分三类，数量 4 / 3 / 3：
   项目细节（4 题）：追问他做过的东西的实现、取舍、踩坑、边界
   技术选型与原理（3 题）：为什么这么选、原理是什么、出问题怎么办
   动机与规划（3 题）：为什么投这个方向、短板是什么、接下来怎么补
2. 必须包含这几个问题（可以换个问法）：
   "这个项目是你自己写的吗，AI 帮了多少"
   "如果检索出来的东西全是错的，你怎么办"
   "你最大的短板是什么"
3. 每个问题后面用括号标注考察点，例如（考察：你是否真的写过这段逻辑）
4. 问题要具体到他的项目和这个岗位，不要问通用八股
5. 只输出编号列表，1 到 10，不要标题不要解释

【求职者画像】
"""

FEEDBACK_PROMPT = """你在做面试复盘。下面是面试官的问题和学生的回答。

给他三段反馈，总共不超过 150 字：
1. 答得好的地方（引用他原话里的具体亮点，如果确实没有，就直说没有）
2. 缺什么（面试官接下来会追问什么，或者哪里答偏了）
3. 一个更好的答法（只能用他给的事实，不许替他编经历或数字）

格式：
✅ 好的：
⚠️ 缺的：
💡 换个说法：

问题：
"""


def _state_path(job: str) -> Path:
    safe = re.sub(r"[^\w\u4e00-\u9fa5]+", "_", job)[:50]
    return DATA_DIR / f"drill_{safe}.json"


def load_state(job: str) -> dict:
    p = _state_path(job)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"job": job, "questions": "", "items": []}


def save_state(state: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _state_path(state["job"]).write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_questions(text: str) -> list:
    """把编号列表切成题目。"""
    out = []
    for line in (text or "").splitlines():
        s = line.strip()
        m = re.match(r"^(\d+)[.、)]\s*(.+)$", s)
        if m:
            out.append(m.group(2).strip())
    return out


def make_questions(profile: str, jd: str, ask_model) -> tuple:
    """生成 10 题。返回 (原始文本, 题目列表)"""
    text = ask_model(QUESTION_PROMPT + profile + "\n\n【目标岗位 JD】\n" + jd) or ""
    return text, parse_questions(text)


def feedback(question: str, answer: str, ask_model) -> str:
    return (ask_model(FEEDBACK_PROMPT + question + "\n\n回答：" + answer) or "").strip()


SUMMARY_PROMPT = """下面是一个学生做过的面试模拟问答。请给一份总评（不超过 200 字）：

## 最危险的三个问题
（哪几题答得最弱，为什么危险）

## 最该补的一件事
（只给一件，要具体到"做什么、大概多久"）

要求：只说事实和判断，不要鼓励式的话，不要"加油"。
"""


def total_review(items: list, ask_model) -> str:
    body = "\n\n".join(
        f"问：{it.get('q')}\n答：{it.get('a')}\n点评：{it.get('f')}" for it in items)
    return (ask_model(SUMMARY_PROMPT + body) or "").strip()
```

## ===== offeragent/job_quality.py（73 行）=====

```python
# -*- coding: utf-8 -*-
"""
job_quality · 岗位质量检查（假岗 / 僵尸岗识别）
================================================
设计原则：只用能验证的信号，不做主观猜测。每条结论都要能说清依据。
纯规则实现，不调用大模型：快、免费、可解释、结果稳定。

检查项与依据：
  1. JD 内容过少        JD + 其他信息总长 < 60 字
  2. 没有公司名         公司字段为空或是 company#xxx 占位
  3. 薪资区间过宽       上限 > 下限 x 5（例如 10-1000/天）
  4. 薪资明显偏低       一线/新一线城市上限 < 80/天
  5. JD 像模板复读      同时出现"岗位职责"和"任职要求"但全文 < 200 字
  6. 发布时间过久       平台最后刷新时间超过 60 天（牛客提供）
  7. 缺链接             没有可点开的岗位详情链接
"""
import re


def assess(job: dict) -> dict:
    """评估一个岗位。返回 {score, verdict, flags}"""
    flags = []
    score = 100
    jd = ((job.get("jd") or "") + " " + (job.get("extra") or "")).strip()

    def add(problem, evidence, penalty):
        flags.append({"problem": problem, "evidence": evidence, "penalty": penalty})
        return penalty

    if len(jd) < 60:
        score -= add("JD 内容过少", f"职责与要求一共 {len(jd)} 字", 25)

    comp = (job.get("company") or "").strip()
    if not comp or comp.startswith("company#"):
        score -= add("看不到公司名", "平台没返回公司名称", 20)

    sal = (job.get("salary") or "").replace(" ", "")
    m = re.match(r"(\d+)-(\d+)", sal)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo <= 0:
            score -= add("薪资下限异常", f"原文 {sal}", 12)
        elif hi > lo * 5:
            score -= add("薪资区间过宽",
                         f"原文 {sal}（上限是下限的 {hi // max(lo, 1)} 倍）", 10)
        cities = ("南京", "上海", "北京", "深圳", "杭州", "广州", "苏州")
        if hi < 80 and (job.get("city") or "") in cities:
            score -= add("薪资偏低", f"{job.get('city')} 实习上限 {hi}/天", 10)

    has_duty = ("岗位职责" in jd) or ("职位描述" in jd)
    has_req = ("任职要求" in jd) or ("任职资格" in jd)
    if has_duty and has_req and len(jd) < 200:
        score -= add("JD 像模板复读", f"同时出现职责与要求，全文只有 {len(jd)} 字", 10)

    days = job.get("posted_days")
    if isinstance(days, int) and days >= 60:
        score -= add("岗位可能挂很久了", f"平台最后刷新在 {days} 天前", 20)

    if not (job.get("url") or "").startswith("http"):
        score -= add("没有岗位链接", "无法点开原文核对", 8)

    score = max(0, min(100, score))
    verdict = "正常" if score >= 80 else ("存疑" if score >= 60 else "疑似僵尸岗")
    return {"score": score, "verdict": verdict, "flags": flags}


def summarize(result: dict) -> str:
    """一句话总结，用于列表显示。"""
    if result["verdict"] == "正常":
        return f"质量 {result['score']} 分（没发现明显问题）"
    first = result["flags"][0]["problem"] if result["flags"] else "有问题"
    return f"质量 {result['score']} 分 · {result['verdict']}（{first}）"
```

## ===== offeragent/job_detail.py（96 行）=====

```python
# -*- coding: utf-8 -*-
"""
job_detail · 岗位档案与筛选依据（可解释性）
============================================
商业化产品的一个硬指标：**用户要能看懂"为什么这个岗位出现在我的列表里"。**

这个模块把一件事说清楚，分三段：
  1. 它是怎么进来的（来源平台、搜索关键词、命中原因、入库时间）
  2. 它为什么被保留 / 被排除（质量检查逐项 + 排除规则命中的原文）
  3. 它到底要什么人（岗位职责 / 任职要求 结构化展示，不是一坨文本）
"""
import re

DUTY_ANCHORS = ["岗位职责", "职位描述", "工作内容", "工作职责", "你将负责",
                "职位介绍", "岗位描述", "职责描述", "Job Description"]
REQ_ANCHORS = ["任职要求", "任职资格", "岗位要求", "职位要求", "我们希望你",
               "任职条件", "资格要求", "Requirements"]


def split_jd(jd: str) -> dict:
    """把 JD 文本按锚点切成 职责 / 要求 / 其他 三块。"""
    text = (jd or "").replace("\r", "")
    lines = text.split("\n")
    sections = {"duty": [], "req": [], "other": []}
    cur = "other"
    for line in lines:
        s = line.strip()
        head = s[:12]
        if any(a in head for a in DUTY_ANCHORS):
            cur = "duty"
            rest = re.sub("|".join(DUTY_ANCHORS), "", s).lstrip("：: ")
            if rest:
                sections[cur].append(rest)
            continue
        if any(a in head for a in REQ_ANCHORS):
            cur = "req"
            rest = re.sub("|".join(REQ_ANCHORS), "", s).lstrip("：: ")
            if rest:
                sections[cur].append(rest)
            continue
        if s:
            sections[cur].append(s)
    return {k: "\n".join(v).strip() for k, v in sections.items()}


def entry_reasons(meta: dict) -> list:
    """这个岗位是怎么进来的。返回 [ {label, detail} ]"""
    out = []
    src = meta.get("source") or "手动导入"
    out.append({"label": "来源", "detail": src})
    if meta.get("search_query"):
        kw = meta["search_query"]
        hit = []
        if kw.lower() in (meta.get("title") or "").lower():
            hit.append("岗位名里有这个关键词")
        if kw.lower() in (meta.get("skills") or "").lower():
            hit.append("技能标签命中")
        if kw in (meta.get("city") or ""):
            hit.append("城市命中")
        out.append({"label": "搜索关键词", "detail": kw})
        out.append({"label": "命中原因",
                    "detail": "；".join(hit) if hit else "平台搜索结果里返回了它（未做本地二次过滤）"})
    if meta.get("created_at"):
        out.append({"label": "入库时间", "detail": str(meta["created_at"])})
    if meta.get("source_url"):
        out.append({"label": "原始链接", "detail": str(meta["source_url"])})
    return out


def keep_or_drop(meta: dict) -> list:
    """为什么保留 / 为什么排除。返回 [ {label, detail, ok} ]"""
    out = []
    if meta.get("status") == "排除":
        out.append({"label": "排除原因",
                    "detail": meta.get("excluded_reason") or "手动排除",
                    "ok": False})
        ev = meta.get("excluded_evidence")
        if ev:
            out.append({"label": "命中原文",
                        "detail": f"「{ev}」", "ok": False})
    q = meta.get("quality")
    if isinstance(q, dict):
        out.append({"label": "岗位质量分",
                    "detail": f"{q.get('score')} 分 · {q.get('verdict')}", "ok": True})
        for f in q.get("flags", []):
            out.append({"label": f"扣分项：{f.get('problem')}",
                        "detail": f"{f.get('evidence')}（-{f.get('penalty')} 分）",
                        "ok": False})
        if not q.get("flags"):
            out.append({"label": "质量检查", "detail": "7 项检查都没发现问题", "ok": True})
    else:
        out.append({"label": "岗位质量", "detail": "还没跑过质量检查", "ok": None})
    if meta.get("match_score") is not None:
        out.append({"label": "匹配度", "detail": f"{meta['match_score']}%", "ok": True})
    return out
```

## ===== offeragent/company_lookup.py（82 行）=====

```python
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
```

## ===== offeragent/pipeline.py（79 行）=====

```python
# -*- coding: utf-8 -*-
"""
pipeline · 投递漏斗 / 跟进提醒 / 被拒归因
=========================================
三个能力：
  1. funnel(jobs)           —— 各状态计数 + 转化率（投了多少、有多少面试、多少 offer）
  2. needs_followup(jobs)   —— 投出去超过 N 天没有动静的，该跟进了
  3. analyze_rejections()   —— 连续被拒后，用大模型找出共同点（只基于真实记录，不编）
"""
import time

STATUSES = ["待投", "已投", "面试中", "已拒", "Offer", "排除"]
ACTIVE = ["待投", "已投", "面试中", "已拒", "Offer"]


def funnel(jobs: list) -> dict:
    """jobs 是 list_jobs() 的结果。返回各状态计数和转化率。"""
    counts = {s: 0 for s in STATUSES}
    for _, meta, _ in jobs:
        st = meta.get("status", "待投")
        counts[st] = counts.get(st, 0) + 1

    submitted = counts["已投"] + counts["面试中"] + counts["已拒"] + counts["Offer"]
    interviewed = counts["面试中"] + counts["已拒"] + counts["Offer"]
    offers = counts["Offer"]

    def rate(a, b):
        return round(a / b * 100, 1) if b else 0.0

    return {
        "counts": counts,
        "submitted": submitted,
        "interviewed": interviewed,
        "offers": offers,
        "reply_rate": rate(interviewed, submitted),
        "offer_rate": rate(offers, submitted),
    }


def needs_followup(jobs: list, days: int = 7) -> list:
    """投出去超过 days 天、状态还是「已投」的岗位，该跟进了。"""
    now = time.time()
    out = []
    for name, meta, jd in jobs:
        if meta.get("status") != "已投":
            continue
        stamp = meta.get("applied_at") or meta.get("created_at") or ""
        try:
            t = time.mktime(time.strptime(stamp[:19], "%Y-%m-%d %H:%M:%S"))
        except Exception:
            continue
        d = int((now - t) / 86400)
        if d >= days:
            out.append({"name": name, "meta": meta, "days": d, "jd": jd})
    out.sort(key=lambda x: -x["days"])
    return out


REJECT_PROMPT = """下面是一个学生最近被拒的投递记录（岗位名、公司、匹配度、备注）。

请做两件事，总共不超过 200 字：
1. 共同点：这些被拒的岗位有什么共同特征（行业、岗位类型、要求）？
2. 最可能的三个原因 + 各自的补法（要具体到做什么）

硬性要求：只根据我给的信息推断，推断不出来就写"信息不足，无法判断"。
不要写鼓励的话。不要编造这些岗位的细节。

记录：
"""


def analyze_rejections(rejected: list, ask_model) -> str:
    if not rejected:
        return ""
    body = "\n".join(
        f"- {r.get('job')} | {r.get('company') or '未知公司'} | 匹配度 {r.get('score')}"
        f" | 备注 {r.get('note') or '无'}" for r in rejected)
    return (ask_model(REJECT_PROMPT + body) or "").strip()
```

## ===== offeragent/resume_tailor.py（124 行）=====

```python
# -*- coding: utf-8 -*-
"""
resume_tailor · 按 JD 定制简历 + ATS 关键词覆盖检查
====================================================
两步：
  1. 用大模型从 JD 里抽关键词（技术 / 职责 / 加分），然后**在本地**检查简历覆盖情况
     —— 覆盖检查是字符串比对，不让模型判断，避免它"觉得"覆盖了
  2. 让模型给重排与改写建议，但**写死"只能用简历里已有的经历和数字"**，
     JD 要求而简历没有的，必须写"缺失，需用户确认"，不许替他补
"""
import re

KEYWORD_PROMPT = """从下面的岗位 JD 里抽关键词，分三类，每类最多 12 个，用顿号分隔：
技术：编程语言、框架、工具、平台名（如 Python、RAG、Chroma、FastAPI）
职责：要做的事（如 检索优化、数据清洗、接口开发、效果评估）
加分：明显是加分的项（如 论文复现、开源贡献、英文文档、大模型微调）

严格按三行输出，格式：
技术：xxx、xxx
职责：xxx、xxx
加分：xxx、xxx
不要解释，不要多余文字。

岗位 JD：
"""

TAILOR_PROMPT = """你在帮一个学生按目标岗位调整简历。下面是他的简历和目标 JD。

硬性要求（违反即失败）：
1. 只能使用简历里已经出现的经历、项目和数字。不许新增经历、不许夸大、不许编造。
2. 你给的是"重排和改写建议"，不是在写新简历。
3. JD 要求但简历里没有的，必须明确写"简历缺这块，需要你确认是否真的有"，不要替他补。
4. 每条建议都要引用依据（简历里的哪句话 / JD 里的哪句话）。

严格按下面三个分隔符输出，分隔符单独一行：

=== cover.md ===
用表格列出 JD 关键词的覆盖情况，三列：关键词 | 状态（已覆盖/部分覆盖/缺失）| 依据

=== reorder.md ===
简历条目的重排建议：按与这个 JD 的相关度给建议顺序，每条格式：条目名 → 建议位置 → 理由

=== bullets.md ===
挑最相关的 2 到 3 条经历，给改写后的 bullet 建议（每条不超过 25 字）。
只重排已有信息、突出与 JD 呼应的部分；每条后面用括号注明"原文依据：xxx"。

【简历】
"""


def extract_keywords(jd: str, ask_model) -> dict:
    """从 JD 抽关键词。返回 {"技术": [...], "职责": [...], "加分": [...]}"""
    out = ask_model(KEYWORD_PROMPT + jd) or ""
    result = {"技术": [], "职责": [], "加分": []}
    for line in out.splitlines():
        line = line.strip().lstrip("*-· ").strip()
        for key in result:
            if line.startswith(key):
                raw = re.sub(r"^" + key + r"[：:]\s*", "", line)
                items = [x.strip() for x in re.split(r"[、,，/]", raw) if x.strip()]
                result[key] = items[:12]
    return result


def check_coverage(resume: str, keywords: dict) -> list:
    """本地检查覆盖情况（纯字符串比对，不交给模型判断）。"""
    low = resume.lower()
    rows = []
    for cat, words in keywords.items():
        for w in words:
            wl = w.lower().strip()
            if not wl:
                continue
            if wl in low:
                status = "已覆盖"
            elif any(part in low for part in re.split(r"[\s/、]+", wl) if len(part) >= 3):
                status = "部分覆盖"
            else:
                status = "缺失"
            rows.append({"keyword": w, "category": cat, "status": status})
    return rows


def coverage_rate(rows: list) -> float:
    """已覆盖 + 部分覆盖算半分，返回百分比。"""
    if not rows:
        return 0.0
    score = sum(1.0 if r["status"] == "已覆盖" else
                (0.5 if r["status"] == "部分覆盖" else 0.0) for r in rows)
    return round(score / len(rows) * 100, 1)


def split_three(text: str) -> dict:
    """按 === xxx === 切三段。"""
    names = ["cover.md", "reorder.md", "bullets.md"]
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("===") and s.endswith("==="):
            if cur:
                out[cur] = "\n".join(buf).strip()
            inner = s.strip("= ").strip()
            cur = inner if inner in names else None
            buf = []
            continue
        if cur:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf).strip()
    return out


def tailor(resume: str, jd: str, ask_model) -> dict:
    """跑一次定制，返回 {"keywords", "coverage", "rate", "advice"}"""
    keywords = extract_keywords(jd, ask_model)
    coverage = check_coverage(resume, keywords)
    text = ask_model(TAILOR_PROMPT + resume + "\n\n【目标 JD】\n" + jd) or ""
    return {
        "keywords": keywords,
        "coverage": coverage,
        "rate": coverage_rate(coverage),
        "advice": split_three(text),
    }
```

## ===== offeragent/browser_fetch.py（305 行）=====

```python
# -*- coding: utf-8 -*-
"""
browser_fetch · 用真实浏览器抓页面（Chrome DevTools Protocol）
==============================================================
为什么需要它：BOSS 直聘、部分招聘站是强反爬 + 需要登录。
直接 requests 抓只能拿到 9KB 的拦截页。

做法：启动一个**独立的 Edge 窗口**（带调试端口、独立用户目录），
用它当"浏览器替身"：你在这个窗口里登录一次，之后程序就能复用登录态读页面。

  python -m browser_fetch --setup      # 第一次：打开窗口让你登录
  from browser_fetch import fetch_html # 程序里用：打开 URL 拿渲染后的 HTML

不绕过验证码、不做指纹伪装、不做多账号。只是复用你自己已经登录的浏览器。
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests
import websocket  # websocket-client

try:
    import winreg          # 只有 Windows 有；用来读 Edge 的安装路径
except ImportError:        # pragma: no cover
    winreg = None

HERE = Path(__file__).parent
PROFILE_DIR = HERE / "data" / "edge_profile"
DEBUG_PORT = 9333

# 允许用环境变量直接指定浏览器（装在不常见位置时的兜底）
BROWSER_ENV = ("EDGE_PATH", "BROWSER_PATH", "CHROME_PATH")


def edge_candidates() -> list:
    """按可靠性排序列出可能的浏览器路径：环境变量 → 注册表 → 常见安装位置 → PATH。"""
    out = []
    for env in BROWSER_ENV:
        v = os.environ.get(env)
        if v:
            out.append(v)
    out += [
        # Edge 正式版（三处常见位置）
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe",
        # Edge 预览通道
        r"C:\Program Files (x86)\Microsoft\Edge Beta\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge Dev\Application\msedge.exe",
        # Chrome 兜底（同样是 Chromium，CDP 一样能用）
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
        # macOS
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for name in ("msedge", "msedge.exe", "google-chrome", "chromium",
                 "chromium-browser", "chrome"):
        p = shutil.which(name)
        if p:
            out.append(p)
    return [os.path.expandvars(p) for p in out]


def _registry_edge():
    """从注册表读 Edge 安装路径——装在非默认盘时，这里通常也能找到。"""
    if winreg is None:
        return None
    sub = (r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
           r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe")
    for key in sub:
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(hive, key) as k:
                    val = winreg.QueryValue(k, None)
                if val and Path(str(val)).exists():
                    return str(val)
            except OSError:
                continue
    return None


def no_browser_message() -> str:
    checked = "\n".join(f"  · {p}" for p in edge_candidates()[:10])
    return ("没找到 Edge / Chrome。BOSS 直聘是强反爬站，只能借用你本机已经登录的浏览器，"
            "所以这一步必须有一个桌面浏览器。\n已找过这些位置：\n"
            + checked +
            "\n办法：① 装一个 Edge（或 Chrome）后重试；"
            "② 或者设环境变量 EDGE_PATH=浏览器 exe 的完整路径；"
            "③ 只想搜岗位的话，把来源换成「牛客」或「实习僧」——它们不需要浏览器。")


def edge_path() -> str:
    """返回可用的 Chromium 系浏览器路径（Edge 优先，找不到退到 Chrome）。"""
    for env in BROWSER_ENV:                  # 环境变量优先级最高
        v = os.environ.get(env)
        if v:
            try:
                if Path(v).exists():
                    return v
            except Exception:
                continue
    reg = _registry_edge()
    if reg:
        return reg
    for p in edge_candidates():
        try:
            if p and Path(p).exists():
                return p
        except Exception:
            continue
    raise RuntimeError(no_browser_message())


def desktop_available() -> tuple:
    """返回 (能不能抓,BOSS 的理由)。

    云端（Linux 容器）根本没有桌面浏览器，所以这里先给一个说人话的理由，
    而不是让用户对着「没找到 Edge」发呆。
    """
    if sys.platform not in ("win32", "darwin"):
        return False, ("BOSS 抓取只在你自己的电脑上可用（云端没有浏览器，"
                       "抓不了需要登录态的 BOSS）。云端请用「牛客」或「实习僧」。")
    try:
        edge_path()
        return True, ""
    except RuntimeError as e:
        return False, str(e)


def is_running() -> bool:
    try:
        r = requests.get(f"http://127.0.0.1:{DEBUG_PORT}/json/version", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def launch(headless: bool = False) -> bool:
    """启动带调试端口的 Edge（独立 profile，不影响你日常用的 Edge）。"""
    if is_running():
        return True
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    args = [
        edge_path(),
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
    ]
    if headless:
        args.insert(1, "--headless=new")
    subprocess.Popen(args, close_fds=True)
    for _ in range(20):
        time.sleep(0.6)
        if is_running():
            return True
    return False


def _new_tab(url: str) -> str:
    """新建标签页，返回它的 webSocketDebuggerUrl。"""
    r = requests.put(f"http://127.0.0.1:{DEBUG_PORT}/json/new?{url}", timeout=10)
    if r.status_code != 200:
        r = requests.get(f"http://127.0.0.1:{DEBUG_PORT}/json/new?{url}", timeout=10)
    return r.json()["webSocketDebuggerUrl"]


class _CDP:
    """极简 CDP 客户端：发一条命令，等它自己的响应。"""

    def __init__(self, ws_url: str):
        self.ws = websocket.create_connection(ws_url, timeout=30,
                                              suppress_origin=True)
        self._id = 0

    def call(self, method: str, params: dict = None, timeout: float = 30):
        self._id += 1
        msg_id = self._id
        self.ws.send(json.dumps({"id": msg_id, "method": method,
                                 "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            raw = self.ws.recv()
            if not raw:
                continue
            data = json.loads(raw)
            if data.get("id") == msg_id:
                return data.get("result", {})
        raise TimeoutError(f"CDP 调用超时：{method}")

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def js_on_page(url: str, expression: str, wait: float = 5.0,
               await_promise: bool = True, timeout: float = 60):
    """打开页面 → 在页面里跑一段 JS → 把它 return 的值拿回来。

    用途：有些站点（比如牛客）的接口必须带着它自己的 cookie / 请求头才通，
    用 requests 直接调会返回「服务器错误」。让浏览器替我们发这个请求最稳。
    """
    if not launch(headless=True):
        raise RuntimeError("浏览器启动失败：" + no_browser_message()[:200])
    ws_url = _new_tab(url)
    cdp = _CDP(ws_url)
    try:
        cdp.call("Page.enable")
        time.sleep(wait)
        res = cdp.call("Runtime.evaluate", {
            "expression": expression,
            "awaitPromise": bool(await_promise),
            "returnByValue": True,
        }, timeout=timeout)
        if res.get("exceptionDetails"):
            raise RuntimeError("页面脚本报错：" +
                               str(res["exceptionDetails"])[:200])
        return res.get("result", {}).get("value")
    finally:
        cdp.close()


def fetch_html(url: str, wait: float = 4.0, keep_open: bool = False) -> str:
    """打开 URL，等页面渲染完，返回 HTML。"""
    if not launch():
        raise RuntimeError("Edge 启动失败（调试端口没起来）")
    ws_url = _new_tab(url)
    cdp = _CDP(ws_url)
    try:
        cdp.call("Page.enable")
        time.sleep(wait)  # 等前端渲染
        res = cdp.call("Runtime.evaluate", {
            "expression": "document.documentElement.outerHTML",
            "returnByValue": True,
        }, timeout=40)
        return res.get("result", {}).get("value", "")
    finally:
        cdp.close()


def run_js(url: str, expression: str, wait: float = 4.0):
    """打开 URL，在页面上下文里跑一段 JS，返回结果（用于直接调站内接口）。"""
    if not launch():
        raise RuntimeError("Edge 启动失败")
    ws_url = _new_tab(url)
    cdp = _CDP(ws_url)
    try:
        cdp.call("Page.enable")
        time.sleep(wait)
        res = cdp.call("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        }, timeout=60)
        return res.get("result", {}).get("value")
    finally:
        cdp.close()


def screenshot(url: str, out_path: str, wait: float = 6.0,
               width: int = 1440, height: int = 900,
               full_page: bool = True) -> str:
    """打开页面并截图，存成 PNG。返回文件路径。"""
    import base64
    if not launch(headless=True):
        raise RuntimeError("Edge 启动失败")
    ws_url = _new_tab(url)
    cdp = _CDP(ws_url)
    try:
        cdp.call("Page.enable")
        cdp.call("Emulation.setDeviceMetricsOverride", {
            "width": width, "height": height,
            "deviceScaleFactor": 1, "mobile": False,
        })
        time.sleep(wait)
        res = cdp.call("Page.captureScreenshot", {
            "format": "png", "captureBeyondViewport": full_page,
        }, timeout=60)
        data = res.get("data", "")
        Path(out_path).write_bytes(base64.b64decode(data))
        return out_path
    finally:
        cdp.close()


if __name__ == "__main__":
    if "--setup" in sys.argv:
        ok = launch()
        print("调试窗口已启动" if ok else "启动失败")
        print(f"请在这个新开的 Edge 窗口里登录：BOSS直聘 / 实习僧 / 牛客（各登一次）")
        print(f"登录态保存在：{PROFILE_DIR}")
        print(f"注意：这个窗口不要关，程序抓取时要用它。")
    else:
        print(__doc__)
```

## ===== offeragent/jd_fetcher.py（127 行）=====

```python
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
```
