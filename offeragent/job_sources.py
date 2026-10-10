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
import hashlib
import threading
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
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
# 能并发抓的来源 = 全部来源 - 要浏览器的两个。判据是"这条链路会不会碰大模型/浏览器"：
# 实习僧、BOSS 要走无头浏览器 + ask_model 抽岗位，而界面传进来的 ask_model 是
# Streamlit 里的 ask_chat（读写 st.session_state，**不是线程安全的**）→ 只能主线程串行。
# 其余 9 个来源都是纯 HTTP（requests + 本地解析），并发跑没有共享状态。
PARALLEL_SAFE_SOURCES = set(SOURCES) - NEEDS_BROWSER

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
                    diag: dict = None, max_items: int = 300) -> list:
    """牛客实习中心。

    注意：以前是「关键词/城市不命中就直接丢掉」，结果是岗位数少得离谱
    （标题里没写「AI」的算法岗、写成「江苏南京」的城市都会被误杀）。
    现在默认**只排序不丢弃**：命中的排前面，其余照常返回，由你自己在列表里勾选。
    strict=True 才回到硬过滤。

    还有一层：首页只带 20 条（页面里的 totalCount 其实是 145+）。所以这里先调
    牛客自己的搜索接口**翻页取几页**（20 → 60~100 条），接口不通才退回首页解析。
    """
    # 翻页深度按"想要多少条"算（每页 20）：实测同一关键词 api_total 能到 302，
    # 以前写死 5 页 = 100 条就收工，是"岗位太少"的原因之一。
    pages = max(NOWCODER_PAGES, pages_for(max_items, 20, cap=15))
    items, api_diag = _nowcoder_api(keyword, pages)
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
            with _NetSlot():
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
      var out = [], total = 0, done = 0, t0 = Date.now();
      for (var p = 1; p <= %d; p++) {
        if (Date.now() - t0 > 60000) { break; }
        var body = 'requestFrom=1&page=' + p +
                   '&pageSize=20&recruitType=2&pageSource=5001%s';
        var ctl = new AbortController();
        var to = setTimeout(function(){ ctl.abort(); }, 12000);
        try {
          var r = await fetch('%s', {method: 'POST', credentials: 'include',
            headers: {'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'},
            body: body, signal: ctl.signal});
          var d = await r.json();
          clearTimeout(to);
          var dd = (d && d.data) || {};
          if (dd.totalCount) { total = dd.totalCount; }
          if (dd.datas && dd.datas.length) { out = out.concat(dd.datas); done = p; }
          else { break; }
          if (dd.totalPage && p >= dd.totalPage) { break; }
        } catch (e) { clearTimeout(to); break; }
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
    """直连接口翻页（3 路并发 + 每站 0.25s 节流）。缺 Referer/Origin 会被判成爬虫。

    两个细节都是踩出来的：
      · **单页失败不要整体放弃**：实测 302 条 / 16 页，中间某一页会偶发
        ConnectionError；以前直接 break，结果只拿到 80 条（"岗位太少"的元凶之一）。
        现在每页重试 1 次，仍失败就跳过这页继续翻后面的。
      · 返回条数少于 pageSize 说明到底了，提前结束（并发时由 stop_when 判定）。
    """
    per_page = 20

    def fetch(p):
        return _nowcoder_fetch_page(p, q, per_page)

    def stop_when(r):
        status, datas, _dd = r or ("skip", None, {})
        if status == "stop":
            return True
        return status == "ok" and len(datas or []) < per_page

    rows = parallel_pages(fetch, pages, key="nowcoder", stop_when=stop_when)
    items, total, done, err, skipped = [], 0, 0, "", []
    for p, r in rows:
        status, datas, extra = r or ("skip", None, {})
        if status != "ok":
            if status == "skip":
                skipped.append(p)         # 这页废了，但不影响别的页
            if not err:
                err = str(extra or "")
            continue
        if not datas:
            continue
        total = (extra or {}).get("totalCount") or total
        items += datas
        done = p
    if items:
        diag = {"api_total": total, "api_pages": done, "api_via": "requests"}
        if err:
            diag["api_note"] = err
        if skipped:
            diag["api_skipped_pages"] = skipped
        return items, diag
    return [], {"api_error": err or "直连接口没返回数据"}


def _nowcoder_fetch_page(p: int, q: str, per_page: int = 20):
    """抓牛客第 p 页，返回 (状态, 数据, 附加信息)：

      ok   → 数据 = 这一页的列表（空列表 = 到底了）
      skip → 网络失败（重试 1 次仍失败）：只废这一页，别的页继续
      stop → 接口明确报错（code != 0）：停止翻页
    """
    url = f"https://www.nowcoder.com{NOWCODER_API}?_={int(time.time() * 1000)}"
    body = (f"requestFrom=1&page={p}&pageSize={per_page}&recruitType=2"
            f"&pageSource=5001" + q)
    err = ""
    for _attempt in range(2):             # 每页最多试 2 次
        try:
            # 超时 12 秒：实测正常页 0.5~0.8 秒就回来，而站点偶发"整页不响应"——
            # 那种卡顿会一直挂到超时为止（曾观测到 20.87s = 正好撞上原来的 20s 超时，
            # 两次尝试都挂就是 40.13s）。12 秒足够宽松，又能把最坏情况从 41 秒压到 25 秒。
            with _NetSlot():        # 占一个全局在飞名额
                r = requests.post(url, data=body, headers=NOWCODER_HEADERS, timeout=12)
            d = r.json()
        except Exception as e:
            err = str(e)[:120]
            time.sleep(0.6)
            continue
        if d.get("code") != 0:
            return "stop", None, str(d.get("msg") or "")[:60]
        dd = d.get("data") if isinstance(d.get("data"), dict) else {}
        return "ok", (dd.get("datas") or []), dd
    return "skip", None, err


def _nowcoder_company(rec: dict) -> str:
    """从牛客记录里挖出**公司名**。

    踩坑：牛客搜索接口的记录里**没有**顶层 companyName（那是首页版的 schema），
    公司名藏在 `recommendInternCompany.companyName`（简称）或
    `user.identity[].companyName`（全称）里。之前直接取 companyName 拿不到，
    就退化成 `company#304612`——后果不只是显示难看：合并去重是按「岗位名+公司」
    做的，公司名全空 → 同名岗位被当重复丢掉。实测搜「AI」280 条里 192 条都叫
    「Ai应用开发」，最后被去重成 75 条，这就是"岗位太少"的一个真原因。
    """
    comp = rec.get("companyName")
    if not comp:
        ric = rec.get("recommendInternCompany")
        if isinstance(ric, dict):
            comp = ric.get("companyShortName") or ric.get("companyName")
    if not comp:
        u = rec.get("user")
        idents = (u.get("identity") or []) if isinstance(u, dict) else []
        for ident in idents:
            if isinstance(ident, dict) and ident.get("companyName"):
                comp = ident["companyName"]
                break
    comp = str(comp or "").strip()
    if comp:
        return comp
    cid = rec.get("companyId")
    return f"牛客公司#{cid}" if cid else ""


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
        company = _nowcoder_company(rec)
        if company:
            extra_bits.append(company)
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
            "company": company,
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
            with _NetSlot():
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
            with _NetSlot():
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


def _dbg(msg: str):
    """`JOBS_DEBUG=1` 时打一行调试日志（排查"搜岗卡住"用）。

    为什么要它：Streamlit 里脚本出错只会给前端一个红框，**服务端日志默认什么都不写**，
    于是"到底卡在哪个来源"完全靠猜。开着这个开关重启 app，日志里就能看到
    每个来源的开始/结束/条数/耗时。
    """
    if os.environ.get("JOBS_DEBUG", "").strip() == "1":
        print("[jobs] " + msg, flush=True)


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
            with _NetSlot():        # 占一个全局在飞名额（真正发包的这一行）
                r = fn(url, headers=kwargs.pop("headers", H), timeout=timeout,
                       proxies=proxies, **kwargs)
            if r.status_code == 200:
                return r
            last = f"HTTP {r.status_code}"
        except Exception as e:
            last = type(e).__name__
    raise RuntimeError(f"取不到 {url}：{last}")


def pages_for(max_items: int, per_page: int = 20, cap: int = 15) -> int:
    """按"想要多少条"算需要翻几页（带上限，防止用户把上限填成 10000 把站点打爆）。"""
    try:
        n = int(max_items)
    except Exception:
        n = 200
    n = max(1, min(n, 1000))
    return max(1, min(cap, -(-n // max(1, per_page))))


def sleep_between_pages(seconds: float = 0.25):
    """翻页之间歇一下：礼貌抓取，别让站点觉得被打。"""
    time.sleep(seconds)


SEARCH_WORKERS = 3          # 单个站点的并发路数上限（不是越多越好，3 路足够且礼貌）
SOURCE_WORKERS = 3          # 一次搜索里同时抓几个"来源"（每个来源内部再各自并发翻页）
PAGE_MIN_INTERVAL = 0.25    # 同一站点两次请求的最小间隔（秒）

_PAGE_LOCK = threading.Lock()
_LAST_HIT = {}              # {站点名: 上次发请求的时间戳}


def _throttle(key: str, min_interval: float = PAGE_MIN_INTERVAL):
    """全局节流：同一个站点两次请求的发出时间至少隔 min_interval 秒。

    拿不到"发车名额"就睡一小下再抢，所以 3 个线程并发时也不会在同一瞬间
    把 3 个请求同时甩给同一个站。锁只保护"抢名额"这一步、不覆盖请求本身，
    否则并发就退化成串行了。
    """
    if min_interval <= 0:
        return
    while True:
        with _PAGE_LOCK:
            wait = _LAST_HIT.get(key, 0.0) + min_interval - time.time()
            if wait <= 0:
                _LAST_HIT[key] = time.time()
                return
        time.sleep(min(wait, 0.2))


GLOBAL_INFLIGHT = 3     # 同时在飞的网络请求总数上限（不管勾了几个来源、每源翻几页）
_INFLIGHT = threading.BoundedSemaphore(GLOBAL_INFLIGHT)
# 同一时刻只允许一次搜岗（见 search_all 的说明：Streamlit 重跑不会杀掉旧线程）
_SEARCH_LOCK = threading.Lock()
SEARCH_LOCK_WAIT = 5    # 等上一次搜岗让出闸最多等几秒（测试里会调小）


class _NetSlot:
    """`with _NetSlot():` 占一个"全局在飞名额"，出来就还。

    为什么值得有：跨来源并发之后，3 个来源 × 每源 3 页 = 最多 9 条连接同时在飞。
    按站点分摊确实每站还是 3 条、间隔也够，但**总连接数**会随"勾了几个来源"线性增长。
    有了这个名额池，"同时最多几条连接"就是一个固定常数：勾 3 个来源和勾 10 个来源，
    对网络的压力一样，代价只是总耗时随来源数变长（这是该付的成本）。

    ⚠️ 用法约束：**只在真正发包的那一行占名额**（requests.get/post、fetch_json_or_text）。
    不要在 parallel_pages / fetch_task 里再包一层——那里会出现"已经拿着名额的线程再去
    申请名额"，同一个信号量嵌套申请会**直接死锁**（三个线程各拿 1 个再各等 1 个，
    谁都动不了）。所以名额只加在最底层。
    """

    def __enter__(self):
        _INFLIGHT.acquire()
        return self

    def __exit__(self, *exc):
        _INFLIGHT.release()
        return False


def parallel_pages(fetch_one, pages: int, workers: int = SEARCH_WORKERS,
                   key: str = "", min_interval: float = PAGE_MIN_INTERVAL,
                   stop_when=None):
    """并发翻页（带礼貌节流），返回 [(页号, 该页结果), ...]：按页号升序、已截断。

    fetch_one(page) -> 该页结果；**抛异常记成 None**（= 这页废了，跳过、继续翻后面的）
    stop_when(结果) -> True 表示"到底了 / 站点明确报错"，停止翻后面的页

    实现是**滚动窗口**：始终保持 workers 个请求在飞，谁先回来谁先补位（不用等整批）。
    为什么不用"按波次翻"（一波全回来再开下一波）：实测单页会出现偶发 ~20 秒卡顿，
    波次模式下这一卡会拖住整整一波；滚动窗口下它只占住 1 个槽位，别的页照常往下翻。
    另外"到底了"会立刻停止再提交新页，所以最多白翻 worker-1 页。
    只翻 1 页或 workers<=1 时自动退化成顺序抓取（方便对照 / 给慢站点留后路）。

    为什么值得做：实测抓 8 页牛客 = 26.6 秒，本地解析 160 条只花 0.0011 秒
    （占 0.004%）——时间全花在等网络上，串行等就是白等。
    """
    pages = max(1, int(pages or 1))
    if pages == 1 or workers <= 1:
        out = []
        for p in range(1, pages + 1):
            _throttle(key, min_interval)
            try:
                obj = fetch_one(p)
            except Exception:
                obj = None
            out.append((p, obj))
            if stop_when and stop_when(obj):
                break
        return out

    def _run(pg):
        _throttle(key, min_interval)
        try:
            return fetch_one(pg)
        except Exception:
            return None

    got, stop_page, next_page, pending = {}, None, 1, {}
    ex = ThreadPoolExecutor(max_workers=max(1, int(workers)))
    try:
        while True:
            while stop_page is None and len(pending) < workers and next_page <= pages:
                pending[ex.submit(_run, next_page)] = next_page   # 补满窗口
                next_page += 1
            if not pending:
                break
            finished = wait(list(pending), return_when=FIRST_COMPLETED).done
            for f in finished:                # 谁先回来先收谁，按页号记结果
                pg = pending.pop(f)
                got[pg] = f.result()
                if stop_page is None and stop_when and stop_when(got[pg]):
                    stop_page = pg            # 到底了：不再提交新页，等手上这几页收完
    finally:
        try:
            ex.shutdown(wait=False, cancel_futures=True)
        except TypeError:                   # 老 Python 没有 cancel_futures
            ex.shutdown(wait=False)

    out = sorted(got.items())
    if stop_page is not None:
        out = [(p, o) for p, o in out if p <= stop_page]
    return out


def search_tencent(keyword: str = "", city: str = "", diag: dict = None,
                   pages: int = None, max_items: int = 200) -> list:
    """腾讯招聘公开接口（免登录）。城市在客户端过滤——接口没有可用的城市参数。

    分页：pageSize 用 50（实测有效），一直翻到没数据或到 max_items。
    以前固定 2 页只拿 40 条，是"岗位太少"的原因之一。
    """
    kws, wants = split_terms(keyword), want_cities(city)
    kw = kws[0] if kws else ""
    per_page = 50
    pages = pages or pages_for(max_items, per_page, cap=10)

    def fetch(p):
        try:
            with _NetSlot():        # 占一个全局在飞名额
                d = requests.get(TENCENT_API, headers=H, timeout=25, params={
                    "keyword": kw, "pageIndex": p, "pageSize": per_page,
                    "language": "zh-cn"}).json()
            return "ok", ((d.get("Data") or {}).get("Posts") or [])
        except Exception as e:
            return "skip", f"第{p}页：{type(e).__name__}"

    def stop_when(r):
        status, posts = r or ("skip", None)
        return status == "ok" and len(posts or []) < per_page

    jobs, raw_n, err = [], 0, ""
    for p, r in parallel_pages(fetch, max(1, pages), key="tencent", stop_when=stop_when):
        status, posts = r or ("skip", None)
        if status != "ok":
            err = err or str(posts or "")
            continue
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
        if len(jobs) >= max_items:
            break
    jobs.sort(key=lambda x: (-x["match_hits"], not x["city_hit"]))
    if diag is not None:
        diag.update({"raw": raw_n, "kept": len(jobs), "cities": wants, "source_api": "公开接口"})
        if err:
            diag["api_error"] = err
    return jobs


def search_netease(keyword: str = "", city: str = "", diag: dict = None,
                   pages: int = None, max_items: int = 200) -> list:
    """网易招聘公开接口（免登录）。JD 原文直接带在 requirement/description 里。

    ⚠️ 实测这个接口对同一关键词 total 能到 1011 条，而以前只翻 2 页拿 40 条
    —— 这是"搜出来岗位太少"最大的一处欠抓。现在 pageSize=50、翻到 total 或 max_items。
    """
    kws, wants = split_terms(keyword), want_cities(city)
    kw = kws[0] if kws else ""
    per_page = 50
    pages = pages or pages_for(max_items, per_page, cap=20)

    def fetch(p):
        try:
            with _NetSlot():        # 占一个全局在飞名额
                d = requests.post(NETEASE_API, headers={**H, "Content-Type": "application/json"},
                                  timeout=25, json={"currentPage": p, "pageSize": per_page,
                                                    "keyword": kw}).json()
            dd = d.get("data") or {}
            return "ok", (dd.get("list") or []), (dd.get("total") or dd.get("totalCount"))
        except Exception as e:
            return "skip", None, f"第{p}页：{type(e).__name__}"

    def stop_when(r):
        status, lst, _total = r or ("skip", None, None)
        return status == "ok" and len(lst or []) < per_page

    jobs, raw_n, total, err = [], 0, None, ""
    for p, r in parallel_pages(fetch, max(1, pages), key="netease", stop_when=stop_when):
        status, lst, extra = r or ("skip", None, None)
        if status != "ok":
            err = err or str(extra or "")
            continue
        if total is None:
            total = extra
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
        if len(jobs) >= max_items:
            break
    jobs.sort(key=lambda x: (-x["match_hits"], not x["city_hit"]))
    if diag is not None:
        diag.update({"raw": raw_n, "kept": len(jobs), "cities": wants, "source_api": "公开接口",
                     "site_total": total})
        if err:
            diag["api_error"] = err
    return jobs


def search_remotive(keyword: str = "", city: str = "", diag: dict = None,
                    limit: int = 20) -> list:
    """Remotive 远程岗（英文，免登录）。城市一律视作"远程"，用来补海外远程机会。"""
    kws, wants = split_terms(keyword), want_cities(city)
    kw = kws[0] if kws else ""
    try:
        with _NetSlot():            # 占一个全局在飞名额
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
        # 实测：这条招聘贴 nbHits=782、nbPages=8；以前只取 1 页 200 条 → 现在翻 3 页
        # （页是独立的查询，2 路并发即可，仍按页号拼回去）
        def fetch_hn_page(pg):
            c = fetch_json_or_text(HN_ALGOLIA + "/search", params={
                "tags": "comment,story_%s" % story_id, "hitsPerPage": 100, "page": pg}).json()
            return c.get("hits") or []

        comments = []
        for _pg, got in parallel_pages(fetch_hn_page, 3, workers=2, key="hn",
                                       stop_when=lambda g: len(g or []) < 100):
            comments += got or []
        if not comments:
            raise RuntimeError("HN 招聘贴这几页一条都没拿到（可能是网络/代理问题）")
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
                      limit: int = 200) -> list:
    """官方 ATS 接口（Greenhouse）：直接读取公司挂在招聘系统上的**全部**职位。

    这是最正规的一类——公司自己开放的招聘 API，不是"爬"。名单见 ATS_COMPANIES，
    想加公司就往那里面加 slug（boards.greenhouse.io/<slug>）。
    """
    kws, wants = split_terms(keyword), want_cities(city)
    jobs, raw_n, failed = [], 0, []
    comps = list(ATS_COMPANIES.items())      # 7 家公司都挂在同一个 hosts 上，3 路并发 + 节流

    def fetch(p):
        slug, name = comps[p - 1]
        try:
            d = fetch_json_or_text(GREENHOUSE_API % slug).json()
            return "ok", name, (d.get("jobs") or [])
        except Exception as e:
            return "fail", name, type(e).__name__

    for _p, r in parallel_pages(fetch, len(comps), key="greenhouse"):
        if len(jobs) >= limit:       # 已经够了就不再往结果里加（并发抓回来的照样丢掉）
            break
        status, name, payload = r or ("fail", "", "unknown")
        if status != "ok":
            failed.append(f"{name}:{payload}")
            continue
        lst = payload
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
BOSS_API = "/wapi/zpgeek/search/joblist.json"      # BOSS 职位列表页自己调的接口
# 实测：同一个会话翻到第 5~6 页时 BOSS 会回 {code:37, message:"您的环境存在异常."}
# （放慢到 1.2 秒一页也一样，说明是它自己的会话级风控，不是我们发太快）。
# 所以 BOSS 侧最多翻这么多页，够了就停；**不绕风控**——它说停就停，并把原因写进诊断。
BOSS_MAX_PAGES = 5


def _boss_api_js(city_code: str, kw: str, pages: int, per_page: int = 30) -> str:
    """在已登录的 BOSS 页面里，翻页调它自己的搜索接口，把结果 JSON 带回来。

    和牛客那套一个思路：**用浏览器替你发这个请求**，这样 cookie / Referer 一定是对的，
    不用去逆向签名。请求是我们之外的用户主动点一次搜索才发，低频只读。

    和牛客一样留了"**单页失败不要整体放弃**"：某页偶发失败就重试 1 次、仍失败就跳过
    这页继续翻（实测第 6 页偶发失败会让整次搜索只剩 5 页 150 条）。

    超时是三重的，因为实测踩过"整次搜索 150 秒没回来"：
      · 单次 fetch 12 秒（AbortController）——页面里的 fetch 默认**没有超时**，
        站点一挂就是直到 CDP 自己超时（150s）；
      · 整轮 60 秒上限——超了就把已经拿到的先返回；
      · Python 侧 CDP 调用 150 秒硬上限。
    """
    q = f"&query={quote(kw)}" if kw else ""
    return """
    (async function(){
      var out = [], total = 0, done = 0, err = '', skipped = [], t0 = Date.now();
      for (var p = 1; p <= %d; p++) {
        if (Date.now() - t0 > 60000) { err = '整轮超时(60s)，已拿到的先返回'; break; }
        var d = null;
        for (var a = 0; a < 2; a++) {
          var ctl = new AbortController();
          var to = setTimeout(function(){ ctl.abort(); }, 12000);
          try {
            var r = await fetch('%s?scene=1&city=%s&page=' + p + '&pageSize=%d%s',
                                {credentials: 'include', signal: ctl.signal});
            d = await r.json();
            clearTimeout(to);
            break;
          } catch (e) {
            clearTimeout(to);
            err = String(e);
            await new Promise(function(res){ setTimeout(res, 600); });
          }
        }
        if (!d) { skipped.push(p); continue; }
        var z = (d && d.zpData) || {};
        if (d.code !== 0) { err = d.message || 'code 异常'; break; }
        if (z.resCount) { total = z.resCount; }
        if (z.jobList && z.jobList.length) { out = out.concat(z.jobList); done = p; }
        else { break; }
        if (!z.hasMore) { break; }
        await new Promise(function(res){ setTimeout(res, 350); });
      }
      return JSON.stringify({items: out, total: total, pages: done,
                             skipped: skipped, err: err});
    })()
    """ % (pages, BOSS_API, city_code, per_page, q)


def _boss_map(items: list, kws: list, wants: list, diag=None,
              total=None, pages_done=None, pages_wanted=None,
              skipped=None, err="") -> list:
    """把 BOSS 接口的 jobList 映射成我们的字段（结构化，不用大模型）。"""
    jobs = []
    for j in items:
        title = (j.get("jobName") or "").strip()
        if not title:
            continue
        brand = (j.get("brandName") or "").strip()
        c = (j.get("cityName") or "").strip()
        area = "·".join(x for x in [j.get("areaDistrict"), j.get("businessDistrict")] if x)
        city_full = f"{c}·{area}" if (c and area) else (c or area)
        skills = "、".join(j.get("skills") or [])
        labels = "、".join(j.get("jobLabels") or [])
        welfare = "、".join(j.get("welfareList") or [])
        jid = j.get("encryptJobId") or ""
        url = f"https://www.zhipin.com/job_detail/{jid}.html" if jid else ""
        boss = " ".join(x for x in [str(j.get("bossName") or ""), str(j.get("bossTitle") or "")] if x)
        extra = " | ".join(x for x in [brand, j.get("brandIndustry"),
                                       j.get("brandScaleName"), boss, labels] if x)
        jd = "\n".join(x for x in [
            f"岗位：{title}",
            f"公司：{brand}" if brand else "",
            f"经验/学历：{labels}" if labels else "",
            f"技能关键词：{skills}" if skills else "",
            f"福利：{welfare}" if welfare else "",
            "（BOSS 接口不返回 JD 正文；点开链接看详情，或入库时让程序去抓详情页）",
        ] if x)
        jobs.append(_pack(title, brand, city_full, j.get("salaryDesc") or "", url, "BOSS直聘",
                          extra=extra[:120], jd=jd,
                          hits=_kw_hits(f"{title} {skills} {labels}", kws),
                          ch=city_hit(city_full, wants)))
    jobs.sort(key=lambda x: (-x["match_hits"], not x["city_hit"]))
    if diag is not None:
        diag.update({"raw": len(items), "kept": len(jobs), "cities": wants,
                     "source_api": "站点搜索接口（复用本机登录态，只读）",
                     "site_total": total, "api_pages": pages_done,
                     "note": "BOSS 职位页自己调的接口；每页 30 条、支持翻页"})
        if pages_wanted:
            diag["api_pages_wanted"] = pages_wanted
        if skipped:
            diag["api_skipped_pages"] = skipped
        if err:
            diag["api_note"] = str(err)[:120]
        try:
            if total and len(items) < int(total):
                diag["boss_limit"] = (
                    "BOSS 风控：单次大约只给 %d 页（约 %d 条），站点总数 %s 更多但拿不到；"
                    "这是它自己的限制，我们不绕（想再多就换关键词/城市分次搜）。"
                    % (BOSS_MAX_PAGES, BOSS_MAX_PAGES * 30, total))
        except Exception:
            pass
    return jobs


def search_boss(keyword: str = "", city: str = "", ask_model=None,
                diag: dict = None, max_items: int = 200) -> list:
    """BOSS直聘：在**本机已登录的 Edge** 里调它自己的搜索接口（先跑一次 setup 登录）。

    为什么从"抓页面文本 → 大模型抽"改成调接口（2026-10-10 实测的事故）：
      用户搜「AI + 南京」时 BOSS 返回 **0 条**。查下来不是网络问题——
      URL 里明明写了 city=101190100（南京），但页面返回的全是**德阳**岗位：
      BOSS 前端会用它自己记的"上次选中城市"覆盖 URL 参数，而这个 Edge 独立 profile
      里记着德阳（正是当初测"未收录城市"时留下的）。结果客户端严格城市过滤
      把德阳岗位全砍掉 → 0 条。
    改成接口之后：城市完全由参数决定，返回结构化 JSON（薪资/经验/学历/技能/公司/招聘者），
    **不用大模型抽**、支持翻页。实测「AI + 南京」resCount=450、每页 30 条、hasMore=true。
    接口万一失败，仍然退回老的"页面文本 + 大模型"那条路（并在诊断里说明它会踩城市覆盖）。
    """
    import browser_fetch as bf
    ok, why = bf.desktop_available()
    if not ok:
        raise RuntimeError(why)
    kws, wants = split_terms(keyword), want_cities(city)
    kw_first = kws[0] if kws else ""
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
    page_url = (f"https://www.zhipin.com/web/geek/job?query={quote(kw_first)}"
                f"&city={city_code}")
    per_page = 30
    pages = min(pages_for(max_items, per_page, cap=15), BOSS_MAX_PAGES)
    data = {}
    _dbg("BOSS：调接口 %s（城市码 %s，%d 页）" % (page_url, city_code, pages))
    _t0 = time.perf_counter()
    try:
        raw = bf.js_on_page(page_url, _boss_api_js(city_code, kw_first, pages, per_page),
                            wait=6, timeout=150)
        data = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception as e:
        _dbg("BOSS 接口异常：%.1fs %s" % (time.perf_counter() - _t0, str(e)[:160]))
        data = {"items": [], "err": f"{type(e).__name__}: {str(e)[:120]}"}
    items = data.get("items") or []
    _dbg("BOSS 接口回来：%.1fs，%d 条（页 %s/%s，err=%s）"
         % (time.perf_counter() - _t0, len(items), data.get("pages"), pages,
            str(data.get("err") or "")[:60]))
    if items:
        jobs = _boss_map(items, kws, wants, diag, total=data.get("total"),
                         pages_done=data.get("pages"), pages_wanted=pages,
                         skipped=data.get("skipped"), err=data.get("err") or "")
        if jobs:
            return jobs
    # ---- 兜底：老路（抓页面文本 → 大模型抽） ----
    if diag is not None:
        diag["api_fallback"] = ("接口没拿到岗位（%s），改用页面文本+大模型抽取"
                                % (data.get("err") or "空结果"))
        diag["api_fallback_note"] = ("注意：这条路会被 BOSS 自己记的城市覆盖 URL 参数，"
                                     "返回的城市可能和你选的不一致（接口那条路没这个问题）")
    if not ask_model:
        if diag is not None:
            diag["api_error"] = "接口空结果，且没有 ask_model，无法兜底抽取"
        return []
    html = bf.fetch_html(page_url, wait=8)
    text = html_to_text(html)
    head = text[:1000]
    if "登录" in head and "职位" not in text:
        raise RuntimeError("BOSS 返回的像登录页。先跑一次 "
                           "python -m browser_fetch --setup，在弹出窗口里登录 BOSS 再试")
    return extract_jobs(text, ask_model, source="BOSS", diag=diag)


def search(source: str, keyword: str, city: str = "", ask_model=None,
           diag: dict = None, max_items: int = 200) -> list:
    """统一入口。max_items = 这个来源最多抓多少条（决定翻几页）。"""
    if source == "牛客":
        return search_nowcoder(keyword, city, diag=diag, max_items=max_items)
    if source == "腾讯招聘":
        return search_tencent(keyword, city, diag=diag, max_items=max_items)
    if source == "网易招聘":
        return search_netease(keyword, city, diag=diag, max_items=max_items)
    if source == "Remotive(远程)":
        return search_remotive(keyword, city, diag=diag, limit=max_items)
    if source == "RemoteOK(远程)":
        return search_remoteok(keyword, city, diag=diag, limit=max_items)
    if source == "Arbeitnow(海外)":
        return search_arbeitnow(keyword, city, diag=diag, limit=max_items)
    if source == "WeWorkRemotely(远程)":
        return search_wwr(keyword, city, diag=diag, limit=max_items)
    if source == "HN Who's Hiring(海外)":
        return search_hn_hiring(keyword, city, diag=diag, limit=max_items)
    if source == "Greenhouse-AI公司(海外)":
        return search_greenhouse(keyword, city, diag=diag, limit=max_items)
    if source == "实习僧":
        return search_shixiseng(keyword, city or "", ask_model, diag=diag)
    if source == "BOSS直聘":
        return search_boss(keyword, city or "", ask_model, diag=diag, max_items=max_items)
    raise ValueError(f"未知来源：{source}")


# ============================================================
# 4.5) 搜索结果缓存（同一「来源 + 关键词 + 城市 + 每源上限」10 分钟内直接复用）
# ============================================================
# 为什么要缓存：抓一次多平台要十几到二十几秒，几乎全是网络等待。用户在界面上
# 反复点「搜岗」（想换个关键词试试、或者手滑点了两次）时，完全没必要把同一批
# 请求再打一遍——对站点也是负担。所以按这个四元组存**原始来源结果**，默认 10 分钟。
#
# 只缓存「来源返回的原始结果」：城市过滤、合并去重仍然在缓存之后做，
# 所以同一份缓存配上 strict_city 开关的不同取值也都是对的。
CACHE_TTL = 600                # 秒。10 分钟内重复搜同一条件 = 秒回
CACHE_MAX_ENTRIES = 60         # 最多留多少条，超了删最旧的（防缓存文件无限长大）
CACHE_ENABLED = True           # 测试里会关掉，避免假数据落进真缓存
CACHE_PATH = Path(__file__).resolve().parent / "data" / "search_cache.json"
_CACHE_LOCK = threading.Lock()


def cache_path() -> Path:
    """缓存文件位置。环境变量 JOBS_CACHE 可覆盖（测试/多实例用）。"""
    env = os.environ.get("JOBS_CACHE", "").strip()
    return Path(env) if env else CACHE_PATH


def _cache_read_raw() -> dict:
    try:
        data = json.loads(cache_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:          # 文件不存在 / 坏了都当"空缓存"，绝不让缓存把搜岗搞挂
        return {}


def _cache_write_raw(data: dict):
    p = cache_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, p)     # 原子替换：避免读到写了一半的文件
    except Exception:
        pass


def cache_key(source: str, keyword: str, city: str, max_items: int) -> str:
    raw = (f"{(source or '').strip()}|{(keyword or '').strip().lower()}|"
           f"{(city or '').strip()}|{int(max_items or 0)}")
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]


def cache_get(source, keyword, city, max_items, ttl: int = CACHE_TTL):
    """命中返回 (岗位列表, 缓存了多久)；没命中/过期返回 (None, 0)。"""
    if not CACHE_ENABLED:
        return None, 0
    k = cache_key(source, keyword, city, max_items)
    with _CACHE_LOCK:
        ent = _cache_read_raw().get(k)
    if not isinstance(ent, dict) or not isinstance(ent.get("jobs"), list):
        return None, 0
    age = time.time() - float(ent.get("t") or 0)
    if age > ttl:
        return None, 0
    return ent["jobs"], age


def cache_put(source, keyword, city, max_items, jobs: list):
    if not CACHE_ENABLED or not jobs:
        return
    k = cache_key(source, keyword, city, max_items)
    with _CACHE_LOCK:
        store = _cache_read_raw()
        store[k] = {"t": time.time(), "n": len(jobs), "src": source, "kw": keyword,
                    "city": city, "max": int(max_items or 0), "jobs": jobs}
        if len(store) > CACHE_MAX_ENTRIES:
            newest = sorted(store.items(), key=lambda kv: -((kv[1] or {}).get("t") or 0))
            store = dict(newest[:CACHE_MAX_ENTRIES])
        _cache_write_raw(store)


def cache_stats() -> dict:
    """给界面看：缓存里有几条、多大、最新一条多久前、TTL 多久。"""
    store = _cache_read_raw()
    p = cache_path()
    try:
        size = p.stat().st_size if p.exists() else 0
    except Exception:
        size = 0
    newest = max(((e or {}).get("t") or 0 for e in store.values()), default=0)
    return {"entries": len(store), "size_kb": round(size / 1024, 1),
            "ttl_min": CACHE_TTL // 60, "enabled": bool(CACHE_ENABLED),
            "newest_age_s": int(time.time() - newest) if newest else None}


def cache_clear() -> int:
    """清空缓存，返回清掉的条数。"""
    with _CACHE_LOCK:
        n = len(_cache_read_raw())
        _cache_write_raw({})
    return n


# ============================================================
# 5) 多平台合并搜岗
# ============================================================
ALL_SOURCES = "全部平台（合并去重）"


def dedup_key(job: dict) -> str:
    """合并去重用的键：**岗位名 + 公司 + 城市**（公司名不可用时退回 URL）。

    为什么不只用「岗位名 + 公司」——实测数据（牛客搜「AI」，深抓到 280 条）：
      · 按「岗位名 + 公司」去重 → 只剩 79 条
      · 按「岗位名 + 公司 + 城市」去重 → 276 条
      · 按 URL 去重 → 276 条（和上一行吻合，说明差掉的 197 条不是重复）
    原因是同一家公司会在**很多城市**发同名岗位（实测「AI应用开发（可转正）@墨泊可士」
    10 条覆盖 10 个城市，URL 各不相同）。按「名+公司」合并会把它们全砍成 1 条，
    这就是"岗位太少"的一个真原因。

    加城市这一维之后：同城 + 同名 + 同公司仍然合并（"同一岗位被两个平台都列出来"
    照样去重），不同城市的真实岗位各留一条。公司名拿不到时退回 URL 兜底。
    """
    def _n(s):
        return re.sub(r"\s+", "", (s or "").lower())

    title, comp, city = _n(job.get("title")), _n(job.get("company")), _n(job.get("city"))
    usable = comp and not comp.startswith("company#") and not comp.startswith("牛客公司#")
    if usable:
        return f"{title}|{comp}|{city}"
    url = (job.get("url") or "").strip()
    return f"{title}|{city}|{url}" if url else f"{title}|{comp}|{city}"


def _parallel_safe(task) -> bool:
    """这个来源能不能放进线程池（task = (来源名, 自定义地址)）。

    只有**纯 HTTP** 的来源可以：它们只做 requests + 本地解析，没有共享状态。
    实习僧 / BOSS 不行——它们走无头浏览器 + 大模型抽岗位，而界面传进来的 ask_model
    是 Streamlit 里的 `ask_chat`，会读写 `st.session_state`，**Streamlit 的会话状态
    不是线程安全的**。把这两个来源放主线程串行跑，界面就不会因为并发而莫名报错。
    """
    src, custom_url = task
    if custom_url:
        return True          # 自定义来源是纯 HTTP（RSS/JSON 解析），不调模型
    return src in PARALLEL_SAFE_SOURCES


def boss_available() -> tuple:
    """BOSS 能不能用：返回 (bool, 原因)。云端/没浏览器时为 False。"""
    try:
        import browser_fetch as bf
        return bf.desktop_available()
    except Exception as e:
        return False, f"浏览器抓取模块不可用：{str(e)[:120]}"


def search_all(keyword: str, city: str = "", ask_model=None,
               sources: list = None, strict_city: bool = True,
               custom_url: str = "", max_per_source: int = 200,
               use_cache: bool = True) -> dict:
    """搜岗的公开入口：**同一时刻只允许一次**，其余细节见 _search_all_impl()。

    为什么要这道闸：Streamlit 里用户换一次交互就会重跑脚本，但**上一次运行里已经
    在发请求的线程不会被杀掉**（Python 线程杀不掉）。用户手快点两下「开始搜岗」，
    两次搜索会同时抢那 3 个全局在飞名额，两边都变慢——实测能把一次搜索拖到 3 分钟
    以上，看起来就像"卡死了"。所以第二次直接拒绝并说清楚，而不是默默排队。
    """
    if not _SEARCH_LOCK.acquire(timeout=SEARCH_LOCK_WAIT):
        raise RuntimeError(
            "上一次搜岗还没跑完（请求已经发出去了），等结果出来再点。"
            "连着点两次会让同一批请求排队跑两遍，只会更慢。")
    _t0 = time.perf_counter()
    _dbg("搜岗开始：关键词=%r 城市=%r 来源=%s 上限=%s" % (keyword, city, sources, max_per_source))
    try:
        res = _search_all_impl(keyword, city, ask_model, sources, strict_city,
                               custom_url, max_per_source, use_cache)
        _dbg("搜岗结束：%.1fs，合并 %d 条 %s" % (time.perf_counter() - _t0,
                                               len(res.get("jobs") or []), res.get("by_source")))
        return res
    finally:
        _SEARCH_LOCK.release()


def _search_all_impl(keyword: str, city: str = "", ask_model=None,
                     sources: list = None, strict_city: bool = True,
                     custom_url: str = "", max_per_source: int = 200,
                     use_cache: bool = True) -> dict:
    """一次搜索，把多个平台的结果合并去重。

    use_cache=True 时：同一「来源+关键词+城市+每源上限」10 分钟内直接复用上次结果
    （抓一次十几秒，全是网络等待；重复搜同一条件是纯浪费）。每个来源的命不命中
    都写进 diag[来源]["cache"]，界面上能看到。

    并发：**纯 HTTP 的来源并发抓**（SOURCE_WORKERS=3，每个来源内部再各自并发翻页），
    要浏览器 + 大模型的来源（实习僧 / BOSS）留在主线程串行（ask_chat 不是线程安全的，
    见 _parallel_safe）。合并结果仍按 sources 的先后顺序输出，与串行抓取一致。

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

    def fetch_task(task):
        """抓一个来源（含缓存读写），返回 (岗位列表, diag, 错误信息)。

        注意：**这个函数可能跑在线程里**，所以它只许做纯 HTTP 的事（见 _parallel_safe）；
        异常一律在内部吃掉转成错误信息，避免一个来源炸掉整次搜索。
        """
        src, _cu = task
        d = {}
        _t0 = time.perf_counter()
        try:
            rows = None
            if use_cache and not _cu:              # 自定义来源不缓存（地址就是变量）
                hit, age = cache_get(src, keyword, city, max_per_source)
                if hit is not None:
                    rows = hit
                    d["cache"] = "命中缓存（%.0f 秒前抓的同一条件，未联网）" % age
            if rows is None:
                if _cu:
                    rows = search_custom_feed(_cu, keyword, city,
                                              diag=d, limit=max_per_source)
                else:
                    rows = search(src, keyword, city, ask_model, diag=d,
                                  max_items=max_per_source)
                    if use_cache:
                        cache_put(src, keyword, city, max_per_source, rows)
                        d["cache"] = "未命中缓存，这次联网抓取（%d 条已写入缓存）" % len(rows)
            _dbg("来源 %s 完成：%d 条，%.1fs%s" % (src, len(rows),
                                                  time.perf_counter() - _t0,
                                                  "（命中缓存）" if rows is not None and d.get("cache", "").startswith("命中") else ""))
            return list(rows), d, ""
        except Exception as e:
            _dbg("来源 %s 失败：%.1fs %s" % (src, time.perf_counter() - _t0, str(e)[:120]))
            return [], d, str(e)[:200]

    # ---- 抓取：纯 HTTP 的来源并发跑；要浏览器/大模型的留在主线程串行 ----
    fetched = {}
    safe = [t for t in tasks if _parallel_safe(t)]
    slow = [t for t in tasks if not _parallel_safe(t)]
    _dbg("开始抓取：并发 %d 个纯 HTTP 来源 %s；串行 %s" % (len(safe), safe, slow))
    if len(safe) > 1:
        with ThreadPoolExecutor(max_workers=min(SOURCE_WORKERS, len(safe))) as ex:
            for task, got in zip(safe, ex.map(fetch_task, safe)):   # map 保序
                fetched[task[0]] = got
    else:
        for t in safe:
            fetched[t[0]] = fetch_task(t)
    for t in slow:
        fetched[t[0]] = fetch_task(t)

    for src, _custom_url in tasks:        # 仍按原顺序合并，输出顺序与串行时完全一致
        rows, d, err = fetched.get(src, ([], {}, "内部错误：这个来源没抓到结果"))
        raw_by_src[src] = list(rows)
        if err:
            by_source[src] = 0
            errors[src] = err
            diag[src] = d
            continue
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
                city_miss[src] = len(rows)          # 这个平台这次没有目标城市的岗位
            rows = keep
        by_source[src] = len(rows)
        diag[src] = d
        for j in rows:
            # 去重键见 dedup_key()：岗位名 + 公司，公司名拿不到时退回 URL
            key = dedup_key(j)
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
                key = dedup_key(j)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(j)
        relaxed_all = True
    diag["keywords"] = split_terms(keyword)
    diag["cities"] = wants
    cache_hits = sum(1 for _s, _d in diag.items()
                     if isinstance(_d, dict)
                     and str(_d.get("cache", "")).startswith("命中缓存"))
    return {"jobs": merged, "by_source": by_source, "errors": errors,
            "diag": diag, "cities": city_stats, "relaxed": relaxed,
            "city_miss": city_miss, "relaxed_all": relaxed_all,
            "wants": wants, "strict_city": strict_city,
            "cache_hits": cache_hits, "cache_enabled": bool(use_cache)}
