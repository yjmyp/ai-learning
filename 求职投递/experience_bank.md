# Experience Bank（余剑 · 2026-08-17）

## 如实说明
- 无正式实习经历（简历已如实标注），候选池以"已上线项目 + 评估数据"为主——不虚构、不夸大。

## Internships
| Name | Duration | One-line highlight | Strong-fit directions |
|---|---|---|---|
| （无） | - | 暂无实习经历，以项目补位 | - |

## Projects
| Name | Duration | One-line highlight | Strong-fit directions |
|---|---|---|---|
| RAG 知识库问答系统（已上线） | 2026.07-2026.08 | 独立实现并上线端到端 RAG：解析→切分→bge 向量化→Chroma→召回+重排→DeepSeek 问答带溯源；12 条评估集 top-1/3/5 = 75%/83%/92% | AI 应用开发、RAG、检索评估、Agent（知识库型）、AI 产品经理（用户视角+可溯源） |
| Agent 工具调用 Demo | 2026.08 | JSON 协议工具调用 + 参数校验守卫 + 自纠错循环（extract_json 修复嵌套对象解析） | Agent 开发、Tool Use、大模型评测、AI 产品经理（流程设计） |

## Role Family × Experience Matrix（项目）
| Experience | AI 应用开发/RAG | Agent 开发 | 大模型评测 | AI 产品经理 |
|---|---|---|---|---|
| RAG 知识库问答系统 | 强 | 中 | 强 | 强 |
| Agent 工具调用 Demo | 中 | 强 | 中 | 中 |
| 候选数 | 2 | 2 | 2 | 2 |

## Pre-Application Calibration Rules
1. 每次投递前从矩阵选 2-4 条（RAG 必选；Agent 岗加 Agent Demo）
2. 读 JD 后按 JD 强调点排序
3. 选完先给用户列清单（项目名 + 一句理由），用户点头再用
4. 自荐语 = 项目 + 个人风格（项目驱动、执行快）+ 岗位匹配，不堆砌
5. 投递后在 application_log notes 里记录实际用了哪些经历

## STAR（RAG 项目）
- **S**: 学完 LLM API 后想做一个"能查资料再回答"的真实产品，而非 demo
- **T**: 从零实现 RAG 全链路并上线，回答要可溯源
- **A**: 文档解析→300字/块切分（重叠50）→bge-small 向量化→Chroma→top-k 召回→TF-IDF 重排→DeepSeek 生成带引用回答；FastAPI + Streamlit；自建 12 条评估集量化命中率；定位"关键词饱和+混合切分稀释"两个问题
- **R**: 11 篇资料切 254 块，top-1/3/5 = 75%/83%/92%，回答带引用溯源，已部署 Streamlit Cloud 公开访问

**Resume bullet:**
> RAG 知识库问答系统 | Python · bge-small-zh · Chroma · FastAPI · Streamlit
> - 独立实现端到端 RAG：解析→切分→向量化→召回→重排→LLM 生成带引用回答
> - 自建 12 条评估集，top-1/3/5 命中率 75%/83%/92%，数据驱动优化
> - FastAPI 封装 REST 接口 + Streamlit 界面，部署 Streamlit Cloud，Git 全流程管理
