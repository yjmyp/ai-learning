# 余剑

**AI 应用开发实习生（LLM / RAG / 智能体）** ｜ 南京 onsite / 远程均可

求职意向：AI 应用开发实习 ｜ 2026.09 下旬到岗，4-5 天/周，可实习 **6 个月以上**（2027.06 毕业，可无缝衔接转正）

电话：17578999648 ｜ 邮箱：yj2994762833@gmail.com ｜ 南京 ｜ 2027 届本科（2023.09-2027.06）

GitHub：https://github.com/yjmyp/ai-learning ｜ 上线项目：https://ai-learning-fphncazxmg3pnesntwchz6.streamlit.app/

---

## 教育背景

**南京邮电大学** · **网络工程** · 本科 · 2027 届

（网络工程背景，可快速理解网络 / 通信业务场景的 AI 落地需求）

相关课程：计算机网络、数据结构、操作系统、数据库原理

---

## 项目经历

### 1. RAG 知识库问答系统（已上线）　2026.07 – 2026.08

**核心成果：11 篇资料 → 254 块向量 → top-1/3/5 命中率 75% / 83% / 92%，回答带引用溯源**

Python ｜ sentence-transformers（bge-small-zh-v1.5）｜ Chroma ｜ FastAPI ｜ Streamlit ｜ DeepSeek API

- 独立设计并实现端到端 RAG 链路：文档解析 → 分层切分（300 字/块、50 字重叠，保留段落语义）→ bge 向量化 → Chroma 持久化向量库 → top-k 召回 → 重排 → LLM 生成**带引用来源**的回答
- 自建 12 条"问题+标准答案"评估集（扩充中），量化检索质量：**top-1/3/5 命中率 75% / 83% / 92%**，以数据驱动切分与检索优化
- 设计回答溯源机制：每条回答附引用编号与资料定位，可一键查看原文，保证可验证
- 工程细节：处理 API 超时/限流重试、修复嵌套 JSON 截断 bug、实现向量库离线缓存持久化；FastAPI 封装 REST 接口，Streamlit Cloud 部署上线，全程 Git 管理、GitHub 开源
- 迭代计划（已知限制）：固定切分 → 下一版语义切分 + BM25 混合召回；评估集 12 条 → 扩展至 50+ 条并引入 LLM-as-judge

### 2. Agent 工具调用 Demo　2026.08

Python ｜ Function Calling ｜ JSON Schema 校验

- 实现基于 JSON Schema 的工具调用协议链路：模型自主解析任务 → 参数校验 → 调用 add/subtract/multiply 工具 → 结构化结果回填
- 设计错误回填与自纠错循环（参数非法 → 错误信息反馈模型 → 重试），参数守卫拦截 **5 类坏输出**（未知工具 / 缺参 / 类型错 / 非对象 / 非法 JSON）
- 掌握 Agent 核心机制（Tool Use / ReAct 决策循环）；下一步：多工具协同 + 会话记忆 + 多轮规划（OfferAgent 项目进行中）

---

## 技能

- **语言与基础**：Python（熟练）、SQL（基础）、HTTP 协议
- **AI 应用开发**：大模型 API 调用（DeepSeek 全链路）、Prompt 工程、RAG 全链路、向量数据库（Chroma）、Function Calling、检索评估（eval）
- **工程与部署**：FastAPI、Streamlit、Git/GitHub、Streamlit Cloud 部署；学习中：Docker 容器化、LangChain、并发处理

---

## 自我评价

- **RAG 全链路落地**：独立完成并上线 RAG 问答系统（254 块向量、top-3 命中率 83%），重视评估与可溯源
- **智能体开发方向**：已实现 Function Calling 工具调用链路（JSON 协议 + 参数校验 + 自纠错），正在深入规划 / 记忆 / 反思
- **网络背景加成**：网络工程专业，可快速理解网络 / 通信场景的 AI 应用需求
- **执行力**：两周内完成"API 对话 → 向量检索 RAG → 网页部署上线"全链路，冷启动快、可独立扛事

---

> 备注：暂无实习经历，以"已上线项目 + 量化评估数据"作为核心证明；可提供完整代码与部署链接验证。简历内容真实可验证。
