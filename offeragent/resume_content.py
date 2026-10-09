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
    "role": "求职意向：AI 应用开发实习生（Agent 开发 / RAG 检索）",
    "meta": [
        "<b>南京邮电大学</b> · 网络工程 · 本科 · 2027 届（2023.09–2027.06）",
        "电话：17578999648 ｜ 邮箱：yj2994762833@gmail.com ｜ 南京",
    ],
    "links": [
        # 只放"陌生人点开就能看"的链接（判断依据是笔记里的自检项"上线链接能打开、能演示吗"）：
        #  1) 根链接有访问密码墙，面试官看到的是密码输入框 → 换成免密数字名片页（?twin=1），
        #     点开就是画像 + 预设问题，可以直接对着问；简历里绝不写密码（简历会外传，等于没设）。
        #  2) RAG 云端部署已崩（点开是 Traceback，比没链接更糟）→ 不放，
        #     它的可验证性由 GitHub 上的评估集与压测报告承担。
        ("GitHub（代码 / 评估集 / 压测报告）", "https://github.com/yjmyp/ai-learning"),
        ("OfferAgent 数字名片（免密，可直接提问）",
         "https://ai-learning-c62pgpcfp7us6rztelatpj.streamlit.app/?twin=1"),
    ],
    "summary": "独立完成两个自研项目：Agent 工具调用与工作流引擎（OfferAgent）、RAG 检索问答服务；"
               "均带自建评估集、压测报告与部署脚本，代码与评估数据在 GitHub 仓库。",
    "projects": [
        {
            "title": "OfferAgent 求职工作台（独立开发，持续迭代）",
            "date": "2026.09 – 至今",
            "intro": "面向求职场景的一站式工作台：将「自我画像 → 岗位筛选 → 匹配打分 → 投递话术 → 投递记录 → "
                     "面试复盘」串成完整链路，替代手工筛岗与逐条撰写话术。",
            "result": "匹配打分由「模型自由给分」改为五维本地加权：同一岗位重复打分标准差从 2.36 分降至 "
                      "0.00 分；22 个真实岗位中自动拦下 8 个不该投的（方向偏算法 5 / 学历要求硕士 2 / 届别不符 1）。",
            "tech": "Python ｜ DeepSeek API ｜ Streamlit ｜ SQLite ｜ LangGraph ｜ MCP ｜ Chroma / bge 向量检索",
            "bullets": [
                "打分从不可复现改为可复算：五维加权（硬技能 0.30 / 项目证据 0.25 / 地点 0.15 / 时间 0.15 / "
                "门槛 0.15），每维输出命中与缺失证据；同一岗位重复打分标准差由 10 分降至 0.00。",
                "工具调用容错：10 个工具统一 Schema 注册表 + Plan / Reflect 节点，对 30 类正常与异常输入"
                "（非法 JSON / 未知工具 / 缺参 / 类型错 / 非对象 / 大小写与空白变体）守卫判定 30/30 正确；"
                "错误以结构化消息回填，模型自行修正重试。",
                "外发动作可控：自研 MCP 服务端（stdio + JSON-RPC 2.0，暴露同一套 10 个工具）；执行类工具标注 "
                "humanConfirm，投递动作始终由人确认；投递前重访岗位链接拦截失效岗位。",
                "全链路闭环：15 题自我蒸馏产出结构化画像 → 岗位匹配 → 话术生成 → 半自动投递 → 面试复盘，"
                "LangGraph 状态图串联各节点，节点可单独测试。",
                "对外 API 层（Java/SpringBoot 3 + JDK 21 + MySQL + Redis + Docker）：岗位数据从 JSON 迁到 "
                "MySQL（JPA + HikariCP，岗位名主键保证导入幂等），热点查询走 Redis 缓存，同一请求第二次耗时"
                "从 464ms 降到 51ms；Redis 计数器按「API Key 哈希 + IP」限流（超限返回 429 + Retry-After）。",
                "API 安全与可观测：Spring Security + API Key 鉴权（fail closed，缺 Key 返回 503，定长比较"
                "防时序攻击）；AI 请求转发 Python 服务（连接 3s / 读 60s 分别配超时），下游 4xx 透传状态码；"
                "Micrometer + Prometheus 暴露缓存命中率等指标；Testcontainers 集成测试真起 MySQL/Redis 容器"
                "（本地无 Docker 自动跳过），共 19 个单元 / 集成测试 0 失败。",
                "工程化：bge 向量记忆（三档降级保证离线可用）、线程池并发批量打分、调用 trace 落盘与可视化、"
                "Token 与成本计量；11 个页面按数据 / AI / UI 三层拆分，离线回归测试 0 失败，"
                "CI 覆盖单测 / 服务验收 / 镜像构建。",
            ],
        },
        {
            "title": "RAG 检索问答服务（独立开发）",
            "date": "2026.07 – 2026.08",
            "intro": "面向私有资料的检索问答服务：文档入库后按语义检索并带引用回答，"
                     "检索质量以自建评估集量化验证。",
            "result": "在 33 篇 / 740 块语料、240 条自建评估集上做两档消融（质量指标两次跑批一致）："
                      "混合检索 R@5 93% / MRR 0.796；加多特征重排（默认档）R@5 95% / MRR 0.856。",
            "tech": "Python ｜ bge-small-zh-v1.5 ｜ Chroma ｜ FastAPI ｜ Streamlit ｜ DeepSeek API",
            "bullets": [
                "重排收益与代价量化：同一份 240 条评估集上，重排将 R@5 从 93% 提至 95%、MRR 从 0.796 提至 "
                "0.856，代价是检索 P95 从约 60ms 升至约 85ms（质量指标两次跑批一致）——故默认开启重排。",
                "可信拒答：避免「词都命中但答案不存在」仍作答，拒答阈值在评估集上网格搜索校准，数值型问题"
                "追加答案级自检；库外问题误拒率 2%。",
                "链路自研（未套 LangChain）：多格式解析（txt / md / pdf / docx / html / csv / xlsx，xlsx 用 "
                "zip + XML 自解析）→ 结构感知切分 → 向量化 → BM25 与向量 RRF 融合召回 → 多特征重排 → "
                "句级引用定位（返回支撑句与字符偏移）。",
                "服务化与运维：FastAPI + SSE 流式 + API Key 鉴权 + 限流 + 存活 / 就绪探针；启动预热将首个请求"
                "从 15.3s 降至 62ms；按来源增量重建（改一篇只重算一篇）；trace 计量延迟与单次成本"
                "（约 0.0003 元）；单机压测稳态约 20 QPS，Docker 一键启动。",
            ],
        },
    ],
    "education": "<b>南京邮电大学</b> ｜ 网络工程（本科） ｜ 2023.09 – 2027.06<br>"
                 "主修课程：数据结构与算法、计算机网络、操作系统、数据库原理<br>"
                 "拓展学习：大模型原理（Transformer / Attention）、LoRA 微调原理、Agent 设计模式与评估方法",
    "skills": [
        ("编程语言", "Python（主力，熟悉 FastAPI / Streamlit）、Java（SpringBoot 3 + REST 接口开发，JDK 21）、SQL；"
                     "数据结构与算法（哈希、双指针、滑动窗口、链表、二叉树、DFS / BFS、二分、回溯、动态规划）"),
        ("大模型应用", "RAG 全链路（文档解析 / 切分 / 向量化 / 混合召回 / 重排 / 引用生成）与检索效果评估；"
                       "Agent（ReAct、Plan-and-Execute、Reflection、多 Agent 协作）；"
                       "Function Calling 与参数校验；MCP 协议；Prompt 工程"),
        ("工程与部署", "FastAPI、Streamlit、SQLite / Chroma、Docker、Git / GitHub Actions、"
                       "SSE 流式输出、线程池并发、云端部署与密钥管理、"
                       "AI 辅助开发工具链（Codex / Cursor / Claude Code）"),
        ("后端与数据（Java）", "SpringBoot 3 / JDK 21、Spring Data JPA + Hibernate、MySQL（建表与索引、"
                              "连接池 HikariCP、只读事务）、Redis（缓存 TTL、固定窗口限流）、"
                              "REST 接口设计与入参校验、Spring Security API Key 鉴权、"
                              "Micrometer + Prometheus 指标、Testcontainers 集成测试、"
                              "Docker 多阶段构建与 compose 编排、Maven"),
        ("计算机基础", "计算机网络、操作系统、数据库原理"),
    ],
    "notes": [
        "技术笔记：持续维护技术学习笔记（Agent 框架对比、Plan-and-Execute / Reflection 实现模式、"
        "RAG 检索与评估、HTTP 请求链路、工具调用协议）。",
        "可复现证据：两个项目的评估集、压测报告与一致性评估脚本随代码提交"
        "（仓库 rag2/eval/、offeragent/docs/）。",
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
