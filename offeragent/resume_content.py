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
        ("OfferAgent", "https://ai-learning-c62pgpcfp7us6rztelatpj.streamlit.app/"),
        ("RAG 知识库", "https://ai-learning-fphncazxmg3pnesntwchz6.streamlit.app/"),
        ("GitHub", "https://github.com/yjmyp/ai-learning"),
    ],
    "projects": [
        {
            "title": "OfferAgent 求职智能体（自研 + 自用，持续迭代）",
            "date": "2026.09 至今",
            "result": "自研 8 工具 Agent 引擎并自用：匹配分改成<b>五维本地加权</b>后同一岗位重复打分"
                      "<b>方差 0.00</b>（模型法平均波动 3.31 分）；工具守卫 6/6 拦截全部坏调用；"
                      "硬门槛自动拦下「硕士线 / 届别不符 / 方向偏算法」，22 个真实岗位全链路跑通；"
                      "跨岗位泛化实测蚂蚁 78 / 小米 72 / Calix 88 分",
            "tech": "Python ｜ DeepSeek API ｜ Streamlit ｜ SQLite ｜ ReAct / Function Calling / 多 Agent 协作",
            "bullets": [
                "<b>自研 Agent 引擎（非框架封装）</b>：8 工具统一 Schema 注册表 + ReAct 循环 + "
                "预算上限防死循环；新增 <b>Plan / Reflect 两个节点</b>（先出 3-6 步计划并校验工具名"
                "合法性；收尾自评目标是否达成，解析失败保守兜底）；五类坏输出守卫（非法 JSON / "
                "未知工具 / 缺参 / 类型错 / 非对象）+ 错误回填自纠错。",
                "<b>工具层两种来源：内置注册表 + MCP</b>：自研 <b>MCP server</b>（stdio + JSON-RPC 2.0，"
                "暴露 10 个工具），任何支持 MCP 的客户端都能挂载；<b>执行类工具（投递）带 humanConfirm</b>，"
                "发送永远停在人确认——Supervisor 模式下投递工具不在子 Agent 工具集里。",
                "<b>匹配分结构化（可复算、可解释）</b>：把「让模型随口给分」换成<b>本地五维加权</b>"
                "（硬技能 0.30 / 项目证据 0.25 / 地点 0.15 / 时间 0.15 / 门槛 0.15），每维给出命中与缺失"
                "证据；<b>一致性评估：重复打分方差 0.00 vs 模型法 3.31 分</b>；22 岗位实测自动筛出 6 个"
                "不该投的（硕士线 / 届别不符 / 方向偏算法）。",
                "<b>记忆语义化 + 可观测</b>：事实与复盘写入<b>向量记忆</b>（bge 语义召回，支持模糊指代）；"
                "trace 落盘 JSONL + <b>可视化页</b>（工具调用分布 / 覆盖率 / 运行时间线）+ 成本计量。",
                "<b>数字分身（可面试演示）</b>：15 题自我蒸馏生成结构化画像 → 渲染为可交互分身页；"
                "HR / 考官在知情前提下点进链接，分身基于画像实时回答并展示项目证据。",
                "<b>投递流程状态机化</b>：LangGraph StateGraph 把「链接核验 → 门禁 → 话术 → 投递 → "
                "记录回写」建成显式状态机，节点可单独复用与测试；投递前自动核验 URL 拦截失效链接。",
                "<b>产品闭环</b>：自我蒸馏（15 题生成结构化画像）→ 岗位匹配 → 话术生成 → "
                "半自动投递 → 面试拷问 → 复盘写回画像，全流程自研自用。",
                "<b>工程化</b>：11 页面应用，数据 / AI / UI 三层拆分可独立测试；"
                "run_tests.py 统一测试入口 26 个测试 0 失败基线；GitHub Actions CI 三档全绿；"
                "简历 HTML / PDF / Markdown 三格式下载；密钥走 Secrets 不落代码。",
            ],
        },
        {
            "title": "RAG 知识库问答系统（已上线，可点开验证）",
            "date": "2026.07 – 2026.08",
            "result": "28 篇资料 → 622 块向量库；自建 <b>54 条评估集</b>做四模式消融，混合检索 + 重排把 "
                      "top-5 命中率从 86% 做到 <b>98%</b>（MRR 0.757→0.832）；拒答门禁使库外问题 "
                      "<b>100% 拦截</b>、误拒 2%",
            "tech": "Python ｜ bge-small-zh-v1.5 ｜ Chroma ｜ FastAPI ｜ Streamlit ｜ DeepSeek API",
            "bullets": [
                "<b>端到端链路自己实现</b>：解析（txt/md/pdf/docx/html/csv/xlsx，xlsx 手写 zip+XML "
                "解析免依赖）→ 结构感知切分 → bge 向量化 → Chroma → <b>BM25 + 向量 RRF 融合</b> → "
                "多特征重排 → <b>句级引用定位</b>（从命中块里挑出真正支撑答案的那句 + 字符偏移）。",
                "<b>评估驱动优化</b>：54 条评估集消融出「混合召回解决没召回、重排解决没排前面」的分工；"
                "<b>多查询改写实测性价比低（top-5 反降、P95 +1.2s）故不默认开</b>——取舍有数据支撑。",
                "<b>可信层</b>：拒答阈值用评估集<b>网格搜索校准</b>（库内最低覆盖率 0.211 / 库外最高 "
                "0.125 → 取 0.13）；数值型问题加答案级自检，难负例拒答 0%→100%、误拒 2%。",
                "<b>工程化交付</b>：FastAPI 服务化（SSE 流式 + X-API-Key）+ 增量索引 + trace 计量"
                "（P95 1.4s、单次成本 0.0003 元）+ Docker 一键起服务。",
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
