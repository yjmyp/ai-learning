# -*- coding: utf-8 -*-
"""
resume_templates · 简历模板引擎（表现层，不含内容与样式定义）
=============================================================
本文件只剩「模板怎么拼」：注册表 + 公共片段 + 渲染器 + 统一入口。

数据在 resume_content.py（简历有什么），样式在 resume_styles.py（长什么样），
本文件负责把它们拼成完整 HTML。三层分开后：
  - 改简历内容 → 改 resume_content.py，模板全部同步
  - 换模板样式 → 改 resume_styles.py
  - 加新模板   → 三处：styles 加 CSS、本文件加 render_xxx、RENDERERS 登记
"""
import base64
import hashlib
import re
from pathlib import Path

from resume_content import DEFAULT_CONTENT, find_photo, photo_data_uri, _photo_box
from resume_styles import (CSS_CLASSIC, CSS_SIDEBAR, CSS_COMPACT,
                           CSS_TIMELINE, CSS_BAND, CSS_MODERN, CSS_DUO)


def build_tag() -> str:
    """本文件内容的短指纹。

    用途：本地和 Streamlit Cloud 各显示一次，**数字不一样就说明云端还在跑旧代码**
    （Streamlit Cloud 有时要手动 Reboot 才会加载新提交），比肉眼比对排版靠谱。
    """
    try:
        return hashlib.md5(Path(__file__).read_bytes()).hexdigest()[:8]
    except Exception:
        return "unknown"


TEMPLATES = {
    "classic": "经典单栏（推荐 · 结果前置）",
    "sidebar": "左侧栏（照片 / 技能放侧边 · 信息密度高）",
    "compact": "极简黑白（传统团队 · 去装饰）",
    "timeline": "时间线式（项目沿时间轴排 · 经历突出）",
    "band": "顶部色带式（深色横幅 · 现代醒目）",
    "modern": "现代强调式（技能标签云 · 卡片项目）",
    "duo": "双栏均衡（左经历右技能 · 欧美常见布局）",
}

TEMPLATE_DESC = {
    "classic": "结果前置的单栏，从上往下扫最顺。默认选这个。",
    "sidebar": "左边一栏放照片 + 联系方式 + 技能，右边只放经历。照片最显眼。",
    "compact": "极简黑白、宋体、细线，不要颜色。投偏传统 / 国企类团队更稳。",
    "timeline": "每个项目一个时间节点，沿着纵向时间线排，经历占比最大。适合项目多的人。",
    "band": "顶部一整条深色横幅放姓名和联系方式，下面内容清爽分区。第一眼最醒目。",
    "modern": "头部超大、技能做成标签云、项目做成卡片。投互联网 / 偏设计感的团队更搭。",
    "duo": "左栏放项目经历，右栏放照片 / 联系方式 / 技能。信息密度高、一眼扫完全部。",
}


# ---------- 公用片段：每个模板都会用到的「零件」，写一次 ----------

def _links_html(content) -> str:
    return "<br>".join(f"{label}：{url}" for label, url in content["links"])


def _meta_html(content) -> str:
    return "<br>".join(content["meta"])


def _summary_html(content) -> str:
    s = content.get("summary", "")
    if not s:
        return ""
    return f'<h2>个人概述</h2><div class="summary">{s}</div>'


def _project_html(p, show_result=True) -> str:
    bullets = "".join(f"<li>{b}</li>" for b in p["bullets"])
    res = f'<div class="result">{p["result"]}</div>' if show_result else ""
    # 技术栈拆成小标签，比一整行竖线好看，也更容易扫
    chips = "".join(f'<span class="chip">{s.strip()}</span>'
                    for s in re.split(r"[｜|·]", p["tech"]) if s.strip())
    return (f'<div class="proj"><div class="proj-head">'
            f'<span class="proj-title">{p["title"]}</span>'
            f'<span class="proj-date">{p["date"]}</span></div>'
            f'{res}<div class="tech">{chips}</div>'
            f"<ul>{bullets}</ul></div>")


def _skills_html(content) -> str:
    return "".join(f"<div><b>{k}</b>{v}</div>" for k, v in content["skills"])


def _notes_html(content) -> str:
    return "".join(f"<li>{n}</li>" for n in content["notes"])


FOOT = '<div class="foot">本简历由本人独立撰写，项目与数据均可验证。</div>'


def _doc(title: str, css: str, body: str) -> str:
    return (f'<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n'
            f"<title>{title}</title>\n<style>{css}</style>\n</head>\n<body>\n{body}\n"
            f"</body>\n</html>\n")


# ---------- 渲染器：每个模板一份，把「内容 + 样式」拼成整页 ----------

def render_classic(content=None, photo_uri: str = "") -> str:
    c = content or DEFAULT_CONTENT
    projects = "".join(_project_html(p) for p in c["projects"])
    summary = _summary_html(c)
    body = f"""<div class="page">
  <div class="head">
    <div class="head-main">
      <h1>{c["name"]}</h1>
      <div class="role">{c["role"]}</div>
      <div class="meta">{_meta_html(c)}</div>
      <div class="links">{_links_html(c)}</div>
    </div>
    {_photo_box(photo_uri)}
  </div>
  {summary}
  <h2>项目经历</h2>
  {projects}
  <h2>教育背景</h2>
  <div class="meta">{c["education"]}</div>
  <h2>技能</h2>
  <div class="skills">{_skills_html(c)}</div>
  <h2>求职说明</h2>
  <ul class="note">{_notes_html(c)}</ul>
  {FOOT}
</div>"""
    return _doc(f'{c["name"]}-简历', CSS_CLASSIC, body)


def render_sidebar(content=None, photo_uri: str = "") -> str:
    c = content or DEFAULT_CONTENT
    projects = "".join(_project_html(p) for p in c["projects"])
    side_meta = "".join(f"<div>{m}</div>" for m in c["meta"])
    side_skills = "".join(f"<div><b>{k}</b>{v}</div>" for k, v in c["skills"])
    side_notes = "".join(f"<li>{n}</li>" for n in c["notes"])
    summary = _summary_html(c)
    body = f"""<div class="page">
  <div class="side">
    {_photo_box(photo_uri)}
    <h3>联系方式</h3>
    <div class="meta">{side_meta}</div>
    <h3>技能</h3>
    <div class="skill meta">{side_skills}</div>
    <h3>求职说明</h3>
    <ul class="meta">{side_notes}</ul>
  </div>
  <div class="main">
    <h1>{c["name"]}</h1>
    <div class="role">{c["role"]}</div>
    <div class="links">{_links_html(c)}</div>
    {summary}
    <h2>项目经历</h2>
    {projects}
    <h2>教育背景</h2>
    <div class="meta">{c["education"]}</div>
    {FOOT}
  </div>
</div>"""
    return _doc(f'{c["name"]}-简历', CSS_SIDEBAR, body)


def render_compact(content=None, photo_uri: str = "") -> str:
    c = content or DEFAULT_CONTENT
    projects = "".join(_project_html(p) for p in c["projects"])
    summary = _summary_html(c)
    body = f"""<div class="page">
  <div class="head">
    <div class="head-main">
      <h1>{c["name"]}</h1>
      <div class="role">{c["role"]}</div>
      <div class="meta">{_meta_html(c)}</div>
      <div class="links">{_links_html(c)}</div>
    </div>
    {_photo_box(photo_uri)}
  </div>
  {summary}
  <h2>项目经历</h2>
  {projects}
  <h2>教育背景</h2>
  <div class="meta">{c["education"]}</div>
  <h2>技能</h2>
  <div class="skills">{_skills_html(c)}</div>
  <h2>求职说明</h2>
  <ul class="note">{_notes_html(c)}</ul>
  {FOOT}
</div>"""
    return _doc(f'{c["name"]}-简历', CSS_COMPACT, body)


def render_timeline(content=None, photo_uri: str = "") -> str:
    """时间线式：项目沿纵向时间线排，经历占比最大。"""
    c = content or DEFAULT_CONTENT
    summary = _summary_html(c)
    items = []
    for p in c["projects"]:
        bullets = "".join(f"<li>{b}</li>" for b in p["bullets"])
        res = f'<div class="result">{p["result"]}</div>'
        chips = "".join(f'<span class="chip">{s.strip()}</span>'
                        for s in re.split(r"[｜|·]", p["tech"]) if s.strip())
        items.append(
            f'<div class="tl-item"><div class="tl-head">'
            f'<span class="tl-title">{p["title"]}</span>'
            f'<span class="tl-date">{p["date"]}</span></div>'
            f'{res}<div class="tech">{chips}</div><ul>{bullets}</ul></div>')
    body = f"""<div class="page">
  <div class="head">
    <div class="head-main">
      <h1>{c["name"]}</h1>
      <div class="role">{c["role"]}</div>
      <div class="meta">{_meta_html(c)}</div>
      <div class="links">{_links_html(c)}</div>
    </div>
    {_photo_box(photo_uri)}
  </div>
  {summary}
  <h2>项目经历</h2>
  <div class="tl">{"".join(items)}</div>
  <h2>教育背景</h2>
  <div class="meta">{c["education"]}</div>
  <h2>技能</h2>
  <div class="skills">{_skills_html(c)}</div>
  <h2>求职说明</h2>
  <ul class="note">{_notes_html(c)}</ul>
  {FOOT}
</div>"""
    return _doc(f'{c["name"]}-简历', CSS_TIMELINE, body)


def render_band(content=None, photo_uri: str = "") -> str:
    """顶部色带式：深色横幅放姓名/联系方式，内容区卡片化。"""
    c = content or DEFAULT_CONTENT
    projects = "".join(_project_html(p) for p in c["projects"])
    summary = _summary_html(c)
    body = f"""<div class="page">
  <div class="band">
    <div class="band-main">
      <h1>{c["name"]}</h1>
      <div class="role">{c["role"]}</div>
      <div class="meta">{_meta_html(c)}</div>
      <div class="links">{_links_html(c)}</div>
    </div>
    {_photo_box(photo_uri)}
  </div>
  <div class="body">
    {summary}
    <h2>项目经历</h2>
    {projects}
    <h2>教育背景</h2>
    <div class="meta">{c["education"]}</div>
    <h2>技能</h2>
    <div class="skills">{_skills_html(c)}</div>
    <h2>求职说明</h2>
    <ul class="note">{_notes_html(c)}</ul>
    {FOOT}
  </div>
</div>"""
    return _doc(f'{c["name"]}-简历', CSS_BAND, body)


def render_modern(content=None, photo_uri: str = "") -> str:
    """现代强调式：超大头部、技能标签云、卡片项目。"""
    c = content or DEFAULT_CONTENT
    projects = "".join(_project_html(p) for p in c["projects"])
    summary = _summary_html(c)
    skill_tags = "".join(f'<span class="skill-tag"><b>{k}</b>{v}</span>'
                         for k, v in c["skills"])
    body = f"""<div class="page">
  <div class="head">
    <div class="head-main">
      <h1>{c["name"]}</h1>
      <div class="role">{c["role"]}</div>
      <div class="meta">{_meta_html(c)}</div>
      <div class="links">{_links_html(c)}</div>
    </div>
    {_photo_box(photo_uri)}
  </div>
  {summary}
  <h2>项目经历</h2>
  {projects}
  <h2>教育背景</h2>
  <div class="meta">{c["education"]}</div>
  <h2>技能</h2>
  <div class="skills">{skill_tags}</div>
  <h2>求职说明</h2>
  <ul class="note">{_notes_html(c)}</ul>
  {FOOT}
</div>"""
    return _doc(f'{c["name"]}-简历', CSS_MODERN, body)


def render_duo(content=None, photo_uri: str = "") -> str:
    """双栏均衡式：左 62% 项目经历，右 38% 照片/联系/技能。欧美简历最常见布局。"""
    c = content or DEFAULT_CONTENT
    projects = "".join(_project_html(p) for p in c["projects"])
    side_meta = "".join(f"<div>{m}</div>" for m in c["meta"])
    side_skills = "".join(f"<div><b>{k}</b>{v}</div>" for k, v in c["skills"])
    side_notes = "".join(f"<li>{n}</li>" for n in c["notes"])
    summary = _summary_html(c)
    body = f"""<div class="page">
  <div class="main">
    <h1>{c["name"]}</h1>
    <div class="role">{c["role"]}</div>
    {summary}
    <h2>项目经历</h2>
    {projects}
    <h2>教育背景</h2>
    <div class="meta">{c["education"]}</div>
    {FOOT}
  </div>
  <div class="side">
    {_photo_box(photo_uri)}
    <h3>联系方式</h3>
    <div class="meta">{side_meta}</div>
    <h3>技能</h3>
    <div class="skill meta">{side_skills}</div>
    <h3>求职说明</h3>
    <ul class="meta">{side_notes}</ul>
  </div>
</div>"""
    return _doc(f'{c["name"]}-简历', CSS_DUO, body)


# ---------- 注册表 + 统一入口：调用方只认模板名 ----------

RENDERERS = {
    "classic": render_classic,
    "sidebar": render_sidebar,
    "compact": render_compact,
    "timeline": render_timeline,
    "band": render_band,
    "modern": render_modern,
    "duo": render_duo,
}


def render(tpl: str = "classic", content=None, photo_uri: str = "") -> str:
    """按模板名生成整页 HTML。photo_uri 传空字符串时不显示照片位。"""
    fn = RENDERERS.get(tpl) or render_classic
    return fn(content, photo_uri)


def render_with_photo(tpl: str = "classic", content=None, photo_path=None) -> str:
    """自动找照片（或指定路径）后渲染。"""
    return render(tpl, content, photo_data_uri(photo_path))


def to_markdown(content=None) -> str:
    """把同一份 DEFAULT_CONTENT 转成 Markdown 文本（可编辑、可投递、可转其他格式）。"""
    c = content or DEFAULT_CONTENT
    lines = [f"# {c['name']} · {c['role']}", ""]
    lines += [m.replace("<b>", "**").replace("</b>", "**").replace("<br>", "；")
              for m in c["meta"]]
    if c.get("links"):
        lines.append("；".join(f"{label}：{url}" for label, url in c["links"]))
    lines += ["", "## 个人概述", ""]
    lines += [c.get("summary", "")]
    lines += ["", "## 项目经历", ""]
    for p in c["projects"]:
        lines.append(f"### {p['title']}　{p.get('date', '')}")
        lines.append("")
        lines.append(p["result"].replace("<b>", "**").replace("</b>", "**"))
        lines.append("")
        lines.append(f"技术栈：{p['tech']}")
        for b in p["bullets"]:
            lines.append("- " + b.replace("<b>", "**").replace("</b>", "**"))
        lines.append("")
    lines.append("## 教育背景")
    lines.append(c["education"].replace("<b>", "**").replace("</b>", "**")
                 .replace("<br>", "；"))
    lines += ["", "## 技能", ""]
    for k, v in c["skills"]:
        lines.append(f"- **{k}**：{v}")
    lines += ["", "## 求职说明", ""]
    lines += [f"- {n}" for n in c["notes"]]
    lines += ["", "> 本简历由本人独立撰写，项目与数据均可验证。"]
    return "\n".join(lines)


# ---------- 应用内预览：把整页模板缩放进 Streamlit ----------

RE_MEDIA = re.compile(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}")
RE_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def _scope_css(css: str, scope: str) -> str:
    """给每条选择器加作用域前缀，避免预览样式污染整个应用。

    打印用的 @media 块直接丢掉——预览不需要，留着反而会干扰页面打印。
    """
    css = RE_MEDIA.sub("", css)
    out = []
    for sel, body in RE_RULE.findall(css):
        parts = []
        for s in sel.split(","):
            s = s.strip()
            if not s:
                continue
            parts.append(scope if s == "body" else f"{scope} {s}")
        if parts:
            out.append(", ".join(parts) + " {" + body.strip() + "}")
    return "\n".join(out)


def preview_html(tpl: str = "classic", content=None, photo_uri: str = "",
                 zoom: float = 0.42, clip_height: int = 0,
                 instance: str = "") -> str:
    """把整页简历缩成可以塞进 st.html 的预览块（样式隔离）。

    这里踩过两个坑，写下来免得再犯：

    1. **缩放必须用 CSS `zoom`，不能用 `transform: scale`。**
       transform 不改变元素在文档流里的占位高度：内容真实排版高 2400+px，
       容器会照着 2400px 撑开，而视觉内容只剩 1000px —— 于是缩略图下面留一大片空白，
       三列高度还各不相同。`zoom` 会影响布局尺寸，容器自动跟着缩放后的内容走。

    2. **作用域 class 不能带点。**
       `_scope_css()` 要的是选择器前缀 `.oa-pv-classic`，但 DOM 上的 class 属性必须写
       `oa-pv-classic`。之前同一个带点字符串既当选择器又当 class 用，结果**所有预览样式
       全部匹配不上**：照片按原图 600×800 撑开、`.page` 的内边距全丢，
       这才是"排版乱 + 图片不对"的真正原因。

    3. **同一个模板在同一页出现两次时，class 必须带实例后缀。**
       `.oa-pv-classic { zoom: 0.42 }` 和 `.oa-pv-classic { zoom: 0.78 }` 是同一条规则，
       后定义的那条会同时盖住两个元素 —— 结果三列缩略里的 classic 按 0.78 渲染、
       宽度 624px 溢出到 336px 的列里被切掉，看起来就是"classic 被裁了"。
       所以每处调用传自己的 instance（页面里用 instance="grid" / "zoom"）。

    clip_height > 0 时按给定高度裁切并加底部渐隐（"统一高度对比"用），默认 0 = 完整显示。
    """
    html = render(tpl, content, photo_uri)
    css = (re.search(r"<style>(.*?)</style>", html, re.S) or [None, ""])[1]
    body = (re.search(r"<body>(.*?)</body>", html, re.S) or [None, ""])[1]
    suffix = f"-{instance}" if instance else ""
    cls = f"oa-pv-{tpl}{suffix}"
    wrap = f"oa-pv-wrap-{tpl}{suffix}"
    scoped = _scope_css(css, f".{cls}")
    w = round(800 * zoom)
    extra = (f".{wrap} {{ width: {w}px; overflow: hidden; background: #fff;"
             f" border: 1px solid #E3E7EE; border-radius: 10px;"
             f" box-shadow: 0 1px 3px rgba(16,24,40,.04); }}"
             f".{cls} {{ zoom: {zoom}; width: 800px; }}"
             f".{cls} .page {{ margin: 0; box-shadow: none; }}")
    if clip_height and clip_height > 0:
        extra += (f".{wrap} {{ height: {clip_height}px; position: relative; }}"
                  f".{wrap}::after {{ content: ''; position: absolute; left: 0; right: 0;"
                  f" bottom: 0; height: 54px; pointer-events: none;"
                  f" background: linear-gradient(rgba(255,255,255,0), #fff); }}")
    return (f"<style>{scoped}\n{extra}</style>"
            f'<div class="{wrap}"><div class="{cls}">{body}</div></div>')
