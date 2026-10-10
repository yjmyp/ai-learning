# -*- coding: utf-8 -*-
"""
job_sources · 岗位来源（联网搜岗）
==================================
每个源用最合适的抓法（按"正规程度"从高到低）：

  官方公开接口（免登录，最正规）
    tencent / netease   腾讯招聘 / 网易招聘 —— 公司自己的招聘接口，直接返回 JSON
    greenhouse          AI 公司官方 ATS 接口（Anthropic 等），公司主动开放
    remoteok / arbeitnow / remotive / wwr / HN —— 海外远程岗公开 API 与官方 RSS
    nowcoder            牛客实习中心 —— 页面自己的搜索接口（公开、免登录）
  公开页面渲染（免登录，但要本机浏览器）
    shixiseng           实习僧 —— 前端渲染，用无头浏览器跑 JS 后交大模型抽取
  真实浏览器 + 复用登录态（需本机已登录）
    boss                BOSS直聘 —— 强反爬，走 CDP 连本机已登录的 Edge

统一返回：[{title, company, city, salary, url, extra, source}]

合规边界：只读公开内容、不绕登录、不破签名、低频；海外源本机可能需要走代理。
"""
import json
import os
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

# 来源清单。分两类：
#   NO_LOGIN_SOURCES：公开接口/网页，**不用登录**，云端也能用（默认就搜这些）
#   其余：实习僧要本机浏览器渲染、BOSS 要本机登录态 —— 云端用不了，按需勾选
SOURCES = ["牛客", "腾讯招聘", "网易招聘", "Remotive(远程)",
           "RemoteOK(远程)", "Arbeitnow(海外)", "WeWorkRemotely(远程)",
           "HN Who's Hiring(海外)", "Greenhouse-AI公司(海外)",
           "实习僧", "BOSS直聘"]
# 国内免登录（默认勾选，云端也能用）
NO_LOGIN_SOURCES = ["牛客", "腾讯招聘", "网易招聘"]
# 海外/远程免登录（本机需代理，云端直连即可；默认不勾，想找海外 AI 岗时自己勾上）
OVERSEAS_SOURCES = ["Remotive(远程)", "RemoteOK(远程)", "Arbeitnow(海外)",
                    "WeWorkRemotely(远程)", "HN Who's Hiring(海外)",
                    "Greenhouse-AI公司(海外)"]
NEEDS_BROWSER = {"实习僧", "BOSS直聘"}

# 城市别名：用户会写"南京市 / 江苏南京 / 魔都 / remote"，接口返回的可能是"南京"或"南京/上海"。
# 不做归一的话，"南京市" 永远匹配不上接口里的 "南京" —— 这就是"城市填了但结果对不上"的根因之一。
CITY_ALIASES = {
    "南京市": "南京", "北京市": "北京", "上海市": "上海", "广州市": "广州",
    "深圳市": "深圳", "杭州市": "杭州", "苏州市": "苏州", "成都市": "成都",
    "武汉市": "武汉", "西安市": "西安", "长沙市": "长沙", "重庆市": "重庆",
    "天津市": "天津", "郑州市": "郑州", "合肥市": "合肥", "济南市": "济南",
    "江苏南京": "南京", "广东深圳": "深圳", "广东广州": "广州",
    "魔都": "上海", "帝都": "北京", "羊城": "广州", "鹏城": "深圳",
    "remote": "远程", "Remote": "远程", "远程办公": "远程", "线上": "远程",
    "anywhere": "远程",
}

# 常见城市（给界面做多选，不用用户手打还是拼错）
COMMON_CITIES = ["南京", "上海", "杭州", "北京", "深圳", "广州", "苏州",
                 "成都", "武汉", "西安", "合肥", "无锡", "远程"]


def norm_city(s: str) -> str:
    """城市名归一：去空格、去"市"、把别名映射到标准名。"""
    t = (s or "").strip().replace(" ", "")
    if not t:
        return ""
    if t in CITY_ALIASES:
        return CITY_ALIASES[t]
    low = t.lower()
    if low in ("remote", "anywhere", "remote job"):
        return "远程"
    for k, v in CITY_ALIASES.items():
        if k and k in t:
            return v
    return t[:-1] if t.endswith("市") and len(t) > 2 else t


def want_cities(city: str) -> list:
    """把用户输入的多个城市归一成列表（去重保序）。"""
    out = []
    for c in split_terms(city):
        n = norm_city(c)
        if n and n not in out:
            out.append(n)
    return out


def city_hit(job_city: str, wants: list) -> bool:
    """岗位城市是否命中用户想要的城市（支持"南京/上海"这种多城市字段、支持远程）。"""
    if not wants:
        return True
    raw = job_city or ""
    parts = [norm_city(p) for p in re.split(r"[/,，、;；\s·]+", raw) if p.strip()]
    for w in wants:
        if w == "远程":
            low = raw.lower()
            if any(k in raw for k in ["远程", "居家"]) or any(
                    k in low for k in ["remote", "anywhere", "worldwide", "global"]):
                return True
            continue
        if w and (w in parts or w in norm_city(raw) or any(w in p for p in parts)):
            return True
    return False


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
# 3.5) 公开接口来源（免登录，云端也能用）：腾讯 / 网易 / Remotive
# ============================================================
TENCENT_API = "https://careers.tencent.com/tencentcareer/api/post/Query"
NETEASE_API = "https://hr.163.com/api/hr163/position/queryPage"
REMOTIVE_API = "https://remotive.com/api/remote-jobs"


def _pack(title, company, city, salary, url, source, extra="", jd="", hits=0, ch=True):
    return {"title": (title or "").strip(), "company": (company or "").strip(),
            "city": (city or "").strip(), "salary": (salary or "").strip(),
            "url": url or "", "source": source, "extra": extra, "jd": jd or "",
            "match_hits": hits, "city_hit": ch}


def _kw_hits(blob: str, kws: list) -> int:
    if not kws:
        return 0
    low = (blob or "").lower()
    return sum(1 for k in kws if k.lower() in low)


# ---------- 海外源的网络细节：直连失败自动走本机代理 ----------
# 本机（国内网络）直连 remoteok / greenhouse / HN 这些会被重置；
# 云端（Streamlit Cloud 在美国）直连正常。所以策略是：先直连，失败再试代理，
# 代理端口自动探测，也可以用 JOBS_PROXY 显式指定。
_PROXY_CACHE = "unset"


def _local_proxy():
    global _PROXY_CACHE
    if _PROXY_CACHE != "unset":
        return _PROXY_CACHE
    import socket
    env = os.environ.get("JOBS_PROXY", "").strip()
    if env:
        _PROXY_CACHE = {"http": env, "https": env}
        return _PROXY_CACHE
    for port in (7897, 7890, 7891, 10809, 10808):
        s = socket.socket()
        s.settimeout(0.3)
        try:
            s.connect(("127.0.0.1", port))
            _PROXY_CACHE = {"http": "http://127.0.0.1:%d" % port,
                            "https": "http://127.0.0.1:%d" % port}
            return _PROXY_CACHE
        except Exception:
            continue
        finally:
            s.close()
    _PROXY_CACHE = None
    return None


def fetch_json_or_text(url: str, method: str = "GET", timeout: int = 30, **kwargs):
    """先直连、失败再走本机代理；返回 requests.Response。海外源统一走这里。"""
    last = None
    for proxies in (None, _local_proxy()):
        try:
            fn = requests.get if method.upper() == "GET" else requests.post
            r = fn(url, headers=kwargs.pop("headers", H), timeout=timeout,
                   proxies=proxies, **kwargs)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
        except Exception as e:
            last = type(e).__name__
    raise RuntimeError(f"取不到 {url}：{last}")


def search_tencent(keyword: str = "", city: str = "", diag: dict = None,
                   pages: int = 2) -> list:
    """腾讯招聘公开接口（免登录）。城市在客户端过滤——接口没有可用的城市参数。"""
    kws, wants = split_terms(keyword), want_cities(city)
    kw = kws[0] if kws else ""
    jobs, raw_n = [], 0
    for p in range(1, max(1, pages) + 1):
        try:
            d = requests.get(TENCENT_API, headers=H, timeout=25, params={
                "keyword": kw, "pageIndex": p, "pageSize": 20, "language": "zh-cn"}).json()
            posts = ((d.get("Data") or {}).get("Posts") or [])
        except Exception as e:
            if diag is not None:
                diag["api_error"] = f"第{p}页：{type(e).__name__}"
            break
        if not posts:
            break
        for j in posts:
            raw_n += 1
            title, c = j.get("RecruitPostName") or "", j.get("LocationName") or ""
            duty, req = str(j.get("Responsibility") or ""), str(j.get("Requirement") or "")
            jobs.append(_pack(
                title, j.get("ComName") or "", c,
                j.get("Salary") or "",
                j.get("PostURL") or j.get("Url") or "",
                "腾讯招聘",
                extra=" | ".join(x for x in [j.get("BGName"), j.get("CategoryName"),
                                             j.get("RequireWorkYearsName")] if x),
                jd=(duty + "\n\n任职要求：\n" + req).strip(),
                hits=_kw_hits(f"{title} {duty} {req}", kws),
                ch=city_hit(c, wants)))
        if len(posts) < 20:
            break
    jobs.sort(key=lambda x: (-x["match_hits"], not x["city_hit"]))
    if diag is not None:
        diag.update({"raw": raw_n, "kept": len(jobs), "cities": wants, "source_api": "公开接口"})
    return jobs


def search_netease(keyword: str = "", city: str = "", diag: dict = None,
                   pages: int = 2) -> list:
    """网易招聘公开接口（免登录）。JD 原文直接带在 requirement/description 里。"""
    kws, wants = split_terms(keyword), want_cities(city)
    kw = kws[0] if kws else ""
    jobs, raw_n = [], 0
    for p in range(1, max(1, pages) + 1):
        try:
            d = requests.post(NETEASE_API, headers={**H, "Content-Type": "application/json"},
                              timeout=25, json={"currentPage": p, "pageSize": 20, "keyword": kw}).json()
            lst = ((d.get("data") or {}).get("list") or [])
        except Exception as e:
            if diag is not None:
                diag["api_error"] = f"第{p}页：{type(e).__name__}"
            break
        if not lst:
            break
        for j in lst:
            raw_n += 1
            title = j.get("name") or ""
            places = j.get("workPlaceNameList") or j.get("workPlaceList") or []
            c = "/".join(str(x) for x in places) if isinstance(places, list) else str(places or "")
            req, desc = str(j.get("requirement") or ""), str(j.get("description") or "")
            jobs.append(_pack(
                title, j.get("firstDepName") or "网易", c, j.get("salary") or "",
                j.get("beeUrl") or f"https://hr.163.com/job-detail.html?id={j.get('id', '')}",
                "网易招聘",
                extra=" | ".join(x for x in [j.get("firstPostTypeName"), j.get("reqEducationName"),
                                             j.get("reqWorkYearsName")] if x),
                jd=(desc + "\n\n任职要求：\n" + req).strip(),
                hits=_kw_hits(f"{title} {desc} {req}", kws),
                ch=city_hit(c, wants)))
        if len(lst) < 20:
            break
    jobs.sort(key=lambda x: (-x["match_hits"], not x["city_hit"]))
    if diag is not None:
        diag.update({"raw": raw_n, "kept": len(jobs), "cities": wants, "source_api": "公开接口"})
    return jobs


def search_remotive(keyword: str = "", city: str = "", diag: dict = None,
                    limit: int = 20) -> list:
    """Remotive 远程岗（英文，免登录）。城市一律视作"远程"，用来补海外远程机会。"""
    kws, wants = split_terms(keyword), want_cities(city)
    kw = kws[0] if kws else ""
    try:
        d = requests.get(REMOTIVE_API, headers=H, timeout=25,
                         params={"search": kw, "limit": limit}).json()
        lst = d.get("jobs") or []
    except Exception as e:
        if diag is not None:
            diag["api_error"] = type(e).__name__
        return []
    jobs = []
    for j in lst[:limit]:
        title = j.get("title") or ""
        loc = j.get("candidate_required_location") or "Remote"
        c = "远程" if any(k in loc.lower() for k in ["worldwide", "anywhere", "remote"]) else loc
        desc = html_to_text(str(j.get("description") or ""))
        jobs.append(_pack(
            title, j.get("company_name") or "", c, j.get("salary") or "",
            j.get("url") or "", "Remotive(远程)",
            extra=" | ".join(x for x in [j.get("category"), j.get("job_type")] if x),
            jd=desc[:4000],
            hits=_kw_hits(f"{title} {desc}", kws),
            ch=city_hit(c, wants)))
    jobs.sort(key=lambda x: (-x["match_hits"], not x["city_hit"]))
    if diag is not None:
        diag.update({"raw": len(lst), "kept": len(jobs), "cities": wants,
                     "source_api": "公开接口", "note": "英文远程岗，需英文简历"})
    return jobs


# ============================================================
# 3.6) 海外 / 官方 ATS 来源（免登录）：RemoteOK / Arbeitnow / WeWorkRemotely / HN / Greenhouse
#      本机直连可能被重置 → 统一走 fetch_json_or_text（直连失败自动代理）；云端直连即可
# ============================================================
REMOTEOK_API = "https://remoteok.com/api"
ARBEITNOW_API = "https://www.arbeitnow.com/api/job-board-api"
WWR_RSS = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
HN_ALGOLIA = "https://hn.algolia.com/api/v1"
GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/%s/jobs"

# Greenhouse 是很多 AI 公司的官方招聘系统（公开接口，完全合规）。
# slug 就是公司名（boards.greenhouse.io/<slug>）；换公司只改这一行。
ATS_COMPANIES = {
    "anthropic": "Anthropic",
    "scaleai": "Scale AI",
    "cohere": "Cohere",
    "huggingface": "Hugging Face",
    "mistral": "Mistral AI",
    "together": "Together AI",
    "runwayml": "Runway",
}


def search_remoteok(keyword: str = "", city: str = "", diag: dict = None,
                    limit: int = 40) -> list:
    """RemoteOK 公开 JSON（免登录，全是远程岗）。"""
    kws, wants = split_terms(keyword), want_cities(city)
    try:
        data = fetch_json_or_text(REMOTEOK_API).json()
    except Exception as e:
        if diag is not None:
            diag["api_error"] = str(e)[:80]
        return []
    raw = [x for x in data if isinstance(x, dict) and x.get("position")]
    jobs = []
    for j in raw[:400]:
        title = j.get("position") or ""
        blob = f"{title} {' '.join(j.get('tags') or [])} {j.get('description') or ''}"
        if kws and not any(k.lower() in blob.lower() for k in kws):
            continue
        jobs.append(_pack(title, j.get("company") or "", "远程", j.get("salary") or "",
                          j.get("url") or j.get("apply_url") or "", "RemoteOK(远程)",
                          extra=" | ".join(j.get("tags") or [])[:80],
                          jd=html_to_text(str(j.get("description") or ""))[:4000],
                          hits=_kw_hits(blob, kws), ch=city_hit("远程", wants)))
        if len(jobs) >= limit:
            break
    if diag is not None:
        diag.update({"raw": len(raw), "kept": len(jobs), "cities": wants,
                     "source_api": "公开 JSON", "note": "全远程岗，英文"})
    return jobs


def search_arbeitnow(keyword: str = "", city: str = "", diag: dict = None,
                     limit: int = 40) -> list:
    """Arbeitnow 公开 job board API（免登录，欧洲为主）。"""
    kws, wants = split_terms(keyword), want_cities(city)
    try:
        data = fetch_json_or_text(ARBEITNOW_API).json()
    except Exception as e:
        if diag is not None:
            diag["api_error"] = str(e)[:80]
        return []
    raw = data.get("data") or []
    jobs = []
    for j in raw:
        title = j.get("title") or ""
        loc = j.get("location") or ""
        tags = " ".join(j.get("tags") or [])
        blob = f"{title} {tags} {j.get('description') or ''}"
        if kws and not any(k.lower() in blob.lower() for k in kws):
            continue
        jobs.append(_pack(title, j.get("company_name") or "", loc, "",
                          j.get("url") or "", "Arbeitnow(海外)",
                          extra=tags[:80],
                          jd=html_to_text(str(j.get("description") or ""))[:4000],
                          hits=_kw_hits(blob, kws), ch=city_hit(loc, wants)))
        if len(jobs) >= limit:
            break
    if diag is not None:
        diag.update({"raw": len(raw), "kept": len(jobs), "cities": wants,
                     "source_api": "公开 JSON", "note": "欧洲/海外岗，英文"})
    return jobs


def search_wwr(keyword: str = "", city: str = "", diag: dict = None,
               limit: int = 40) -> list:
    """WeWorkRemotely 官方 RSS（免登录，远程编程岗）。"""
    import xml.etree.ElementTree as ET
    kws, wants = split_terms(keyword), want_cities(city)
    try:
        xml = fetch_json_or_text(WWR_RSS).text
        root = ET.fromstring(xml)
    except Exception as e:
        if diag is not None:
            diag["api_error"] = f"{type(e).__name__}:{str(e)[:60]}"
        return []
    items = root.findall(".//item")
    jobs = []
    for it in items:
        def txt(tag):
            el = it.find(tag)
            return (el.text or "").strip() if el is not None and el.text else ""
        title_raw = txt("title")
        desc = html_to_text(txt("description"))
        blob = f"{title_raw} {desc}"
        if kws and not any(k.lower() in blob.lower() for k in kws):
            continue
        # WWR 的标题通常是 "公司: 岗位"
        company, title = ("", title_raw)
        if ":" in title_raw:
            company, title = title_raw.split(":", 1)[0].strip(), title_raw.split(":", 1)[1].strip()
        jobs.append(_pack(title, company, "远程", "", txt("link"), "WeWorkRemotely(远程)",
                          extra="RSS", jd=desc[:4000], hits=_kw_hits(blob, kws),
                          ch=city_hit("远程", wants)))
        if len(jobs) >= limit:
            break
    if diag is not None:
        diag.update({"raw": len(items), "kept": len(jobs), "cities": wants,
                     "source_api": "官方 RSS", "note": "远程编程岗，英文"})
    return jobs


def search_hn_hiring(keyword: str = "", city: str = "", diag: dict = None,
                     limit: int = 30) -> list:
    """Hacker News「Who is hiring」招聘贴（公开 Algolia API）。

    为什么值得加：每月一贴，里面大量 AI/LLM 岗位，且很多是远程、不看学历看作品——
    和我这种"自学 + 项目驱动"的候选人匹配度高。每条评论就是一个岗位。
    """
    kws, wants = split_terms(keyword), want_cities(city)
    try:
        s = fetch_json_or_text(HN_ALGOLIA + "/search", params={
            "query": "Ask HN: Who is hiring", "tags": "story", "hitsPerPage": 5}).json()
        hits = [h for h in (s.get("hits") or []) if "who is hiring" in (h.get("title") or "").lower()]
        if not hits:
            raise RuntimeError("没找到 Who is hiring 贴")
        story_id = hits[0]["objectID"]
        c = fetch_json_or_text(HN_ALGOLIA + "/search", params={
            "tags": "comment,story_%s" % story_id, "hitsPerPage": 200}).json()
        comments = c.get("hits") or []
    except Exception as e:
        if diag is not None:
            diag["api_error"] = str(e)[:80]
        return []
    jobs = []
    for h in comments:
        # 只要**顶层评论**：Who is hiring 贴里每条顶层评论 = 一个招聘方的帖子；
        # 嵌套回复是求职者提问，混进来就是噪音（第一版没过滤，抓到过"这说不通啊"这种回复）。
        if str(h.get("parent_id")) != str(story_id):
            continue
        text = html_to_text(str(h.get("comment_text") or ""))
        if not text or len(text) < 40:
            continue
        if kws and not any(k.lower() in text.lower() for k in kws):
            continue
        first = re.split(r"[|\n]", text)[0].strip()
        jobs.append(_pack(first[:60] or "HN 招聘贴", "见正文", "远程/海外", "",
                          f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                          "HN Who's Hiring(海外)", extra=HN_STORY_TITLE,
                          jd=text[:4000], hits=_kw_hits(text, kws),
                          ch=city_hit("远程", wants) if wants else True))
        if len(jobs) >= limit:
            break
    if diag is not None:
        diag.update({"raw": len(comments), "kept": len(jobs), "cities": wants,
                     "source_api": "公开 API", "note": "每月招聘贴，AI 岗密集，英文"})
    return jobs


HN_STORY_TITLE = "Hacker News: Who is hiring（每月招聘贴）"


def search_greenhouse(keyword: str = "", city: str = "", diag: dict = None,
                      limit: int = 40) -> list:
    """官方 ATS 接口（Greenhouse）：直接读取公司挂在招聘系统上的**全部**职位。

    这是最正规的一类——公司自己开放的招聘 API，不是"爬"。名单见 ATS_COMPANIES，
    想加公司就往那里面加 slug（boards.greenhouse.io/<slug>）。
    """
    kws, wants = split_terms(keyword), want_cities(city)
    jobs, raw_n, failed = [], 0, []
    for slug, name in ATS_COMPANIES.items():
        try:
            d = fetch_json_or_text(GREENHOUSE_API % slug).json()
            lst = d.get("jobs") or []
        except Exception as e:
            failed.append(f"{name}:{type(e).__name__}")
            continue
        for j in lst:
            raw_n += 1
            title = j.get("title") or ""
            loc = (j.get("location") or {}).get("name") or ""
            depts = " ".join(d.get("name", "") for d in (j.get("departments") or []) if isinstance(d, dict))
            offices = " ".join(o.get("name", "") for o in (j.get("offices") or []) if isinstance(o, dict))
            meta = j.get("metadata") or []
            meta_txt = " ".join(str(m.get("value")) for m in meta if isinstance(m, dict))
            # 英文岗的标题未必含关键词（"Software Engineer, Safeguards" 也是 AI 岗），
            # 所以标题 + 部门 + 办公地 + 元数据一起匹配
            blob = f"{title} {depts} {offices} {meta_txt}"
            if kws and not any(k.lower() in blob.lower() for k in kws):
                continue
            jobs.append(_pack(title, name, loc, "",
                              j.get("absolute_url") or "",
                              "Greenhouse-AI公司(海外)",
                              extra=" | ".join(x for x in [depts, offices, meta_txt] if x)[:80],
                              jd="（详情见职位链接；ATS 接口不返回 JD 正文）",
                              hits=_kw_hits(title, kws), ch=city_hit(loc, wants)))
            if len(jobs) >= limit:
                break
        if len(jobs) >= limit:
            break
    if diag is not None:
        diag.update({"raw": raw_n, "kept": len(jobs), "cities": wants,
                     "source_api": "官方 ATS 接口",
                     "note": "AI 公司官网职位（%d 家）" % len(ATS_COMPANIES),
                     "failed": failed[:4]})
    return jobs


def search_custom_feed(url: str, keyword: str = "", city: str = "", diag: dict = None,
                       limit: int = 40) -> list:
    """自定义来源：填任意公开 RSS / Atom / JSON 列表地址，程序自己抽岗位。

    为什么做这个：招聘渠道无穷多（高校就业网、公司博客、社区汇总贴、公众号导出…），
    与其等程序内置，不如给一个"你填地址、我来抽"的通用口子。只读公开内容，不绕登录。
    """
    import xml.etree.ElementTree as ET
    kws, wants = split_terms(keyword), want_cities(city)
    try:
        r = fetch_json_or_text(url)
        body = r.text
    except Exception as e:
        if diag is not None:
            diag["api_error"] = str(e)[:100]
        return []
    rows = []
    try:                                    # JSON 形态
        data = r.json()
        items = data if isinstance(data, list) else (data.get("jobs") or data.get("data") or data.get("items") or [])
        for it in items or []:
            if not isinstance(it, dict):
                continue
            rows.append({
                "title": it.get("title") or it.get("position") or it.get("name") or "",
                "company": it.get("company") or it.get("company_name") or "",
                "city": it.get("location") or it.get("city") or "",
                "url": it.get("url") or it.get("link") or it.get("absolute_url") or "",
                "jd": html_to_text(str(it.get("description") or ""))[:3000],
            })
    except Exception:                       # RSS/Atom 形态
        try:
            root = ET.fromstring(body)
            for it in root.findall(".//item") + root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                def t(tag, atom=False):
                    el = it.find(("{http://www.w3.org/2005/Atom}" + tag) if atom else tag)
                    return (el.text or "").strip() if el is not None and el.text else ""
                link = t("link") or (it.find("{http://www.w3.org/2005/Atom}link").attrib.get("href")
                                     if it.find("{http://www.w3.org/2005/Atom}link") is not None else "")
                rows.append({"title": t("title"), "company": "", "city": "",
                             "url": link, "jd": html_to_text(t("description"))[:3000]})
        except Exception as e:
            if diag is not None:
                diag["api_error"] = "解析失败：" + type(e).__name__
            return []
    jobs = []
    for row in rows:
        blob = f"{row['title']} {row['jd']} {row['city']}"
        if kws and not any(k.lower() in blob.lower() for k in kws):
            continue
        jobs.append(_pack(row["title"], row["company"], row["city"], "", row["url"],
                          "自定义来源", extra=url[:60], jd=row["jd"],
                          hits=_kw_hits(blob, kws), ch=city_hit(row["city"], wants)))
        if len(jobs) >= limit:
            break
    if diag is not None:
        diag.update({"raw": len(rows), "kept": len(jobs), "cities": wants,
                     "source_api": "自定义 URL", "note": url[:70]})
    return jobs


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
    if source == "腾讯招聘":
        return search_tencent(keyword, city, diag=diag)
    if source == "网易招聘":
        return search_netease(keyword, city, diag=diag)
    if source == "Remotive(远程)":
        return search_remotive(keyword, city, diag=diag)
    if source == "RemoteOK(远程)":
        return search_remoteok(keyword, city, diag=diag)
    if source == "Arbeitnow(海外)":
        return search_arbeitnow(keyword, city, diag=diag)
    if source == "WeWorkRemotely(远程)":
        return search_wwr(keyword, city, diag=diag)
    if source == "HN Who's Hiring(海外)":
        return search_hn_hiring(keyword, city, diag=diag)
    if source == "Greenhouse-AI公司(海外)":
        return search_greenhouse(keyword, city, diag=diag)
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
               sources: list = None, strict_city: bool = True,
               custom_url: str = "") -> dict:
    """一次搜索，把多个平台的结果合并去重。

    返回 {
      "jobs": [...],                 # 合并去重后的岗位，牛客优先、其余按平台顺序
      "by_source": {"牛客": 5, ...},  # 每个平台拿到几条
      "errors": {"BOSS": "需要先登录"}, # 哪个平台失败、为什么
      "diag": {...},                 # 抓取诊断：原始条数 / 页面长度 / 关键词拆分
      "cities": {"牛客": [("深圳",7),...]},  # 每个平台原始结果的城市分布（解释"为什么这条不是南京"）
      "relaxed": {"牛客": 12},        # 严格过滤后被丢掉多少条（0 条时不丢，见下）
    }

    城市处理（这是用户反馈"填了城市但结果对不上"的关键修复）：
      · 归一化：南京市/江苏南京/魔都/remote → 南京/上海/远程；
      · strict_city=True 时**真的过滤掉**城市不匹配的岗位；
      · 但如果某个平台过滤后一条不剩，则**保留该平台原始结果**并记进 relaxed，
        否则用户会遇到"填了城市 → 一条都没有"，那比看到不匹配的结果更糟。
    """
    wants = want_cities(city)
    if sources:
        targets = list(sources)
    else:   # 默认只用免登录来源（云端可用）；实习僧在本机有浏览器时自动加上
        targets = list(NO_LOGIN_SOURCES)
        try:
            import browser_fetch as bf
            if bf.desktop_available()[0]:
                targets.append("实习僧")
        except Exception:
            pass
    merged, seen, by_source, errors, diag, city_stats, relaxed = [], set(), {}, {}, {}, {}, {}
    raw_by_src, city_miss = {}, {}

    # BOSS 需要本机浏览器；云端直接跳过，并把原因写清楚
    try:
        import browser_fetch as bf
        _ok, _why = bf.desktop_available()
    except Exception as e:
        _ok, _why = False, str(e)[:120]
    if not _ok and "BOSS直聘" in targets:
        targets = [t for t in targets if t != "BOSS直聘"]
        errors["BOSS直聘"] = _why

    # 把"自定义来源"当成一个额外来源一起处理（同一套城市过滤/去重逻辑）
    tasks = [(s, "") for s in targets]
    if custom_url.strip():
        tasks.append(("自定义来源", custom_url.strip()))

    for src, _custom_url in tasks:
        d = {}
        try:
            rows = (search_custom_feed(_custom_url, keyword, city, diag=d)
                    if _custom_url else search(src, keyword, city, ask_model, diag=d))
            raw_by_src[src] = list(rows)
            # 城市分布：让用户看到"这个平台捞回来的都是哪些城市"
            counter = {}
            for j in rows:
                c = (j.get("city") or "未标注").strip() or "未标注"
                counter[c] = counter.get(c, 0) + 1
            city_stats[src] = sorted(counter.items(), key=lambda x: -x[1])[:6]
            # 严格城市过滤：不匹配就**整条丢掉**（宁缺毋滥，用户要的是"城市对得上"）
            if strict_city and wants:
                keep = [j for j in rows if city_hit(j.get("city"), wants)]
                relaxed[src] = len(rows) - len(keep)
                if not keep and rows:
                    city_miss[src] = len(rows)      # 这个平台这次没有目标城市的岗位
                rows = keep
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
    if wants:
        merged.sort(key=lambda j: 0 if city_hit(j.get("city"), wants) else 1)
    # 全空才放宽：所有平台都没有目标城市的岗位时，把原始结果并回来并标注，
    # 否则用户会看到"填了城市一条都没有"，比看到不匹配更糟。
    relaxed_all = False
    if strict_city and wants and not merged:
        for src, _u in tasks:
            for j in raw_by_src.get(src, []):
                key = re.sub(r"\s+", "", f"{(j.get('title') or '').lower()}|"
                                          f"{(j.get('company') or '').lower()}")
                if key in seen:
                    continue
                seen.add(key)
                merged.append(j)
        relaxed_all = True
    diag["keywords"] = split_terms(keyword)
    diag["cities"] = wants
    return {"jobs": merged, "by_source": by_source, "errors": errors,
            "diag": diag, "cities": city_stats, "relaxed": relaxed,
            "city_miss": city_miss, "relaxed_all": relaxed_all,
            "wants": wants, "strict_city": strict_city}
