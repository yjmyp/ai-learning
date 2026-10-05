# 代码包：简历系统 + 应用入口（当前教学主线）

> 内容包括：简历三层（content/styles/templates）+ 简历页 + 数据层/AI层/入口。目标是让 AI 能讲透「数据与表现分离 + 注册表」模式，并带我加第 8 套模板。

## 怎么喂
把本文件全文复制给 DeepSeek，开头加一句：
> 「先读完全文代码，再按我的水平逐块讲解，一次一小步，先框架后填空，不直接给完整答案。」

## 包含的文件

| 文件 | 行数 | 说明 |
|---|---|---|
| `offeragent/resume_content.py` | 126 | 见下方代码 |
| `offeragent/resume_styles.py` | 451 | 见下方代码 |
| `offeragent/resume_templates.py` | 430 | 见下方代码 |
| `offeragent/pages_resume.py` | 305 | 见下方代码 |
| `offeragent/store.py` | 228 | 见下方代码 |
| `offeragent/llm.py` | 193 | 见下方代码 |
| `offeragent/offer_agent_app.py` | 341 | 见下方代码 |

**合计 2074 行**（约 8KB），在 DeepSeek 上下文内。

---

## ===== offeragent/resume_content.py（126 行）=====

```python
# -*- coding: utf-8 -*-
"""
resume_content · 简历内容层（数据，不含排版）
=============================================
只放「简历有什么」：正文数据 DEFAULT_CONTENT、照片素材、照片工具函数。
和样式（resume_styles.py）、模板引擎（resume_templates.py）完全分开——
改内容不用碰排版，加排版不用碰内容。这是「数据与表现分离」。
"""
import base64
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
```

## ===== offeragent/resume_styles.py（451 行）=====

```python
# -*- coding: utf-8 -*-
"""
resume_styles · 简历样式层（纯 CSS，不含内容与逻辑）
====================================================
每个模板一段 CSS 常量。新增模板 = 在这里加一段 CSS_DUO 这样的常量，
再到 resume_templates.py 注册表登记 + 写一个渲染函数，内容层不用动。
"""

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

CSS_TIMELINE = """
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
       color: #2D3748; margin: 0; background: #eceff3; font-size: 13px; line-height: 1.62; }
.page { width: 800px; margin: 18px auto; background: #fff; padding: 44px 52px 34px;
        box-shadow: 0 2px 14px rgba(0,0,0,.12); }
.head { display: flex; gap: 22px; align-items: flex-start; margin-bottom: 10px; }
.head-main { flex: 1; min-width: 0; }
.photo { flex: 0 0 auto; }
.photo img { width: 100px; height: 134px; object-fit: cover; object-position: center top;
             border: 1px solid #E2E8F0; border-radius: 8px; display: block;
             box-shadow: 0 2px 8px rgba(16,24,40,.10); }
h1 { font-size: 27px; margin: 0 0 6px; letter-spacing: 1px; color: #111827; }
.role { display: inline-block; font-size: 12.6px; color: #047857; font-weight: 700;
        background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 999px;
        padding: 2px 11px; margin-bottom: 8px; }
.meta { font-size: 12.4px; color: #4B5563; line-height: 1.8; }
.meta b { color: #111827; }
.links { font-size: 12.4px; color: #047857; margin-top: 4px; word-break: break-all; }
h2 { font-size: 14.5px; color: #111827; margin: 22px 0 12px; letter-spacing: .6px; }
h2::before { content: ''; display: inline-block; width: 5px; height: 14px;
             background: #10B981; border-radius: 2px; margin-right: 9px;
             vertical-align: -1px; }
/* ---- 时间轴 ---- */
.tl { position: relative; padding-left: 26px; }
.tl::before { content: ''; position: absolute; left: 7px; top: 4px; bottom: 4px;
              width: 2px; background: #D1FAE5; border-radius: 2px; }
.tl-item { position: relative; margin-bottom: 15px; }
.tl-item::before { content: ''; position: absolute; left: -26px; top: 5px;
                   width: 12px; height: 12px; border-radius: 50%;
                   background: #10B981; border: 3px solid #D1FAE5; }
.tl-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.tl-title { font-size: 14px; font-weight: 700; color: #111827; }
.tl-date { font-size: 11.5px; color: #6B7280; white-space: nowrap; }
.result { font-size: 12.6px; color: #065F46; background: #F0FDF4; border-left: 3px solid #10B981;
          padding: 5px 10px; margin: 5px 0 6px; border-radius: 0 5px 5px 0; }
.tech { display: flex; flex-wrap: wrap; gap: 5px; margin: 0 0 6px; }
.chip { font-size: 11px; color: #047857; background: #ECFDF5; border: 1px solid #BBF7D0;
        border-radius: 5px; padding: 1px 7px; }
ul { margin: 2px 0 0; padding-left: 17px; }
li { margin: 3px 0; }
li::marker { color: #9AA6B8; }
.skills div { margin: 3px 0; }
.skills b { display: inline-block; min-width: 88px; color: #111827; }
.note { font-size: 12.2px; color: #4B5563; }
.foot { font-size: 10.5px; color: #9CA3AF; margin-top: 16px; border-top: 1px solid #EEF1F5;
        padding-top: 8px; }
@media print {
  body { background: #fff; font-size: 10.9px; line-height: 1.42; }
  .page { width: auto; margin: 0; box-shadow: none; padding: 0 8mm; }
  h1 { font-size: 20px; margin: 0 0 2px; } .role { font-size: 12px; margin-bottom: 3px; }
  .meta { font-size: 10.6px; line-height: 1.52; } .links { font-size: 10.6px; margin-top: 2px; }
  h2 { font-size: 12.4px; margin: 8px 0 5px; }
  .tl { padding-left: 18px; } .tl::before { left: 5px; }
  .tl-item::before { left: -18px; width: 9px; height: 9px; border-width: 2px; }
  .tl-item { margin-bottom: 6px; }
  .tl-title { font-size: 12.2px; }
  .result { font-size: 10.6px; padding: 2px 6px; margin: 2px 0 3px; }
  .tech { font-size: 10.4px; margin: 1px 0 2px; }
  ul { padding-left: 13px; } li { margin: 1px 0; }
  .photo img { width: 80px; height: 107px; }
  .foot { margin-top: 4px; padding-top: 4px; }
}
"""

CSS_BAND = """
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
       color: #1F2937; margin: 0; background: #E8EDF3; font-size: 13px; line-height: 1.62; }
.page { width: 800px; margin: 18px auto; background: #fff; padding: 0 0 30px;
        box-shadow: 0 2px 14px rgba(0,0,0,.12); }
.band { background: linear-gradient(120deg, #0F172A 0%, #1E3A5F 55%, #2563EB 100%);
        color: #fff; padding: 34px 48px 30px; display: flex; gap: 22px; align-items: center; }
.band-main { flex: 1; min-width: 0; }
.band h1 { font-size: 28px; margin: 0 0 7px; letter-spacing: 1.5px; color: #fff; }
.band .role { display: inline-block; font-size: 12.6px; font-weight: 700;
              background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.35);
              border-radius: 999px; padding: 2px 12px; margin-bottom: 9px; color: #fff; }
.band .meta { font-size: 12.6px; color: #CBD5E1; line-height: 1.8; }
.band .meta b { color: #fff; }
.band .links { font-size: 12.6px; color: #93C5FD; margin-top: 4px; word-break: break-all; }
.photo { flex: 0 0 auto; }
.photo img { width: 96px; height: 128px; object-fit: cover; object-position: center top;
             border: 3px solid #fff; border-radius: 8px; display: block;
             box-shadow: 0 4px 14px rgba(0,0,0,.28); }
.body { padding: 0 48px; }
h2 { font-size: 14px; color: #0F172A; margin: 20px 0 9px; letter-spacing: .6px; }
h2::before { content: ''; display: inline-block; width: 4px; height: 13px;
             background: #2563EB; border-radius: 2px; margin-right: 8px;
             vertical-align: -1px; }
.proj { margin-bottom: 13px; background: #F8FAFC; border: 1px solid #E9EEF5;
        border-left: 3px solid #2563EB; border-radius: 8px; padding: 10px 14px; }
.proj-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.proj-title { font-size: 14px; font-weight: 700; color: #0F172A; }
.proj-date { font-size: 11.5px; color: #6B7280; white-space: nowrap; }
.result { font-size: 12.6px; color: #1D4ED8; background: #EFF6FF; border-radius: 5px;
          padding: 5px 10px; margin: 6px 0; }
.tech { display: flex; flex-wrap: wrap; gap: 5px; margin: 0 0 6px; }
.chip { font-size: 11px; color: #1E40AF; background: #E0EDFF; border: 1px solid #BFDBFE;
        border-radius: 999px; padding: 1px 9px; }
ul { margin: 2px 0 0; padding-left: 17px; }
li { margin: 3px 0; }
li::marker { color: #9AA6B8; }
.skills div { margin: 3px 0; }
.skills b { display: inline-block; min-width: 88px; color: #0F172A; }
.note { font-size: 12.2px; color: #4B5563; }
.foot { font-size: 10.5px; color: #9CA3AF; margin: 18px 48px 0; border-top: 1px solid #EEF1F5;
        padding-top: 8px; }
@media print {
  body { background: #fff; font-size: 10.8px; line-height: 1.4; }
  .page { width: auto; margin: 0; box-shadow: none; }
  .band { padding: 0 0 10px; background: #fff; color: #000; border-bottom: 2px solid #111; }
  .band h1 { color: #000; font-size: 21px; margin-bottom: 2px; }
  .band .role { background: #fff; border: 1px solid #333; color: #000; font-size: 11px;
                margin-bottom: 3px; }
  .band .meta { color: #333; font-size: 10.4px; line-height: 1.5; }
  .band .meta b { color: #000; }
  .band .links { color: #333; font-size: 10.4px; }
  .body { padding: 0; }
  h2 { font-size: 12.2px; margin: 8px 0 4px; }
  .proj { margin-bottom: 6px; padding: 6px 8px; }
  .proj-title { font-size: 12px; }
  .result { font-size: 10.4px; padding: 2px 6px; margin: 3px 0; }
  .tech { margin-bottom: 3px; }
  .chip { font-size: 9.6px; }
  ul { padding-left: 13px; } li { margin: 1px 0; }
  .photo img { width: 72px; height: 96px; border: 1px solid #ccc; }
  .foot { margin: 8px 0 0; padding-top: 4px; }
}
"""

CSS_MODERN = """
* { box-sizing: border-box; }
body { font-family: "Inter", "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
       color: #334155; margin: 0; background: #EEF1F6; font-size: 13px; line-height: 1.6; }
.page { width: 800px; margin: 18px auto; background: #fff; padding: 46px 54px 34px;
        box-shadow: 0 2px 14px rgba(0,0,0,.10); }
.head { display: flex; gap: 22px; align-items: flex-start; margin-bottom: 6px; }
.head-main { flex: 1; min-width: 0; }
.photo { flex: 0 0 auto; }
.photo img { width: 108px; height: 142px; object-fit: cover; object-position: center top;
             border-radius: 12px; display: block; box-shadow: 0 4px 12px rgba(16,24,40,.14); }
h1 { font-size: 32px; margin: 0 0 4px; letter-spacing: .5px; font-weight: 800; color: #0F172A; }
.role { font-size: 13.4px; font-weight: 600; color: #6366F1; margin-bottom: 7px; }
.meta { font-size: 12.4px; color: #475569; line-height: 1.8; }
.meta b { color: #0F172A; }
.links { font-size: 12.4px; color: #6366F1; margin-top: 3px; word-break: break-all; }
h2 { font-size: 13.2px; color: #0F172A; margin: 20px 0 10px; letter-spacing: 1.6px;
     text-transform: uppercase; }
h2::before { content: ''; display: inline-block; width: 22px; height: 3px;
             background: linear-gradient(90deg, #6366F1, #A5B4FC); border-radius: 2px;
             margin-right: 8px; vertical-align: 2px; }
.proj { margin-bottom: 13px; border: 1px solid #E8EDF5; border-radius: 10px;
        padding: 11px 15px; background: #FCFCFF; }
.proj-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.proj-title { font-size: 14px; font-weight: 700; color: #0F172A; }
.proj-date { font-size: 11.5px; color: #94A3B8; white-space: nowrap; }
.result { font-size: 12.6px; color: #4F46E5; margin: 5px 0 6px; }
.tech { display: flex; flex-wrap: wrap; gap: 5px; margin: 0 0 6px; }
.chip { font-size: 10.8px; color: #4F46E5; background: #EEF2FF; border-radius: 6px;
        padding: 2px 8px; font-weight: 600; }
ul { margin: 2px 0 0; padding-left: 17px; }
li { margin: 3px 0; }
li::marker { color: #A5B4FC; }
.skills { display: flex; flex-wrap: wrap; gap: 8px; }
.skills .skill-tag { background: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 999px;
                     padding: 4px 12px; font-size: 12px; color: #334155; }
.skills .skill-tag b { color: #0F172A; }
.skills .skill-tag b::after { content: '：'; color: #94A3B8; font-weight: 400; }
.note { font-size: 12.2px; color: #475569; }
.foot { font-size: 10.5px; color: #9CA3AF; margin-top: 18px; border-top: 1px solid #EEF1F5;
        padding-top: 8px; }
@media print {
  body { background: #fff; font-size: 10.8px; line-height: 1.42; }
  .page { width: auto; margin: 0; box-shadow: none; padding: 0 8mm; }
  h1 { font-size: 22px; margin-bottom: 2px; }
  .role { font-size: 12px; margin-bottom: 3px; }
  .meta { font-size: 10.5px; line-height: 1.52; } .links { font-size: 10.5px; }
  h2 { font-size: 11.4px; margin: 8px 0 4px; }
  .proj { margin-bottom: 6px; padding: 6px 9px; }
  .proj-title { font-size: 12px; }
  .result { font-size: 10.4px; margin: 2px 0 3px; }
  .tech { margin-bottom: 3px; }
  .chip { font-size: 9.4px; }
  ul { padding-left: 13px; } li { margin: 1px 0; }
  .skills { gap: 4px; }
  .skills .skill-tag { padding: 2px 8px; font-size: 9.8px; }
  .photo img { width: 82px; height: 108px; }
  .foot { margin-top: 6px; padding-top: 4px; }
}
"""

# ============================================================
# 新模板：双栏均衡（duo）—— 欧美简历最常见布局
# 左栏 62% 放项目经历（信息主体），右栏 38% 放照片/联系/技能/教育。
# 强调色用青蓝（#0E7490），跟现有模板的蓝/绿/紫区分开。
# ============================================================
CSS_DUO = """
* { box-sizing: border-box; }
body { font-family: "Inter", "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
       color: #1F2937; margin: 0; background: #E9EDF2; font-size: 12.6px; line-height: 1.6; }
.page { width: 800px; margin: 18px auto; background: #fff; display: flex;
        box-shadow: 0 2px 14px rgba(0,0,0,.12); min-height: 1080px; }
.main { flex: 0 0 62%; padding: 36px 26px 28px 36px; min-width: 0; }
.side { flex: 1; background: #F4F7FA; padding: 36px 22px 26px; min-width: 0;
        border-left: 1px solid #E2E8F0; }
.photo { margin-bottom: 14px; }
.photo img { width: 128px; height: 168px; object-fit: cover; object-position: center top;
             border-radius: 10px; display: block; box-shadow: 0 4px 12px rgba(16,24,40,.12); }
h1 { font-size: 28px; margin: 0 0 4px; letter-spacing: .5px; color: #0F172A; }
.role { font-size: 12.8px; font-weight: 600; color: #0E7490; margin-bottom: 8px; }
.main h2 { font-size: 14px; color: #0F172A; margin: 20px 0 9px; letter-spacing: 1.2px;
           text-transform: uppercase; }
.main h2::after { content: ''; display: block; width: 34px; height: 2px;
                  background: #0E7490; margin-top: 4px; }
.side h3 { font-size: 11px; color: #0E7490; margin: 20px 0 7px; letter-spacing: 1.6px;
           text-transform: uppercase; }
.side h3::after { content: ''; display: block; height: 1px; background: #D7E2EC;
                  margin-top: 5px; }
.side .meta { font-size: 11.4px; color: #3F4756; line-height: 1.75; word-break: break-all; }
.side .meta b { color: #111827; }
.side .links { font-size: 11.2px; color: #0E7490; word-break: break-all; margin-bottom: 6px; }
.side ul { padding-left: 14px; margin: 3px 0; }
.side li { margin: 3px 0; font-size: 11.2px; color: #3F4756; }
.side .skill b { display: block; color: #0F172A; margin-top: 7px; font-weight: 650; }
.side .skill div { margin-bottom: 6px; }
.proj { margin-bottom: 14px; }
.proj-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.proj-title { font-size: 13.4px; font-weight: 700; color: #0F172A; }
.proj-date { font-size: 11px; color: #6B7280; white-space: nowrap; }
.result { font-size: 12px; color: #065F46; background: #F0FDF4; border-left: 3px solid #0E7490;
          padding: 4px 9px; margin: 5px 0 6px; border-radius: 0 5px 5px 0; }
.tech { display: flex; flex-wrap: wrap; gap: 4px; margin: 0 0 6px; }
.chip { font-size: 10.4px; color: #0E7490; background: #EDF7FA; border: 1px solid #C9E7F0;
        border-radius: 999px; padding: 1px 8px; }
ul { margin: 2px 0 0; padding-left: 16px; }
li { margin: 3px 0; }
li::marker { color: #94A3B8; }
.note { font-size: 11.6px; color: #475569; }
.foot { font-size: 10.2px; color: #9CA3AF; margin: 18px 0 0; border-top: 1px solid #EEF1F5;
        padding-top: 6px; }
@media print {
  body { background: #fff; font-size: 10.4px; line-height: 1.4; }
  .page { width: auto; margin: 0; box-shadow: none; min-height: 0; }
  .main { padding: 0 12px 0 0; }
  .side { padding: 0 0 0 14px; background: #fff; border-left: 1px solid #dde3ec; }
  h1 { font-size: 21px; margin-bottom: 2px; }
  .role { font-size: 11px; margin-bottom: 4px; }
  .main h2 { font-size: 11.8px; margin: 9px 0 4px; }
  .main h2::after { width: 24px; margin-top: 2px; }
  .side h3 { font-size: 9.8px; margin: 11px 0 3px; }
  .side .meta { font-size: 9.6px; line-height: 1.55; }
  .side li { font-size: 9.6px; margin: 1px 0; }
  .side .skill b { margin-top: 4px; }
  .side .skill div { margin-bottom: 4px; }
  .proj { margin-bottom: 6px; }
  .proj-title { font-size: 11.6px; }
  .result { font-size: 10px; padding: 2px 6px; margin: 2px 0 3px; }
  .tech { margin-bottom: 3px; }
  .chip { font-size: 9.2px; padding: 0 6px; }
  ul { padding-left: 13px; } li { margin: 1px 0; }
  .photo img { width: 84px; height: 110px; margin-bottom: 6px; }
  .foot { margin: 8px 0 0; padding-top: 4px; }
}
"""
```

## ===== offeragent/resume_templates.py（430 行）=====

```python
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


def render_timeline(content=None, photo_uri: str = "") -> str:
    """时间线式：项目沿纵向时间线排，经历占比最大。"""
    c = content or DEFAULT_CONTENT
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
    body = f"""<div class="page">
  <div class="main">
    <h1>{c["name"]}</h1>
    <div class="role">{c["role"]}</div>
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
```

## ===== offeragent/pages_resume.py（305 行）=====

```python
# -*- coding: utf-8 -*-
"""简历页域：简历内容管理 / 模板选择 / 照片 / ATS 定制 —— 从 pages_more.py 拆出。

拆出来的原因（也是分层思路）：
- pages_more.py 原来 36KB 装 8 个页面，简历相关（内容/模板/照片/定制）自成一块。
- 简历页只依赖「内容层(resume_templates) + 工具层(store/llm/ui_kit/doc_io/resume_builder…)」，
  和拷问/投递记录等其他页面没有互相调用 —— 拆开互不影响。
"""
import streamlit as st

from store import *
from llm import *
from ui_kit import *
from pages_twin import find_avatar
import doc_io
import resume_builder
import resume_clean
import resume_tailor
import resume_templates


def _render_pdf_bytes(tpl: str) -> bytes | None:
    """本地无头 Edge 渲染 PDF；云端等无 Edge 环境返回 None（按钮降级为提示）。"""
    try:
        import make_resume_pdf as mk
        tmp = mk.RESUME_DIR / "_dl_tmp.pdf"
        mk.html_to_pdf(resume_templates.render_with_photo(tpl), tmp)
        data = tmp.read_bytes()
        tmp.unlink(missing_ok=True)
        return data
    except Exception:
        return None


def resume_source_panel(prefix: str) -> str:
    """简历来源统一面板（导入文件 / 问答生成 / 手动编辑）。返回当前简历全文。

    prefix 用来隔离不同页面的控件 key，避免重复元素 ID。
    """
    key = f"{prefix}_text"
    if key not in st.session_state:
        st.session_state[key] = load_my_resume()

    src = st.radio("简历从哪来",
                   ["📎 导入文件（PDF / Word / 图片 / 文本）",
                    "💬 问答式生成一份", "✍️ 手动编辑"],
                   horizontal=True, key=f"{prefix}_src")

    if "导入" in src:
        st.caption("支持 PDF、Word(.docx)、txt/md，以及简历截图（离线 OCR 识别，约 5-15 秒）。")
        up = st.file_uploader("选择简历文件",
                              type=["pdf", "docx", "txt", "md", "png", "jpg",
                                    "jpeg", "webp", "bmp"],
                              key=f"{prefix}_up")
        if up is not None and st.button("读取这个文件", key=f"{prefix}_read"):
            with st.spinner("读取中…"):
                try:
                    out = doc_io.read_any(up.getvalue(), up.name)
                except Exception as e:
                    out = {"text": "", "method": "失败", "warning": str(e)}
            if out["text"]:
                st.session_state[key] = out["text"]
                st.success(f"读取成功：{out['method']}，{len(out['text'])} 字")
            if out.get("warning"):
                st.warning(out["warning"])
            if not out["text"]:
                st.error("没读到文字。可以改用截图上传，或手动粘贴。")
            st.rerun()
    elif "问答" in src:
        rb = resume_builder.load()
        done, total = resume_builder.progress(rb)
        st.progress(done / total,
                    text=(f"第 {done + 1} / {total} 题" if done < total else "全部答完"))
        q = resume_builder.current(rb)
        if q:
            st.markdown(f"**{q['q']}**")
            st.caption("为什么问这个 / 怎么答有用：" + q["why"])
            if q["k"] == "photo":
                # 照片这一题直接给上传按钮，比让人打字有用
                up_photo = st.file_uploader("上传照片（jpg / png / webp）",
                                            type=["jpg", "jpeg", "png", "webp"],
                                            key=f"{prefix}_rb_photo")
                if up_photo is not None:
                    st.image(up_photo.getvalue(), width=140, caption="预览")
                    if st.button("✅ 用这张照片", type="primary",
                                 key=f"{prefix}_rb_photo_save"):
                        dst = resume_builder.save_photo(up_photo.getvalue())
                        resume_builder.answer(rb, f"已上传：{dst.name}")
                        st.rerun()
                c1, c2 = st.columns(2)
                if c1.button("没有照片，跳过这题", key=f"{prefix}_rb_skip"):
                    resume_builder.answer(rb, "无")
                    st.rerun()
                if c2.button("重新开始", key=f"{prefix}_rb_reset"):
                    resume_builder.reset()
                    st.rerun()
            else:
                val = st.text_area("你的回答", rb["answers"].get(q["k"], ""),
                                   key=f"{prefix}_rb_{q['k']}", height=100)
                c1, c2, c3 = st.columns(3)
                if c1.button("提交，下一题", type="primary", key=f"{prefix}_rb_next"):
                    resume_builder.answer(rb, val)
                    st.rerun()
                if c2.button("跳过这题", key=f"{prefix}_rb_skip"):
                    resume_builder.answer(rb, "")
                    st.rerun()
                if c3.button("重新开始", key=f"{prefix}_rb_reset"):
                    resume_builder.reset()
                    st.rerun()
        else:
            st.caption("答完了。生成草稿后，空着的字段会明确列出来，不会替你编。")
            if st.button("📝 生成简历草稿（调用 DeepSeek）", type="primary",
                         key=f"{prefix}_rb_build"):
                with st.spinner("整理中…"):
                    try:
                        draft = resume_builder.build(rb, lambda p: ask_chat(p))
                        (DATA_DIR / "resume_draft.md").write_text(draft, encoding="utf-8")
                        st.session_state[key] = draft
                        st.session_state[f"{prefix}_draft"] = draft
                    except Exception as e:
                        st.error(str(e))
            if st.session_state.get(f"{prefix}_draft"):
                with st.expander("看生成的草稿", expanded=True):
                    st.markdown(st.session_state[f"{prefix}_draft"])

    return st.text_area("简历全文（可编辑）", height=280, key=key)


def page_my_resume():
    """我的简历：管理简历内容本身（不针对具体岗位）。"""
    hero("我的简历", "导入 / 问答生成 / 手动编辑。保存后用于 ATS 覆盖检查和面试准备")
    saved = MY_RESUME_PATH.exists()
    if saved:
        st.success(f"已保存到 {MY_RESUME_PATH.name}（{len(read_text(MY_RESUME_PATH))} 字）")
    else:
        st.info("还没保存过。下面是仓库里已有的简历，改完点保存就会变成「我的简历」。")
    text = resume_source_panel("my")
    c1, c2 = st.columns([1, 3])
    if c1.button("💾 保存为我的简历", type="primary", key="my_save"):
        cleaned, rep = save_my_resume(text)
        st.success(f"已保存（{len(cleaned)} 字）")
        if rep:
            st.warning("顺手清掉了这些不该出现在简历里的东西："
                       + "、".join(f"{name}×{n}" for name, n, _ in rep))
            with st.expander("看被删掉的原文片段"):
                for name, n, sample in rep:
                    st.caption(f"{name} ×{n}　例：{sample}")
        else:
            st.caption("文本检查通过：没有本地路径 / 编码乱码。")
        next_step("resume_saved")
    c2.caption("保存位置：简历/我的简历.md　·　投递里的「简历定制」默认读这份")

    st.markdown("---")
    st.markdown("#### 📷 简历照片")
    st.caption("照片会出现在：打印版简历的右上角、以及公开名片页的头像。"
               "传一次就够，后面所有模板共用这一张。")
    ph1, ph2 = st.columns([1, 3], vertical_alignment="center")
    _ph = find_avatar()
    with ph1:
        if _ph:
            st.image(str(_ph), width=130, caption=f"当前：{_ph.name}")
        else:
            st.markdown(
                '<div style="width:130px;height:130px;border-radius:50%;'
                'background:linear-gradient(135deg,#5558D6,#1B2A4A);color:#fff;'
                'display:flex;align-items:center;justify-content:center;'
                'font-size:44px;font-weight:700;">余</div>',
                unsafe_allow_html=True)
            st.caption("还没有照片")
    with ph2:
        up_img = st.file_uploader("上传照片（jpg / png / webp，竖版证件照最好）",
                                  type=["jpg", "jpeg", "png", "webp"], key="photo_up")
        if up_img is not None:
            st.image(up_img.getvalue(), width=120, caption="预览")
            if st.button("✅ 用这张照片", type="primary", key="photo_save"):
                dst = resume_builder.save_photo(up_img.getvalue())
                st.success(f"已保存到 {dst.name}")
                st.rerun()
        st.caption("保存位置：简历/照片.jpg　·　想让云端名片也有头像，"
                   "把这张图提交到 GitHub（`git add 简历/照片.jpg && git commit && git push`）")

    st.markdown("---")
    st.markdown("#### 🎨 简历模板")
    st.caption("同一份内容，**七套不同布局的整体模板**（不是小改版，是结构不同的七种简历）。"
               "下面是模板卡片墙：每张卡片 = 一套模板的**版式缩略**，点「选用」切换；"
               "下载按钮对应**选中的那套**（照片自动嵌入）。")
    tpl_labels = list(resume_templates.TEMPLATES.values())
    tpl_keys = list(resume_templates.TEMPLATES.keys())
    _pv_photo = resume_templates.photo_data_uri()
    st.caption(f"模板引擎版本 `{resume_templates.build_tag()}`"
               "（这个指纹和云端不一致 = 云端还在跑旧代码，去 Manage app → Reboot）")

    # 记忆上次选的模板（刷新不丢）
    tpl_key = st.session_state.get("tpl_pick_key", "classic")
    if tpl_key not in tpl_keys:
        tpl_key = "classic"

    # ---- 模板卡片墙：4 列排开，卡片 = 版式缩略 + 描述 + 选用按钮 ----
    st.markdown("###### 选一套模板（点卡片下的「选用」）")
    for row in range(0, len(tpl_keys), 4):
        cols = st.columns(4)
        for _k, col in zip(tpl_keys[row:row + 4], cols):
            with col:
                st.html(resume_templates.preview_html(
                    _k, photo_uri=_pv_photo, zoom=0.20, instance=f"card_{_k}"))
                _active = (_k == tpl_key)
                if st.button(
                        f"选用「{_k}」",
                        key=f"tpl_card_{_k}",
                        type="primary" if _active else "secondary",
                        use_container_width=True):
                    st.session_state["tpl_pick_key"] = _k
                    st.rerun()
                st.caption(resume_templates.TEMPLATE_DESC.get(_k, ""))

    # ---- 选中的那套：放大看整页 ----
    st.markdown("---")
    st.markdown(f"###### 放大看「**{tpl_key}**」整页（跟我打印出来的一致）")
    st.html(resume_templates.preview_html(tpl_key, photo_uri=_pv_photo,
                                          zoom=0.78, instance="zoom"))

    # ---- 每套完整预览（不裁切，能完整看排版）----
    with st.expander("每套模板的完整预览（跟打印稿同一套排版，完整显示不裁切）"):
        for _k in tpl_keys:
            st.markdown(f"**{_k}**　—　{resume_templates.TEMPLATE_DESC.get(_k, '')}")
            st.html(resume_templates.preview_html(_k, photo_uri=_pv_photo,
                                                  zoom=0.42, instance=f"full_{_k}"))

    st.markdown("---")
    _html = resume_templates.render_with_photo(tpl_key)
    _md = resume_templates.to_markdown()
    _pdf_bytes = _render_pdf_bytes(tpl_key)
    t1, t2, t3 = st.columns([1, 1, 1])
    t1.download_button("⬇️ 下载 HTML", data=_html.encode("utf-8"),
                       file_name=f"余剑-简历-{tpl_key}.html", mime="text/html",
                       key="tpl_dl_html")
    if _pdf_bytes:
        t2.download_button("⬇️ 下载 PDF（含照片）", data=_pdf_bytes,
                           file_name=f"余剑-简历-{tpl_key}.pdf",
                           mime="application/pdf", key="tpl_dl_pdf")
    else:
        t2.caption("PDF 需本地生成（云端无 Edge）\n"
                   f"终端跑：`python offeragent\\make_resume_pdf.py "
                   f"--template {tpl_key}`")
    t3.download_button("⬇️ 下载 Markdown（可编辑）", data=_md.encode("utf-8"),
                       file_name="余剑-简历.md", mime="text/markdown",
                       key="tpl_dl_md")
    st.caption("HTML = 双击 → Ctrl+P 也能存 PDF；PDF = 高保真、照片已嵌入、实测 1 页；"
               "Markdown = 纯文本，可贴进 BOSS/邮件正文或继续改。")


def page_resume_tailor(embedded: bool = False):
    """按 JD 定制简历 + ATS 关键词覆盖检查。"""
    if not embedded:
        hero("简历定制", "按目标岗位检查关键词覆盖，并给重排与改写建议（只重排已有经历，不编）")
    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    if not jobs:
        st.info("先到「找工作 → 岗位库」添加岗位")
        return
    name = st.selectbox("目标岗位", [j[0] for j in jobs], key="tailor_pick")
    jd = read_text(JDS_DIR / f"{name}.txt")
    st.caption("这一步只做检查、不改内容。简历正文和模板在左边「简历内容 / 模板 / 照片」里管理。")
    resume = resume_source_panel("tailor")

    if st.button("🔬 检查覆盖 + 给建议（调用 DeepSeek）", type="primary", key="tailor_run"):
        if not resume.strip():
            st.warning("简历内容为空")
            return
        resume, _rep = resume_clean.clean(resume)
        if _rep:
            st.caption("已自动清掉 " + "、".join(f"{n}×{c}" for n, c, _ in _rep)
                       + "（本地路径/编码乱码，不属于简历内容）")
        with st.spinner("抽取 JD 关键词 + 本地比对 + 生成建议…"):
            try:
                out = resume_tailor.tailor(resume, jd, lambda p: ask_chat(p))
                st.session_state["tailor_out"] = out
                next_step("ats_done")
            except Exception as e:
                st.error(str(e))

    out = st.session_state.get("tailor_out")
    if not out:
        return
    st.metric("关键词覆盖率", f"{out['rate']}%",
              help="已覆盖算 1 分、部分覆盖算 0.5 分。这是本地字符串比对的结果，不是模型判断。")
    miss = [r for r in out["coverage"] if r["status"] == "缺失"]
    part = [r for r in out["coverage"] if r["status"] == "部分覆盖"]
    c1, c2 = st.columns(2)
    c1.metric("缺失关键词", len(miss))
    c2.metric("部分覆盖", len(part))
    with st.expander("看完整覆盖表（关键词 / 状态 / 类别）", expanded=True):
        for r in out["coverage"]:
            tag = {"已覆盖": "oa-tag-green", "部分覆盖": "oa-tag-amber",
                   "缺失": "oa-tag-red"}.get(r["status"], "oa-tag-blue")
            st.markdown(f'<span class="oa-tag {tag}">{r["status"]}</span> '
                        f'**{r["keyword"]}**　<span style="color:#94A3B8">{r["category"]}</span>',
                        unsafe_allow_html=True)
    if miss:
        st.warning("缺失的关键词：" + "、".join(r["keyword"] for r in miss)
                   + "　→ 简历里没有的不要硬写，先确认你是不是真的做过")
    for key, title in [("reorder.md", "重排建议"), ("bullets.md", "改写建议")]:
        if out["advice"].get(key):
            st.markdown(f"### {title}")
            st.markdown(out["advice"][key])
```

## ===== offeragent/store.py（228 行）=====

```python
# -*- coding: utf-8 -*-
"""
store.py —— OfferAgent 数据层（2026-09-29 从 offer_agent_app.py 抽出）
============================================================================
纯 Python 逻辑，不依赖 streamlit，可独立测试：
  岗位库读写（meta 权威源）、简历读写、日志读取、分数对账（单一权威源）、投递防抖。
"""
import json
import os
import re
import time
from pathlib import Path

import resume_clean

try:
    from jd_fetcher import fetch_jd
    FETCHER_OK = True
except Exception:
    FETCHER_OK = False

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
JDS_DIR = DATA_DIR / "jds"
MATCH_DIR = DATA_DIR / "match_results"
PROFILE_PATH = DATA_DIR / "profile.md"
ME_PATH = BASE_DIR / "me.txt"
CONFIG_PATH = DATA_DIR / "config.json"
TALKQ_PATH = DATA_DIR / "talk_queue.json"
USAGE_PATH = DATA_DIR / "usage.json"
META_SUFFIX = ".meta.json"
MY_RESUME_PATH = BASE_DIR.parent / "简历" / "我的简历.md"
REPORTS_DIR = DATA_DIR / "reports"


def ensure_dirs():
    for d in (DATA_DIR, JDS_DIR, MATCH_DIR):
        d.mkdir(parents=True, exist_ok=True)


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default


def write_text(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def load_my_resume() -> str:
    """读「我的简历」：优先读 简历/我的简历.md，没有就退回仓库里已有的简历。"""
    if MY_RESUME_PATH.exists():
        return resume_clean.clean(read_text(MY_RESUME_PATH))[0]
    for cand in [BASE_DIR.parent / "简历" / "余剑-简历-AI应用开发实习.md",
                 BASE_DIR.parent / "简历" / "余剑-简历-AI应用开发实习-v2.md"]:
        if cand.exists():
            return resume_clean.clean(read_text(cand))[0]
    return ""


def save_my_resume(text: str) -> tuple:
    """保存「我的简历」。顺手清掉本地路径乱码，返回 (干净文本, 清洗报告)。"""
    cleaned, report = resume_clean.clean((text or "").strip())
    MY_RESUME_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_text(MY_RESUME_PATH, cleaned + "\n")
    return cleaned, report


def load_meta(name: str) -> dict:
    p = JDS_DIR / (name + META_SUFFIX)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_meta(name: str, meta: dict):
    (JDS_DIR / (name + META_SUFFIX)).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_jobs() -> list:
    """返回 [(name, meta, jd_text)]，按状态排序：待投 → 已投 → 排除"""
    jobs = []
    for p in sorted(JDS_DIR.glob("*.txt")):
        name = p.stem
        meta = load_meta(name)
        meta.setdefault("name", name)
        meta.setdefault("company", "")
        meta.setdefault("city", "")
        meta.setdefault("status", "待投")
        meta.setdefault("match_score", None)
        meta.setdefault("excluded_reason", "")
        meta.setdefault("created_at", "")
        meta.setdefault("source_url", "")
        jobs.append((name, meta, read_text(p)))
    order = {"待投": 0, "已投": 1, "排除": 2}
    jobs.sort(key=lambda x: (order.get(x[1]["status"], 9), -(x[1]["match_score"] or 0)))
    return jobs


def detect_network_exclude(jd_text: str):
    """检测 JD 是否「专门点名要求网络工程专业」。返回 (原因, 命中原文)。"""
    patterns = [
        r"专业要求[^\n]*网络工程",
        r"专业[：:][^\n]*网络工程",
        r"网络工程[^\n]*等相关专业",
        r"计算机、软件工程、网络工程",
        r"（?网络工程）?[、，]?人工智能等相关专业",
    ]
    for pat in patterns:
        m = re.search(pat, jd_text)
        if m:
            evidence = m.group(0).strip()
            return ("JD 专业要求点名「网络工程」，非纯 AI 应用岗方向，自动排除",
                    evidence[:80])
    return None, ""


def save_new_job(name: str, city: str, jd_text: str, source_url: str = "",
                 extra: dict = None) -> str:
    """新增/更新岗位；返回提示信息"""
    name = re.sub(r"[\\/:*?\"<>|]", "_", name.strip())
    if not name:
        return "岗位名不能为空"
    ensure_dirs()
    write_text(JDS_DIR / f"{name}.txt", jd_text.strip())
    meta = load_meta(name)
    meta["name"] = name
    meta["city"] = city.strip()
    meta.setdefault("status", "待投")
    meta.setdefault("match_score", None)
    meta.setdefault("created_at", time.strftime("%Y-%m-%d"))
    if source_url:
        meta["source_url"] = source_url
    if extra:
        meta.update(extra)
    reason, evidence = detect_network_exclude(jd_text)
    if reason:
        meta["status"] = "排除"
        meta["excluded_reason"] = reason
        meta["excluded_evidence"] = evidence
    elif meta.get("excluded_reason") and meta["status"] == "排除":
        meta["status"] = "待投"
        meta["excluded_reason"] = ""
        meta["excluded_evidence"] = ""
    save_meta(name, meta)
    return f"已保存：{name}（{'自动排除：' + reason if reason else '待投'}）"


# ============================================================
# 日志与单一权威源（2026-09-29 新增）
# ============================================================
def read_logs() -> list:
    """读 Agent 运行日志（事件流，append-only）。"""
    p = DATA_DIR / "agent_logs.jsonl"
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").strip().splitlines():
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out


def audit_scores() -> list:
    """单一权威源对账：meta（权威）vs 日志（历史事件）。
    返回 [(公司, meta分数, 日志最新分数, 一致?, 说明)]。
    规则：岗位库 meta.match_score 是唯一权威；日志只记事件，历史分数是快照，不覆盖岗位库。
    """
    logs = read_logs()
    latest = {}
    for l in logs:
        comp = l.get("company") or l.get("job")
        if comp and l.get("match_score") is not None:
            latest[comp] = l["match_score"]      # 文件有序，最后一条 = 最新事件
    rows = []
    for name, meta, _jd in list_jobs():
        comp = meta.get("company") or name
        m = meta.get("match_score")
        lg = latest.get(comp) or latest.get(name)
        if m is None and lg is None:
            rows.append((comp, None, None, True, "未匹配（两者皆无）"))
        elif m is None:
            rows.append((comp, None, lg, False, "日志有事件分但岗位库未回填——以岗位库为准，重跑批量匹配可修复"))
        elif lg is None:
            rows.append((comp, m, None, True, "岗位库有分，日志无事件（正常，日志只记事件）"))
        elif m == lg:
            rows.append((comp, m, lg, True, "一致"))
        else:
            rows.append((comp, m, lg, False, "不一致：岗位库为权威（重跑匹配更新），日志为历史快照"))
    return rows


# ============================================================
# 投递防抖（2026-09-29 新增：P3-⑪ 批量连发保护）
# ============================================================
def check_apply_allowed(name: str, meta: dict) -> dict:
    """投递防抖：已投 / 24 小时内投过 → 拦截。返回 {"allowed": bool, "reason": str}。"""
    if meta.get("status") == "已投":
        return {"allowed": False, "reason": f"{name} 已标记「已投」，禁止重复投递"}
    t = meta.get("last_apply_time", "")
    if t:
        try:
            last = time.mktime(time.strptime(t[:19], "%Y-%m-%d %H:%M:%S"))
            if time.time() - last < 86400:
                return {"allowed": False,
                        "reason": f"{name} 24 小时内已发起过投递（{t}），防重复连发"}
        except Exception:
            pass
    return {"allowed": True, "reason": ""}


def mark_applied(name: str, meta: dict) -> dict:
    """标记已投：写 status + last_apply_time（防抖依据）。"""
    meta["status"] = "已投"
    meta["applied_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    meta["last_apply_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_meta(name, meta)
    return meta
```

## ===== offeragent/llm.py（193 行）=====

```python
# -*- coding: utf-8 -*-
"""
llm.py —— OfferAgent AI 调用层（2026-09-29 从 offer_agent_app.py 抽出）
============================================================================
API Key 解析、每日额度保护、模型调用、匹配报告解析。不依赖页面。
"""
import json
import os
import re
import time

import requests
import streamlit as st

from store import CONFIG_PATH, USAGE_PATH, read_text, write_text

API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
MODEL_OPTIONS = ["deepseek-chat", "deepseek-v4-flash"]


def get_api_key() -> str:
    try:
        k = st.secrets.get("DEEPSEEK_API_KEY", "")
        if k:
            return k
    except Exception:
        pass
    k = os.environ.get("DEEPSEEK_API_KEY", "")
    if k:
        return k
    cfg = read_text(CONFIG_PATH, "{}")
    try:
        k = json.loads(cfg).get("api_key", "")
        if k:
            return k
    except Exception:
        pass
    # 本地 CLI 回退：local_key.py（与 offer_agent_core / batch_score 同一来源）
    try:
        from local_key import API_KEY
        if API_KEY:
            return API_KEY
    except Exception:
        pass
    return ""


def get_model() -> str:
    cfg = read_text(CONFIG_PATH, "{}")
    try:
        return json.loads(cfg).get("model", DEFAULT_MODEL)
    except Exception:
        return DEFAULT_MODEL


def daily_limit() -> int:
    """每天允许的模型调用次数上限（防公开链接被人刷费用）。
    优先级：Secrets 的 DAILY_CALL_LIMIT > 环境变量 > 本地 config.json > 默认 200。"""
    raw = ""
    try:
        raw = st.secrets.get("DAILY_CALL_LIMIT", "")
    except Exception:
        raw = ""
    if not raw:
        raw = os.environ.get("DAILY_CALL_LIMIT", "")
    if not raw:
        try:
            raw = json.loads(read_text(CONFIG_PATH, "{}")).get("daily_call_limit", "")
        except Exception:
            raw = ""
    try:
        n = int(raw)
        return n if n > 0 else 0        # 0 = 不限（明确设 0 才关闭保护）
    except Exception:
        return 200


def _usage_today() -> dict:
    """今天的调用计数，按日期自动归零。"""
    today = time.strftime("%Y-%m-%d")
    try:
        u = json.loads(read_text(USAGE_PATH, "{}"))
    except Exception:
        u = {}
    if not isinstance(u, dict) or u.get("date") != today:
        u = {"date": today, "calls": 0}
    return u


def _bump_usage() -> int:
    u = _usage_today()
    u["calls"] = int(u.get("calls", 0)) + 1
    try:
        USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        write_text(USAGE_PATH, json.dumps(u, ensure_ascii=False))
    except Exception:
        pass
    return u["calls"]


def usage_left() -> tuple:
    """返回 (今天剩余次数, 上限)。上限为 0 表示不限。"""
    lim = daily_limit()
    used = int(_usage_today().get("calls", 0))
    if lim <= 0:
        return (-1, 0)
    return (max(lim - used, 0), lim)


def ask_model(messages: list, model: str = None) -> str:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("未配置 API Key：请到「设置」页填入 DeepSeek API Key")
    lim = daily_limit()
    used = int(_usage_today().get("calls", 0))
    if used >= lim:
        raise RuntimeError(
            f"今天的模型调用额度已用完（上限 {lim} 次）。这是防止公开链接被人刷费用的保护。"
            f"要放宽就把 Secrets / 设置里的 DAILY_CALL_LIMIT 调大，或者明天再用。")
    _bump_usage()
    model = model or get_model()
    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages},
        timeout=120,
    )
    if resp.status_code != 200:
        try:
            err = resp.json().get("error", {}).get("message", resp.text[:200])
        except Exception:
            err = resp.text[:200]
        raise RuntimeError(f"API 错误（{resp.status_code}）：{err}")
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"响应解析失败：{str(data)[:200]}")


def ask_chat(prompt: str, *materials: str, model: str = None) -> str:
    messages = [{"role": "user", "content": prompt}]
    for m in materials:
        if m and m.strip():
            messages.append({"role": "user", "content": m})
    return ask_model(messages, model)


def extract_score(report: str) -> int:
    m = re.search(r"匹配度[:：]?\s*(\d{1,3})\s*%", report)
    if m:
        return min(100, max(0, int(m.group(1))))
    return None


def parse_report(report: str) -> dict:
    """把匹配报告解析成结构化小节：{'匹配点': [...], '差距': [...], ...}"""
    sections = {}
    current = None
    for line in report.splitlines():
        m = re.match(r"^#+\s*(匹配点|差距|短板与风险|短板|结论|同类岗位对比建议|维度评分)",
                     line.strip())
        if m:
            current = m.group(1)
            sections[current] = []
            continue
        if current and line.strip():
            items = sections[current]
            if line.strip().startswith(("-", "•", "*")):
                items.append(line.strip().lstrip("-•* ").strip())
            else:
                if items:
                    items[-1] = items[-1] + " " + line.strip()
                else:
                    items.append(line.strip())
    return sections


def extract_dim_scores(report: str) -> dict:
    """从「维度评分」小节提取五维分数 {维度: 分数}"""
    m = re.search(r"##\s*维度评分\s*\n(.*)", report)
    if not m:
        return {}
    line = m.group(1).strip().splitlines()[0] if m.group(1).strip() else ""
    dims = {}
    for part in line.replace("，", " ").replace(",", " ").split():
        part = part.strip()
        mm = re.match(r"([\u4e00-\u9fa5A-Za-z]+)\s*[:：]\s*(\d{1,3})", part)
        if mm:
            dims[mm.group(1)] = min(100, max(0, int(mm.group(2))))
    return dims
```

## ===== offeragent/offer_agent_app.py（341 行）=====

```python
# -*- coding: utf-8 -*-
"""
OfferAgent · 求职智能体 Web 应用（v2 · 联网版）
================================================
余剑 2027 届 ｜ 南京邮电大学 · 网络工程
v2 升级：① 岗位库支持 URL 一键联网抓取 JD（jd_fetcher）② 话术自然口语化（双版本）
         ③ 匹配报告结构化卡片渲染 + 视觉升级

本地运行：  streamlit run offer_agent_app.py
部署：      Streamlit Cloud，API Key 放 Secrets（DEEPSEEK_API_KEY）
"""
import json
import os
import re
import time
from pathlib import Path

import requests
import streamlit as st

import plotly.graph_objects as go

try:
    from jd_fetcher import fetch_jd
    FETCHER_OK = True
except Exception:
    FETCHER_OK = False

# ============================================================
# 常量与路径
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
JDS_DIR = DATA_DIR / "jds"
MATCH_DIR = DATA_DIR / "match_results"
PROFILE_PATH = DATA_DIR / "profile.md"
ME_PATH = BASE_DIR / "me.txt"
CONFIG_PATH = DATA_DIR / "config.json"
TALKQ_PATH = DATA_DIR / "talk_queue.json"
USAGE_PATH = DATA_DIR / "usage.json"
META_SUFFIX = ".meta.json"
MY_RESUME_PATH = BASE_DIR.parent / "简历" / "我的简历.md"

API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
MODEL_OPTIONS = ["deepseek-chat", "deepseek-v4-flash"]

# ============================================================
# 提示词（2026-09-27 起抽到 prompts.py 统一管理）
# ============================================================
from prompts import (  # noqa: E402
    BANNED_PHRASES,
    PROMPT_ADVICE,
    PROMPT_HIGHLIGHT,
    PROMPT_MATCH,
    PROMPT_PROFILE,
    TALK_VARIANTS,
    build_talk_prompt,
    check_talk,
    generate_talk,
)

import distill  # noqa: E402  自我蒸馏模块（4 轮问答 → 4 份档案）
import apply_assist  # noqa: E402  投递辅助（打开页面 / 写剪贴板 / 记录投递）
import job_sources  # noqa: E402  联网搜岗（牛客 / 实习僧 / BOSS）
import distill_chat  # noqa: E402  问答式自我蒸馏（对话形态）
import theme  # noqa: E402  界面样式（v4 专业版）
import job_quality  # noqa: E402  岗位质量检查（假岗/僵尸岗识别）
import resume_tailor  # noqa: E402  简历定制 + ATS 覆盖检查
import interview_drill  # noqa: E402  面试拷问
import pipeline  # noqa: E402  投递漏斗 / 跟进提醒 / 被拒归因
import inbox_parse  # noqa: E402  邮件/消息 → 状态识别
import v41  # noqa: E402  v4.1 增强（批量匹配/链接检测/漏斗图/三件套/面试提醒/密码门）
import digital_twin  # noqa: E402  数字分身（自我介绍/反问/扮演我/复盘进化/岗位雷达）
import company_lookup  # noqa: E402  公司速查
import job_detail  # noqa: E402  岗位档案与筛选依据
import doc_io  # noqa: E402  文档/图片读取（PDF / Word / 图片 OCR）
import resume_builder  # noqa: E402  问答式生成简历
import resume_clean  # noqa: E402  简历文本清洗（剔除本地路径 / 编码乱码）
import resume_templates  # noqa: E402  简历排版模板（classic / sidebar / compact）

REPORTS_DIR = DATA_DIR / "reports"

# ============================================================
# 页面域模块（2026-09-29 拆分，减小单文件体积）
# ============================================================
from pages_home import *
from pages_work import *
from pages_match import *
from pages_more import *
from pages_resume import *
from pages_agent import *
from pages_apply import *
from pages_twin import *

# ============================================================
# 分层重构（2026-09-29）：数据层 store / AI 层 llm / 渲染层 ui_kit
# ============================================================
from store import (ensure_dirs, read_text, write_text, load_my_resume, save_my_resume,
                   load_meta, save_meta, list_jobs, save_new_job, detect_network_exclude,
                   read_logs, audit_scores, check_apply_allowed, mark_applied)
from llm import (get_api_key, get_model, daily_limit, usage_left, ask_model, ask_chat,
                 extract_score, parse_report, extract_dim_scores)
from ui_kit import (NEXT_HINTS, next_step, score_color, score_gauge, dim_radar, rank_bar,
                    inject_css, hero, status_tag, render_section_cards, render_job_detail)

# 云端持久化（Streamlit Cloud 无持久磁盘）：有 GITHUB_PAT 且岗位库为空 → 启动时自动拉取
if os.environ.get("GITHUB_PAT") and not (DATA_DIR / "jds").exists():
    try:
        from sync_data import pull
        pull()
        st.caption("已从私有仓库恢复岗位数据")
    except Exception as _e:
        st.warning(f"数据同步跳过：{_e}")


# ============================================================
# 页面：今日行动（行动导向首屏）
# ============================================================
def page_today_hub():
    """今天：要做什么 + 做得怎么样。统计放进同一页的第二个页签，口径只有这一处。"""
    t1, t2 = st.tabs(["行动清单", "数据与日志"])
    with t1:
        page_today()
    with t2:
        page_data_log()


def page_interview():
    """面试：被拷问 → 让分身陪练 → 复盘写回画像。三件事一个闭环。"""
    t1, t2, t3 = st.tabs(["面试拷问", "分身陪练", "复盘入库"])
    profile = read_text(PROFILE_PATH) or read_text(ME_PATH)
    with t1:
        page_drill()
    with t2:
        twin_practice_section(profile)
    with t3:
        twin_review_section(profile)


def build_pages():
    """注册所有页面（侧边栏按分区显示）。返回 dict 给 st.navigation。

    注意：Streamlit 侧边栏最多直接显示 10 个页面，多的会被折叠成「View more」。
    核心 10 页 + 第 11 页「Agent 流程」（引擎接入）——折叠进 View more 不影响使用。
    """
    profile = read_text(PROFILE_PATH) or read_text(ME_PATH)
    spec = [
        ("主线", [
            ("today", "今天（行动 + 数据）", "🚀", page_today_hub, True),
        ]),
        ("找工作", [
            ("jobs", "岗位库", "🔎", page_jobs, False),
            ("match", "匹配分析", "🎯", page_match, False),
            ("resume", "简历（模板 / 照片 / 覆盖）", "📄", page_resume, False),
            ("apply", "投递台", "✉️", page_apply_desk, False),
            ("records", "投递记录", "📋", page_applications, False),
            ("agent", "Agent 流程（引擎演示）", "🤖", page_agent, False),
        ]),
        ("我的", [
            ("distill", "自我蒸馏", "🧬", distill_section, False),
            ("interview", "面试准备（拷问 / 陪练 / 复盘）", "🎤", page_interview, False),
        ]),
        ("对外", [
            ("show", "名片与分享", "📇", page_show, False),
        ]),
        ("其它", [
            ("settings", "设置", "⚙️", page_settings, False),
        ]),
    ]
    sections, flat = {}, {}
    for section, items in spec:
        pages = []
        for key, title, icon, fn, is_default in items:
            pg = st.Page(fn, title=title, icon=icon,
                         url_path=key, default=is_default)
            pages.append(pg)
            flat[key] = pg
        sections[section] = pages
    PAGES.clear()
    PAGES.update(flat)
    return sections


def page_resume():
    """简历：一个页面装两件事——内容/模板/照片 + 按岗位的覆盖检查。"""
    t1, t2 = st.tabs(["简历内容 / 模板 / 照片", "按岗位检查覆盖（ATS）"])
    with t1:
        page_my_resume()
    with t2:
        page_resume_tailor(embedded=True)

# ============================================================
# 页面：Agent 流程（引擎接入 —— 模型自主规划工具链）
# ============================================================
def pipeline_bar():
    """顶部流程条：一行看完自己在哪一步（不抢统计页的活）。"""
    jobs = list_jobs()
    total = len(jobs)
    matched = sum(1 for _, m, _ in jobs if m.get("match_score") is not None)
    applied = sum(1 for _, m, _ in jobs
                  if m["status"] in ("已投", "面试中", "已拒", "Offer"))
    replied = sum(1 for _, m, _ in jobs
                  if m["status"] in ("面试中", "已拒", "Offer"))
    try:
        tgt = int(json.loads(read_text(CONFIG_PATH, "{}")).get("daily_target", 3) or 3)
    except Exception:
        tgt = 3
    today = apply_assist.applied_today()
    st.markdown(
        f'<div class="oa-flow">'
        f'<span class="oa-flow-step">① 找岗 <b>{total}</b></span>'
        f'<span class="oa-flow-arrow">→</span>'
        f'<span class="oa-flow-step">② 跑过匹配 <b>{matched}</b></span>'
        f'<span class="oa-flow-arrow">→</span>'
        f'<span class="oa-flow-step">③ 已投 <b>{applied}</b></span>'
        f'<span class="oa-flow-arrow">→</span>'
        f'<span class="oa-flow-step">④ 有回应 <b>{replied}</b></span>'
        f'<span class="oa-flow-today">今天 {today} / {tgt}'
        f'{"　✅ 达标" if today >= tgt else "　还差 " + str(tgt - today) + " 家"}</span>'
        f'</div>', unsafe_allow_html=True)


def _is_cloud() -> bool:
    """粗判是否跑在 Streamlit Community Cloud（云端仓库挂在 /mount/src 下）。"""
    try:
        return str(BASE_DIR).replace("\\", "/").startswith("/mount/src")
    except Exception:
        return False


def check_auth():
    """L1 密码门：配置了密码才启用；未配置 = 本地开发免登录。"""
    pw = ""
    try:
        pw = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        pass
    if not pw:
        pw = os.environ.get("APP_PASSWORD", "")
    pw_hash = ""
    if not pw:
        try:
            _c = json.loads(read_text(CONFIG_PATH, "{}"))
            pw_hash = _c.get("app_password_hash", "") or ""
        except Exception:
            pass
    if not pw and not pw_hash:
        if _is_cloud():
            st.error("⚠️ 这个应用跑在公网，但没有设置访问密码。任何拿到链接的人都能用你的 "
                     "DeepSeek Key 花钱。请到 Manage app → Settings → Secrets 加一行：\n\n"
                     "```toml\nAPP_PASSWORD = \"你自己的密码\"\n```\n\n"
                     "保存后应用会自动重启，刷新本页就会出现密码框。")
        return
    if st.session_state.get("auth_ok"):
        return
    st.title("🔒 OfferAgent")
    st.caption("这个应用设置了访问密码（部署时在 Secrets 填 APP_PASSWORD，"
               "或在本机「设置」页设置）。")
    guess = st.text_input("访问密码", type="password", key="auth_pw")
    if st.button("进入", type="primary", key="auth_go"):
        ok = False
        if pw and guess == pw:
            ok = True
        elif pw_hash and v41.hash_password(guess) == pw_hash:
            ok = True
        if ok:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("密码不对")
    st.stop()


def main():
    _twin = "1" in str(st.query_params.get("twin", ""))
    theme_names = list(theme.THEMES.keys())
    st.set_page_config(
        page_title="余剑 · AI 求职数字名片" if _twin else "OfferAgent · 求职智能体",
        page_icon="🪞" if _twin else "🎯",
        layout="wide", initial_sidebar_state="expanded")
    if _twin:
        # 名片页也要套主题样式，否则会是 Streamlit 默认长相
        try:
            _tcfg = json.loads(read_text(CONFIG_PATH, "{}"))
        except Exception:
            _tcfg = {}
        _tn = _tcfg.get("theme") or theme_names[0]
        inject_css(_tn if _tn in theme_names else theme_names[0])
        ensure_dirs()
        page_twin_portal()
        return
    check_auth()
    # 主题：存在 data/config.json 的 theme 字段里
    try:
        _cfg = json.loads(read_text(CONFIG_PATH, "{}"))
    except Exception:
        _cfg = {}
    theme_now = _cfg.get("theme") or theme_names[0]
    if theme_now not in theme_names:
        theme_now = theme_names[0]
    inject_css(theme_now)
    ensure_dirs()

    # 原生多页导航：侧边栏自动生成「分区 + 页」两级结构，每页有真实 URL
    pg = st.navigation(build_pages(), position="sidebar")

    with st.sidebar:
        st.divider()
        picked_theme = st.selectbox("界面风格（可切换对比）", theme_names,
                                    index=theme_names.index(theme_now),
                                    key="theme_pick")
        if picked_theme != theme_now:
            _cfg["theme"] = picked_theme
            write_text(CONFIG_PATH, json.dumps(_cfg, ensure_ascii=False, indent=2))
            st.rerun()
        jobs_all = list_jobs()
        pending_n = sum(1 for _, m, _ in jobs_all if m["status"] == "待投")
        applied_n = sum(1 for _, m, _ in jobs_all if m["status"] == "已投")
        st.markdown(
            f'<div class="oa-side-stat">待投 <b>{pending_n}</b>　已投 <b>{applied_n}</b>'
            f'<br>今天已投 <b>{apply_assist.applied_today()}</b></div>',
            unsafe_allow_html=True,
        )
        _left, _lim = usage_left()
        st.caption("今天模型调用：**不限**" if _lim <= 0
                   else f"今天模型调用：**{_lim - _left} / {_lim}** 次")

    # 流程条贴在每个页面上方；设置页不需要
    if pg.url_path != "settings":
        pipeline_bar()
        st.divider()
    pg.run()
    pending = st.session_state.pop("_pending_hint", "")
    if pending:
        st.success("✅ " + pending)


if __name__ == "__main__":
    main()
```
