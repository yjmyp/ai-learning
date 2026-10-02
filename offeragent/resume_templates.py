# -*- coding: utf-8 -*-
"""
resume_templates · 简历排版模板
===============================
同一份内容，三种排版，随时切换：
  classic  —— 经典单栏：结果前置，从上往下扫最顺（默认）
  sidebar  —— 左侧栏：照片 / 联系方式 / 技能放左边，右边只放经历，信息密度高
  compact  —— 极简黑白：不要颜色和装饰，投偏传统团队更稳

内容来自 DEFAULT_CONTENT（改这里就等于改简历正文），照片用 base64 直接嵌进去。
"""
import base64
import re
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent

DEFAULT_CONTENT = {
    "name": "余剑",
    "role": "AI 应用开发实习生（LLM 应用 / RAG / Agent）",
    "meta": [
        "<b>南京邮电大学</b> · 网络工程 · 本科 · 2027 届（2023.09–2027.06）",
        "17578999648 ｜ yj2994762833@gmail.com ｜ 南京（南京 onsite 优先，可远程）",
        "到岗 2026.09 下旬起 · 4–5 天/周 · 可连续实习 6 个月以上（毕业可无缝转正）",
    ],
    "links": [
        ("上线项目", "https://ai-learning-fphncazxmg3pnesntwchz6.streamlit.app/"),
        ("GitHub", "https://github.com/yjmyp/ai-learning"),
    ],
    "projects": [
        {
            "title": "OfferAgent 求职智能体（自研 + 自用，持续迭代）",
            "date": "2026.09 至今",
            "result": "自研 8 工具 Agent 引擎，批量匹配实测 <b>13 岗全链路跑通（匹配分 62–88）</b>；"
                      "门禁 60 分自动拦低质量岗；多岗位泛化实测 蚂蚁 78% / 小米 72% / Calix 88%；"
                      "工具守卫 6/6 拦截全部坏调用；批量打分改线程池 3 并发，耗时降至约 1/3",
            "tech": "Python ｜ DeepSeek API ｜ Streamlit ｜ SQLite ｜ ReAct / Function Calling / 多 Agent 协作",
            "bullets": [
                "<b>自研 Agent 引擎（非框架封装）</b>：8 个工具统一 schema 注册表 + 状态对象 + "
                "ReAct 决策循环 + 预算上限防死循环；每一步写入 trace 可复盘；五类坏输出守卫"
                "（非法 JSON / 未知工具 / 缺参 / 类型错 / 非对象），错误回填后模型自动重写重试。",
                "<b>Supervisor 多 Agent 协作</b>：主管 Agent 是唯一工具入口，下辖岗位分析师 / "
                "话术专家 / 投递复盘员，职责隔离；投递工具不在子 Agent 工具集里，"
                "执行类动作 100% 停在人工确认（产品红线）。",
                "<b>质量门禁与防呆</b>：匹配分 &lt;60 输出 verdict「不建议投」；投递前自动重访岗位链接，"
                "404 / 不可达直接拦截；话术带 45+ 禁用词库防 AI 腔（v6 迭代）。",
                "<b>记忆与可观测</b>：SQLite 跨会话记忆；trace 落盘 JSONL 支持投递漏斗 / 跟进提醒 / "
                "复盘归因；生产日志可复盘——6 次真实运行 22 步全成功、话术截断自动踢回重试。",
                "<b>产品闭环</b>：自我蒸馏（15 题生成结构化画像）→ 岗位匹配 → 话术生成 → "
                "半自动投递 → 面试拷问 → 复盘写回画像，全流程自研自用。",
                "<b>工程化</b>：11 页面应用，数据 / AI / UI 三层拆分可独立测试；"
                "run_tests.py 统一测试入口 26 个测试 0 失败基线；密钥走 Secrets 不落代码。",
            ],
        },
        {
            "title": "RAG 知识库问答系统（已上线，可点开验证）",
            "date": "2026.07 – 2026.08",
            "result": "11 篇资料 → 254 块向量库；自建评估集实测 top-1 / top-3 / top-5 命中率 "
                      "<b>75% / 83% / 92%</b>，回答带引用溯源",
            "tech": "Python ｜ bge-small-zh-v1.5 ｜ Chroma ｜ FastAPI ｜ Streamlit ｜ DeepSeek API",
            "bullets": [
                "<b>独立实现端到端链路</b>：文档解析 → 分层切分（300 字/块、重叠 50、保留段落边界）"
                "→ bge 向量化 → Chroma 持久化 → top-k 召回 → TF-IDF 重排 → 带引用编号生成；"
                "不套 LangChain 封装，链路上任何一环出问题都能定位。",
                "<b>自建 12 条评估集量化检索质量</b>：逐条记录 top-1/3/5 命中，用同一套数据"
                "对比切分参数与重排策略，把「感觉还行」变成可复现的数字。",
                "<b>定位并修复真实问题</b>：切分稀释定义段导致检索漂移 → 改分层切分保留段落边界；"
                "修复嵌套 JSON 被正则截断的 bug；实现向量库离线缓存；部署 Streamlit Cloud，Git 管理。",
            ],
        },
        {
            "title": "Agent 工具调用（Function Calling 工程化）",
            "date": "2026.08",
            "result": "参数守卫拦截 <b>5 类坏调用</b>，错误回填后模型可自纠错重试",
            "tech": "Python ｜ DeepSeek API ｜ JSON 协议 / 参数合同校验",
            "bullets": [
                "实现「模型自主决定调哪个工具 → 参数校验 → 执行 → 结构化结果回填」完整链路。",
                "<b>不做 happy path</b>：参数守卫拦 5 类坏输出（未知工具 / 缺参 / 类型错 / 非对象 / "
                "非法 JSON），失败时错误回填给模型自纠错；已演进为 OfferAgent 的引擎核心。",
            ],
        },
    ],
    "education": "<b>南京邮电大学</b> ｜ 网络工程 ｜ 本科 ｜ 2027 届<br>"
                 "相关课程：计算机网络、数据结构、操作系统、数据库原理",
    "skills": [
        ("语言 / 基础", "Python、SQL、HTTP 协议、数据结构与算法"),
        ("Agent / 大模型应用", "ReAct / Reflection / Plan-and-Execute 设计模式、多 Agent 协作"
                               "（Supervisor）、Function Calling 与参数合同校验、Prompt 工程、"
                               "MCP 工具接入协议、DeepSeek API 全链路、RAG 全链路（切分 / 向量化 / "
                               "召回 / 重排 / 生成）、Chroma、检索效果评估、LoRA 等微调方式原理"),
        ("工程 / 部署", "FastAPI、Streamlit、SQLite、Git / GitHub、Docker 容器化、LangGraph 编排、"
                        "LangSmith 可观测、并发 / 异步编程、Streamlit Cloud 部署 + Secrets 管理"),
        ("工具链", "熟练使用 Codex / Cursor / Claude Code 等 AI 编程工具提效"),
    ],
    "notes": [
        "目标：AI 应用开发 / Agent 开发实习；次选大模型应用评测方向。",
        "暂无正式实习经历，作品以「自研并自用的 Agent 系统 + 可复现量化评估 + 真实 debug 记录」为主；"
        "简历每个数字、链接均可当场验证。",
    ],
}

TEMPLATES = {
    "classic": "经典单栏（推荐 · 结果前置）",
    "sidebar": "左侧栏（照片 / 技能放侧边 · 信息密度高）",
    "compact": "极简黑白（传统团队 · 去装饰）",
}

PHOTO_CANDIDATES = [
    REPO / "简历" / "照片.jpg",
    REPO / "简历" / "照片.png",
    HERE / "assets" / "avatar.png",
    HERE / "assets" / "avatar.jpg",
]


def find_photo():
    for p in PHOTO_CANDIDATES:
        if p.exists() and p.is_file():
            return p
    return None


def photo_data_uri(path=None) -> str:
    p = Path(path) if path else find_photo()
    if not p or not Path(p).exists():
        return ""
    mime = "image/png" if str(p).lower().endswith(".png") else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(Path(p).read_bytes()).decode()}"


def _photo_box(uri: str, cls: str = "photo") -> str:
    if not uri:
        return ""
    return f'<div class="{cls}"><img src="{uri}" alt="照片"></div>'


# ---------- 公用片段 ----------

def _links_html(content) -> str:
    return "<br>".join(f"{label}：{url}" for label, url in content["links"])


def _meta_html(content) -> str:
    return "<br>".join(content["meta"])


def _project_html(p, show_result=True) -> str:
    bullets = "".join(f"<li>{b}</li>" for b in p["bullets"])
    res = f'<div class="result">{p["result"]}</div>' if show_result else ""
    return (f'<div class="proj"><div class="proj-head">'
            f'<span class="proj-title">{p["title"]}</span>'
            f'<span class="proj-date">{p["date"]}</span></div>'
            f'{res}<div class="tech">{p["tech"]}</div>'
            f"<ul>{bullets}</ul></div>")


def _skills_html(content) -> str:
    return "".join(f"<div><b>{k}</b>{v}</div>" for k, v in content["skills"])


def _notes_html(content) -> str:
    return "".join(f"<li>{n}</li>" for n in content["notes"])


FOOT = '<div class="foot">本简历由本人独立撰写，项目与数据均可验证。</div>'

# ---------- CSS ----------

CSS_CLASSIC = """
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; color: #1f2328;
       margin: 0; background: #eceff3; font-size: 13px; line-height: 1.62; }
.page { width: 800px; margin: 18px auto; background: #fff; padding: 40px 48px 34px;
        box-shadow: 0 2px 14px rgba(0,0,0,.12); }
.head { display: flex; gap: 20px; align-items: flex-start; }
.head-main { flex: 1; }
.photo img { width: 104px; height: 140px; object-fit: cover;
             border: 1px solid #d8dee7; border-radius: 4px; display: block; }
h1 { font-size: 25px; margin: 0 0 4px; letter-spacing: .5px; }
.role { font-size: 14px; color: #1d4ed8; font-weight: 700; margin-bottom: 6px; }
.meta { font-size: 12.5px; color: #4b5563; line-height: 1.75; }
.meta b { color: #111827; }
.links { font-size: 12.5px; color: #1d4ed8; margin-top: 3px; word-break: break-all; }
h2 { font-size: 14.5px; color: #111827; margin: 20px 0 8px; padding-bottom: 4px;
     border-bottom: 2px solid #1d4ed8; }
.proj { margin-bottom: 15px; }
.proj-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.proj-title { font-size: 14px; font-weight: 700; }
.proj-date { font-size: 12px; color: #6b7280; white-space: nowrap; }
.result { font-size: 12.8px; color: #0f5132; background: #eaf6ef; border-left: 3px solid #2f9e61;
          padding: 5px 9px; margin: 5px 0; border-radius: 0 4px 4px 0; }
.tech { font-size: 12.2px; color: #1d4ed8; margin: 3px 0 5px; }
ul { margin: 3px 0 0; padding-left: 18px; }
li { margin: 3px 0; }
.skills div { margin: 3px 0; }
.skills b { display: inline-block; min-width: 84px; }
.note { font-size: 12.2px; color: #4b5563; }
.foot { font-size: 11px; color: #9ca3af; margin-top: 16px; border-top: 1px solid #eef1f5;
        padding-top: 8px; }
@media print {
  body { background: #fff; font-size: 10.9px; line-height: 1.42; }
  .page { width: auto; margin: 0; box-shadow: none; padding: 0 8mm; }
  h1 { font-size: 20px; margin: 0 0 2px; } .role { font-size: 12px; margin-bottom: 3px; }
  .meta { font-size: 10.6px; line-height: 1.52; } .links { font-size: 10.6px; margin-top: 2px; }
  h2 { font-size: 12.4px; margin: 6px 0 3px; padding-bottom: 2px; }
  .proj { margin-bottom: 5px; }
  .proj-title { font-size: 12.2px; }
  .result { font-size: 10.6px; padding: 2px 6px; margin: 2px 0 3px; }
  .tech { font-size: 10.4px; margin: 1px 0 2px; }
  ul { padding-left: 13px; } li { margin: 1px 0; }
  .photo img { width: 84px; height: 112px; }
  .foot { margin-top: 4px; padding-top: 4px; }
}
"""

CSS_SIDEBAR = """
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; color: #1f2328;
       margin: 0; background: #eceff3; font-size: 12.6px; line-height: 1.6; }
.page { width: 800px; margin: 18px auto; background: #fff; display: flex;
        box-shadow: 0 2px 14px rgba(0,0,0,.12); min-height: 1060px; }
.side { width: 232px; background: #f3f5fa; padding: 30px 18px; border-right: 1px solid #e3e7f0; }
.main { flex: 1; padding: 30px 30px 26px; }
.photo img { width: 120px; height: 158px; object-fit: cover; margin: 0 auto 14px;
             display: block; border: 1px solid #d8dee7; border-radius: 4px; background: #fff; }
.side h3 { font-size: 12.5px; color: #1d4ed8; margin: 16px 0 6px; letter-spacing: .4px; }
.side .meta { font-size: 11.6px; color: #3f4756; line-height: 1.7; word-break: break-all; }
.side .meta b { color: #111827; }
.side .skill b { display: block; color: #111827; margin-top: 5px; }
.side .skill div { margin-bottom: 6px; }
.side ul { padding-left: 15px; margin: 3px 0; }
.side li { margin: 3px 0; font-size: 11.6px; color: #3f4756; }
h1 { font-size: 23px; margin: 0 0 3px; }
.role { font-size: 13.4px; color: #1d4ed8; font-weight: 700; margin-bottom: 5px; }
.links { font-size: 11.6px; color: #1d4ed8; word-break: break-all; margin-bottom: 4px; }
h2 { font-size: 13.6px; color: #111827; margin: 16px 0 7px; padding-bottom: 3px;
     border-bottom: 2px solid #1d4ed8; }
.proj { margin-bottom: 13px; }
.proj-head { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; }
.proj-title { font-size: 13.4px; font-weight: 700; }
.proj-date { font-size: 11.4px; color: #6b7280; white-space: nowrap; }
.result { font-size: 11.8px; color: #0f5132; background: #eaf6ef; border-left: 3px solid #2f9e61;
          padding: 4px 8px; margin: 4px 0; border-radius: 0 4px 4px 0; }
.tech { font-size: 11.4px; color: #1d4ed8; margin: 2px 0 4px; }
ul { margin: 3px 0 0; padding-left: 17px; }
li { margin: 2px 0; }
.foot { font-size: 10.4px; color: #9ca3af; margin-top: 14px; border-top: 1px solid #eef1f5;
        padding-top: 6px; }
@media print {
  body { background: #fff; font-size: 10.6px; line-height: 1.42; }
  .page { width: auto; margin: 0; box-shadow: none; min-height: 0; }
  .side { width: 178px; padding: 0 12px 0 0; background: #fff; border-right: 1px solid #e3e7f0; }
  .main { padding: 0 0 0 14px; }
  h1 { font-size: 19px; } .role { font-size: 11.6px; }
  h2 { font-size: 12px; margin: 8px 0 4px; }
  .side h3 { font-size: 11px; margin: 10px 0 4px; }
  .proj { margin-bottom: 6px; }
  .proj-title { font-size: 11.8px; }
  .result { font-size: 10.4px; padding: 2px 6px; margin: 2px 0 3px; }
  .tech { font-size: 10.2px; }
  ul { padding-left: 13px; } li { margin: 1px 0; }
  .photo img { width: 84px; height: 110px; margin-bottom: 8px; }
}
"""

CSS_COMPACT = """
* { box-sizing: border-box; }
body { font-family: "SimSun", "Songti SC", "Microsoft YaHei", serif; color: #000;
       margin: 0; background: #eee; font-size: 13px; line-height: 1.6; }
.page { width: 800px; margin: 18px auto; background: #fff; padding: 42px 50px 34px;
        box-shadow: 0 2px 12px rgba(0,0,0,.12); }
.head { display: flex; gap: 20px; align-items: flex-start; }
.head-main { flex: 1; }
.photo img { width: 96px; height: 128px; object-fit: cover; border: 1px solid #999;
             display: block; }
h1 { font-size: 24px; margin: 0 0 4px; letter-spacing: 2px; }
.role { font-size: 13.6px; margin-bottom: 6px; }
.meta { font-size: 12.4px; line-height: 1.7; }
.links { font-size: 12.2px; margin-top: 3px; word-break: break-all; }
h2 { font-size: 14px; margin: 18px 0 7px; padding-bottom: 3px; border-bottom: 1px solid #000; }
.proj { margin-bottom: 13px; }
.proj-head { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; }
.proj-title { font-size: 13.6px; font-weight: 700; }
.proj-date { font-size: 12px; white-space: nowrap; }
.result { font-size: 12.4px; margin: 4px 0; }
.tech { font-size: 12px; margin: 2px 0 4px; }
ul { margin: 3px 0 0; padding-left: 18px; }
li { margin: 3px 0; }
.skills div { margin: 3px 0; }
.skills b { display: inline-block; min-width: 88px; }
.foot { font-size: 11px; color: #666; margin-top: 14px; border-top: 1px solid #ddd;
        padding-top: 7px; }
@media print {
  body { background: #fff; font-size: 11.2px; line-height: 1.45; }
  .page { width: auto; margin: 0; box-shadow: none; padding: 0 10mm; }
  h1 { font-size: 20px; } .role { font-size: 12px; }
  .meta { font-size: 11px; line-height: 1.55; }
  h2 { font-size: 12.6px; margin: 9px 0 5px; }
  .proj { margin-bottom: 7px; }
  .proj-title { font-size: 12.4px; }
  .result { font-size: 11px; margin: 2px 0 3px; }
  .tech { font-size: 10.8px; }
  ul { padding-left: 15px; } li { margin: 1px 0; }
  .photo img { width: 84px; height: 112px; }
}
"""

# ---------- 三个渲染器 ----------

def _doc(title: str, css: str, body: str) -> str:
    return (f'<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n'
            f"<title>{title}</title>\n<style>{css}</style>\n</head>\n<body>\n{body}\n"
            f"</body>\n</html>\n")


def render_classic(content=None, photo_uri: str = "") -> str:
    c = content or DEFAULT_CONTENT
    projects = "".join(_project_html(p) for p in c["projects"])
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


RENDERERS = {
    "classic": render_classic,
    "sidebar": render_sidebar,
    "compact": render_compact,
}


def render(tpl: str = "classic", content=None, photo_uri: str = "") -> str:
    """按模板名生成整页 HTML。photo_uri 传空字符串时不显示照片位。"""
    fn = RENDERERS.get(tpl) or render_classic
    return fn(content, photo_uri)


def render_with_photo(tpl: str = "classic", content=None, photo_path=None) -> str:
    """自动找照片（或指定路径）后渲染。"""
    return render(tpl, content, photo_data_uri(photo_path))


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
                 zoom: float = 0.5, height: int = 620) -> str:
    """生成"能直接塞进 st.html"的缩略预览：样式隔离、按比例缩小。

    zoom 用标准 transform: scale 实现（CSS zoom 在 iframe 沙盒里不生效，
    会导致整页按 800px 原宽渲染被裁成"左上角一块"）。
    """
    html = render(tpl, content, photo_uri)
    css = (re.search(r"<style>(.*?)</style>", html, re.S) or [None, ""])[1]
    body = (re.search(r"<body>(.*?)</body>", html, re.S) or [None, ""])[1]
    scope = f".oa-pv-{tpl}"
    scoped = _scope_css(css, scope)
    w = 800 * zoom
    extra = (f".oa-pv-wrap-{tpl} {{ width: {w:.0f}px; min-height: {height}px; overflow: hidden;"
             f" border: 1px solid #E3E7EE; border-radius: 10px; background: #fff; }}"
             f".oa-pv-scale-{tpl} {{ width: 800px; transform: scale({zoom}); "
             f"transform-origin: top left; }}"
             f"{scope} .page {{ margin: 0; box-shadow: none; }}")
    return (f'<style>{scoped}\n{extra}</style>'
            f'<div class="oa-pv-wrap-{tpl}"><div class="oa-pv-scale-{tpl}">{body}</div></div>')
