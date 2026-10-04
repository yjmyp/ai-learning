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
