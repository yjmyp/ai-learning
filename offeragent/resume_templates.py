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

# ---------- CSS ----------

CSS_CLASSIC = """
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
       color: #1F2328; margin: 0; background: #eceff3; font-size: 13px; line-height: 1.62; }
.page { width: 800px; margin: 18px auto; background: #fff; padding: 42px 50px 34px;
        box-shadow: 0 2px 14px rgba(0,0,0,.12); }
.head { display: flex; gap: 22px; align-items: flex-start; }
.head-main { flex: 1; min-width: 0; }
.photo { flex: 0 0 auto; }
.photo img { width: 104px; height: 140px; object-fit: cover; object-position: center top;
             border: 1px solid #DCE3EC; border-radius: 6px; display: block;
             box-shadow: 0 1px 3px rgba(16,24,40,.10); }
h1 { font-size: 26px; margin: 0 0 7px; letter-spacing: 1px; color: #0F172A; }
.role { display: inline-block; font-size: 12.6px; color: #1D4ED8; font-weight: 700;
        background: #EEF2FF; border-radius: 999px; padding: 2px 11px; margin-bottom: 8px; }
.meta { font-size: 12.5px; color: #4B5563; line-height: 1.8; }
.meta b { color: #111827; }
.links { font-size: 12.5px; color: #1D4ED8; margin-top: 4px; word-break: break-all; }
h2 { font-size: 14px; color: #0F172A; margin: 19px 0 8px; padding-bottom: 5px;
     border-bottom: 1px solid #E5E9F2; letter-spacing: .6px; }
h2::before { content: ''; display: inline-block; width: 4px; height: 13px;
             background: #1D4ED8; border-radius: 2px; margin-right: 8px;
             vertical-align: -1px; }
.proj { margin-bottom: 14px; }
.proj-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.proj-title { font-size: 14px; font-weight: 700; color: #0F172A; }
.proj-date { font-size: 11.5px; color: #6B7280; white-space: nowrap; }
.result { font-size: 12.6px; color: #0F5132; background: #F1F8F3; border-left: 3px solid #2F9E61;
          padding: 5px 10px; margin: 5px 0 6px; border-radius: 0 5px 5px 0; }
.tech { display: flex; flex-wrap: wrap; gap: 5px; margin: 0 0 6px; }
.chip { font-size: 11px; color: #1D4ED8; background: #F2F5FE; border: 1px solid #E1E8FA;
        border-radius: 5px; padding: 1px 7px; }
ul { margin: 2px 0 0; padding-left: 17px; }
li { margin: 3px 0; }
li::marker { color: #9AA6B8; }
.skills div { margin: 3px 0; }
.skills b { display: inline-block; min-width: 88px; color: #0F172A; }
.note { font-size: 12.2px; color: #4B5563; }
.foot { font-size: 10.5px; color: #9CA3AF; margin-top: 16px; border-top: 1px solid #EEF1F5;
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
body { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
       color: #1F2328;
       margin: 0; background: #eceff3; font-size: 12.6px; line-height: 1.6; }
.page { width: 800px; margin: 18px auto; background: #fff; display: flex;
        box-shadow: 0 2px 14px rgba(0,0,0,.12); min-height: 1060px; }
.side { width: 236px; background: #F6F8FC; padding: 32px 20px;
        border-right: 1px solid #E6EBF3; }
.main { flex: 1; padding: 32px 30px 26px; min-width: 0; }
.photo img { width: 120px; height: 158px; object-fit: cover; object-position: center top;
             margin: 0 auto 16px; display: block; background: #fff;
             border: 3px solid #fff; border-radius: 8px;
             box-shadow: 0 2px 8px rgba(16,24,40,.14); }
.side h3 { font-size: 11.5px; color: #1D4ED8; margin: 18px 0 8px; letter-spacing: 1.2px; }
.side h3::after { content: ''; display: block; height: 1px; background: #DCE4F0;
                  margin-top: 6px; }
.side .meta { font-size: 11.6px; color: #3F4756; line-height: 1.78; word-break: break-all; }
.side .meta b { color: #111827; }
.side .skill b { display: block; color: #0F172A; margin-top: 6px; font-weight: 650; }
.side .skill div { margin-bottom: 7px; }
.side ul { padding-left: 15px; margin: 3px 0; }
.side li { margin: 3px 0; font-size: 11.6px; color: #3F4756; }
h1 { font-size: 24px; margin: 0 0 4px; letter-spacing: .8px; color: #0F172A; }
.role { font-size: 13px; color: #1D4ED8; font-weight: 700; margin-bottom: 6px; }
.links { font-size: 11.6px; color: #1D4ED8; word-break: break-all; margin-bottom: 4px; }
h2 { font-size: 13.4px; color: #0F172A; margin: 17px 0 7px; padding-bottom: 4px;
     border-bottom: 1px solid #E5E9F2; letter-spacing: .5px; }
h2::before { content: ''; display: inline-block; width: 4px; height: 12px;
             background: #1D4ED8; border-radius: 2px; margin-right: 7px;
             vertical-align: -1px; }
.proj { margin-bottom: 12px; }
.proj-head { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; }
.proj-title { font-size: 13.2px; font-weight: 700; color: #0F172A; }
.proj-date { font-size: 11.2px; color: #6B7280; white-space: nowrap; }
.result { font-size: 11.6px; color: #0F5132; background: #F1F8F3; border-left: 3px solid #2F9E61;
          padding: 4px 9px; margin: 4px 0 5px; border-radius: 0 5px 5px 0; }
.tech { display: flex; flex-wrap: wrap; gap: 4px; margin: 0 0 5px; }
.chip { font-size: 10.6px; color: #1D4ED8; background: #F2F5FE; border: 1px solid #E1E8FA;
        border-radius: 5px; padding: 1px 6px; }
ul { margin: 2px 0 0; padding-left: 16px; }
li { margin: 2px 0; }
li::marker { color: #9AA6B8; }
.foot { font-size: 10.4px; color: #9CA3AF; margin-top: 14px; border-top: 1px solid #EEF1F5;
        padding-top: 6px; }
@media print {
  body { background: #fff; font-size: 10.2px; line-height: 1.36; }
  .page { width: auto; margin: 0; box-shadow: none; min-height: 0; }
  .side { width: 168px; padding: 0 10px 0 0; background: #fff;
          border-right: 1px solid #e3e7f0; }
  .main { padding: 0 0 0 12px; }
  h1 { font-size: 18px; margin-bottom: 2px; } .role { font-size: 11px; margin-bottom: 4px; }
  h2 { font-size: 11.6px; margin: 7px 0 3px; padding-bottom: 2px; }
  h2::before { height: 10px; margin-right: 5px; }
  .side h3 { font-size: 10.4px; margin: 9px 0 3px; }
  .side h3::after { margin-top: 3px; }
  .side .meta { font-size: 9.8px; line-height: 1.55; }
  .side li { font-size: 9.8px; margin: 1px 0; }
  .side .skill b { margin-top: 3px; }
  .side .skill div { margin-bottom: 4px; }
  .proj { margin-bottom: 5px; }
  .proj-title { font-size: 11.4px; }
  .result { font-size: 10px; padding: 2px 6px; margin: 2px 0 3px; }
  .tech { gap: 3px; margin-bottom: 3px; }
  .chip { font-size: 9.6px; padding: 0 5px; }
  ul { padding-left: 13px; } li { margin: 1px 0; }
  .photo img { width: 76px; height: 100px; margin-bottom: 7px; border-width: 2px; }
  .foot { margin-top: 6px; padding-top: 4px; }
}
"""

CSS_COMPACT = """
* { box-sizing: border-box; }
body { font-family: "SimSun", "Songti SC", "Noto Serif SC", serif; color: #000;
       margin: 0; background: #eee; font-size: 13px; line-height: 1.6; }
.page { width: 800px; margin: 18px auto; background: #fff; padding: 42px 50px 34px;
        box-shadow: 0 2px 12px rgba(0,0,0,.12); }
.head { display: flex; gap: 20px; align-items: flex-start; }
.head-main { flex: 1; min-width: 0; }
.photo { flex: 0 0 auto; }
.photo img { width: 96px; height: 128px; object-fit: cover; object-position: center top;
             border: 1px solid #333; display: block; }
h1 { font-size: 25px; margin: 0 0 5px; letter-spacing: 3px; }
.role { font-size: 13.4px; margin-bottom: 7px; }
.meta { font-size: 12.4px; line-height: 1.72; }
.links { font-size: 12.2px; margin-top: 3px; word-break: break-all; }
h2 { font-size: 13.8px; margin: 17px 0 7px; padding-bottom: 4px;
     border-bottom: 1px solid #000; letter-spacing: 1px; }
.proj { margin-bottom: 12px; }
.proj-head { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; }
.proj-title { font-size: 13.6px; font-weight: 700; }
.proj-date { font-size: 12px; white-space: nowrap; }
.result { font-size: 12.4px; margin: 4px 0; }
.result::before { content: '▸ '; font-weight: 700; }
.tech { font-size: 11.8px; margin: 2px 0 5px; color: #333; }
.tech .chip { background: none; border: 0; padding: 0; color: #333; font-size: 11.8px; }
.tech .chip + .chip::before { content: ' · '; color: #999; }
ul { margin: 3px 0 0; padding-left: 17px; }
li { margin: 3px 0; }
.skills div { margin: 3px 0; }
.skills b { display: inline-block; min-width: 88px; }
.foot { font-size: 11px; color: #666; margin-top: 14px; border-top: 1px solid #ddd;
        padding-top: 7px; }
@media print {
  body { background: #fff; font-size: 10.8px; line-height: 1.4; }
  .page { width: auto; margin: 0; box-shadow: none; padding: 0 10mm; }
  h1 { font-size: 19px; margin-bottom: 3px; letter-spacing: 2px; }
  .role { font-size: 11.6px; margin-bottom: 4px; }
  .meta { font-size: 10.6px; line-height: 1.5; }
  .links { font-size: 10.6px; margin-top: 2px; }
  h2 { font-size: 12.2px; margin: 8px 0 4px; padding-bottom: 3px; }
  .proj { margin-bottom: 6px; }
  .proj-title { font-size: 11.8px; }
  .result { font-size: 10.4px; margin: 2px 0 3px; }
  .tech { font-size: 10.2px; margin-bottom: 3px; }
  ul { padding-left: 14px; } li { margin: 1px 0; }
  .photo img { width: 76px; height: 101px; }
  .foot { margin-top: 6px; padding-top: 4px; }
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
