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
    "全国": "100010000",
    # 直辖市
    "北京": "101010100", "上海": "101020100", "天津": "101030100", "重庆": "101040100",
    # 华东
    "南京": "101190100", "无锡": "101190200", "苏州": "101190400",
    "杭州": "101210100", "宁波": "101210400", "温州": "101210700",
    "合肥": "101220100", "福州": "101230100", "厦门": "101230200",
    "南昌": "101240100", "济南": "101120100", "青岛": "101120200",
    # 华北 / 东北
    "石家庄": "101090100", "太原": "101100100", "呼和浩特": "101080100",
    "哈尔滨": "101050100", "长春": "101060100", "沈阳": "101070100",
    # 华中 / 华南
    "郑州": "101180100", "武汉": "101200100", "长沙": "101250100",
    "广州": "101280100", "深圳": "101280600", "佛山": "101280800",
    "东莞": "101281600", "珠海": "101280700", "南宁": "101300100",
    "海口": "101310100",
    # 西北 / 西南
    "西安": "101110100", "兰州": "101160100", "银川": "101170100",
    "西宁": "101150100", "乌鲁木齐": "101130100",
    "成都": "101270100", "贵阳": "101260100", "昆明": "101290100",
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
def search_boss(keyword: str, city: str = "", ask_model=None,
                diag: dict = None) -> list:
    """走 browser_fetch（Edge 调试窗口）。需要先跑一次 setup 登录 BOSS。"""
    if not ask_model:
        raise RuntimeError("这个源需要 ask_model 才能解析")
    import browser_fetch as bf
    ok, why = bf.desktop_available()
    if not ok:
        raise RuntimeError(why)
    kw_first = split_terms(keyword)[0] if split_terms(keyword) else ""
    city_first = split_terms(city)[0] if split_terms(city) else "全国"
    city_code = BOSS_CITY_CODES.get(city_first)
    if not city_code:
        # 城市表里没有：不偷换成别的城市，回退「全国」并在诊断里说清楚
        city_code = "100010000"
        if diag is not None:
            diag["boss_city_fallback"] = (
                f"BOSS 城市表里没有「{city_first}」，已按「全国」检索；"
                "可在支持的城市里重选（北京/上海/广州/深圳/杭州/南京/苏州/成都/"
                "武汉/西安/长沙/重庆/天津/郑州/青岛/厦门/合肥/济南等 40+ 城市）。")
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
        return search_shixiseng(keyword, city or "", ask_model, diag=diag)
    if source == "BOSS直聘":
        return search_boss(keyword, city or "", ask_model, diag=diag)
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


def search_all(keyword: str, city: str = "", ask_model=None,
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
