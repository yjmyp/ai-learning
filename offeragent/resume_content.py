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
        "电话：17578999648 ｜ 邮箱：yj2994762833@gmail.com",
        "南京（可现场 / 远程）｜ 可实习：2026.09 起，每周 4–5 天，可连续 6 个月以上",
    ],
    "links": [
        ("OfferAgent", "https://ai-learning-c62pgpcfp7us6rztelatpj.streamlit.app/"),
        ("RAG 知识库", "https://ai-learning-fphncazxmg3pnesntwchz6.streamlit.app/"),
        ("GitHub", "https://github.com/yjmyp/ai-learning"),
    ],
    "summary": "AI 应用开发方向 2027 届本科生，独立完成 2 个可上线、可量化的 LLM 应用项目："
               "Agent 工具调用与工作流（OfferAgent）、RAG 知识库问答系统。"
               "覆盖「Agent 引擎 → 检索链路 → 量化评估 → 服务化部署」完整链路，代码开源、应用可在线运行。",
    "projects": [
        {
            "title": "OfferAgent 求职智能体（个人项目，自研并已上线）",
            "date": "2026.09 – 至今",
            "result": "将匹配打分从「模型自由给分」改为五维本地加权：同一岗位重复打分标准差由 "
                      "2.36 分降至 0.00 分；工具守卫对 30 类输入的判定 30/30 正确。",
            "tech": "Python ｜ DeepSeek API ｜ Streamlit ｜ SQLite ｜ LangGraph ｜ MCP ｜ Chroma / bge 向量检索",
            "bullets": [
                "设计五维加权匹配打分：硬技能 0.30 / 项目证据 0.25 / 地点 0.15 / 时间 0.15 / "
                "门槛 0.15，每个维度输出命中与缺失证据；硬门槛自动拦截「硕士」「届别不符」"
                "「方向偏算法」类岗位，已在 22 个真实岗位上跑通全链路。",
                "实现 Plan / Reflect 增强的 ReAct 引擎：10 个工具统一 Schema 注册表 + 执行预算上限"
                "防死循环；Plan 先产出 3–6 步计划并校验工具名合法性，Reflect 收尾自评目标是否达成；"
                "对 30 类正常与异常输入做守卫评测，判定 30/30 正确，错误以结构化消息回填后模型可自纠错。",
                "实现 MCP 工具层：基于 stdio + JSON-RPC 2.0 自研服务端，对外暴露同一套 10 个工具；"
                "执行类工具（打开投递链接）标注 humanConfirm，投递动作始终由人确认。",
                "工程化：向量记忆（bge 语义召回，三档降级保证离线可用）、线程池并发批量打分、"
                "调用 trace 落盘与可视化、成本计量；应用按数据 / AI / UI 三层拆分，"
                "离线回归测试 0 失败，GitHub Actions CI 覆盖单测 / 服务验收 / 镜像构建。",
            ],
        },
        {
            "title": "RAG 知识库问答系统（已上线）",
            "date": "2026.07 – 2026.08",
            "result": "在 32 篇 / 740 块自建语料上，混合检索 R@5 达 93%、MRR 0.796、P99 延迟 69ms；"
                      "拒答门禁对库外问题的误拒率为 1%。",
            "tech": "Python ｜ bge-small-zh-v1.5 ｜ Chroma ｜ FastAPI ｜ Streamlit ｜ DeepSeek API",
            "bullets": [
                "自建 240 条评估集（200 条可回答问题逐条绑定标准答案块，40 条库外与难负例）"
                "对检索做量化评估，定位出「混合召回解决未召回到、重排解决未排到前面」的分工。",
                "实现混合检索与重排链路：BM25 + 向量 RRF 融合召回后做多特征重排，"
                "并在命中块内做句级引用定位（返回支撑答案的句子与字符偏移，前端可高亮）。",
                "实现拒答门禁与答案级自检：拒答阈值用评估集网格搜索校准；"
                "对数值型问题增加答案级自检，库外问题误拒率 1%。",
                "端到端链路自研实现（未使用 LangChain 封装）：多格式解析（txt / md / pdf / docx / "
                "html / csv / xlsx，其中 xlsx 用 zip + XML 自解析，不依赖第三方库）→ 结构感知切分 "
                "→ 向量化 → 混合召回 → 重排 → 生成。",
                "服务化与运维：FastAPI + SSE 流式输出 + API Key 鉴权 + 限流 + 存活 / 就绪探针；"
                "启动预热使首个请求从 15.3s 降至 62ms，单机压测稳态约 20 QPS，Docker 一键启动。",
            ],
        },
    ],
    "education": "<b>南京邮电大学</b> ｜ 网络工程（本科） ｜ 2023.09 – 2027.06<br>"
                 "主修课程：数据结构与算法、计算机网络、操作系统、数据库原理<br>"
                 "自学：大模型原理（Transformer / Attention）、LoRA 微调原理、Agent 设计模式与评估方法",
    "skills": [
        ("编程语言", "Python（主力，熟悉 FastAPI / Streamlit）、SQL；"
                     "数据结构与算法（哈希、双指针、滑动窗口、链表、二叉树、DFS / BFS、二分、回溯、动态规划）"),
        ("大模型应用", "RAG 全链路（文档解析 / 切分 / 向量化 / 混合召回 / 重排 / 引用生成）与检索效果评估；"
                       "Agent（ReAct、Plan-and-Execute、Reflection、多 Agent 协作）；"
                       "Function Calling 与参数校验；MCP 协议；Prompt 工程"),
        ("工程与部署", "FastAPI、Streamlit、SQLite / Chroma、Docker、Git / GitHub Actions、"
                       "SSE 流式输出、线程池并发、云端部署与密钥管理"),
        ("计算机基础", "计算机网络、操作系统、数据库原理"),
    ],
    "notes": [],
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
