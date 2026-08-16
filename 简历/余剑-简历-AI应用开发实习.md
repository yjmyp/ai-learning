# 余剑

**AI 应用开发实习生（完整实现并部署 RAG 应用）** ｜ 南京优先，可远程

电话：17578999648 ｜ 邮箱：yj2994762833@gmail.com ｜ 南京 ｜ 2027 届本科（2023.09-2027.06）

GitHub：https://github.com/yjmyp/ai-learning ｜ 上线项目：https://ai-learning-rkcci4rwsv6aewbthzbvvc.streamlit.app/

---

## 教育背景

**南京邮电大学** · 网络工程 · 本科 · 2027 届

相关课程：计算机网络、数据结构、操作系统、数据库原理

---

## 项目经历

### 1. RAG 知识库问答系统（已上线）　2026.07 – 2026.08

Python ｜ sentence-transformers（bge-small-zh-v1.5）｜ Chroma ｜ FastAPI ｜ Streamlit ｜ DeepSeek API

- 独立设计并实现端到端 RAG 链路：文档解析 → 分层切分（300 字/块、50 字重叠，保留段落语义）→ bge 向量化 → Chroma 持久化向量库 → top-k 召回 → 重排 → LLM 生成**带引用来源**的回答
- 自建 12 条"问题+标准答案"评估集（扩充中），量化检索质量：**top-1/3/5 命中率 75% / 83% / 92%**，以数据驱动切分与检索优化
- 设计回答溯源机制：每条回答附引用编号与资料定位，可一键查看原文，保证可验证
- 使用 FastAPI 封装 REST 接口，Streamlit 构建交互界面，部署至 Streamlit Cloud 公开访问；全程 Git 管理、GitHub 开源
- 当前限制（技术债务）：固定切分未语义感知、未做混合检索、评估规模较小；下一版计划：语义切分 + BM25 混合召回 + 评估集扩展

### 2. Agent 工具调用 Demo　2026.08

Python ｜ Function Calling ｜ JSON 协议

- 实现基于 JSON 协议的工具调用链路：模型自主解析任务、决定调用 add/subtract/multiply 工具并返回结构化结果
- 掌握 Agent 核心机制（Tool Use / ReAct 决策循环）；计划 9 月扩展多工具协同与基础状态管理

---

## 技能

- **语言与基础**：Python（熟练）、SQL（基础）、HTTP 协议基础
- **AI 应用开发**：大模型 API 调用（DeepSeek）、Prompt 工程、RAG 全链路、向量数据库（Chroma）、Function Calling、检索评估（eval）
- **工程与部署**：FastAPI、Streamlit、Git/GitHub、Streamlit Cloud 部署

---

## 自我评价

- 专注大语言模型应用落地：独立完成并上线 RAG 问答系统（11 篇资料 → 254 块 → top-3 命中率 83%），重视效果评估与可溯源
- 学习路径清晰：正在深入 Agent 开发（工具调用 → 规划 → 记忆 → 反思），对评测工程化方向感兴趣
- 项目驱动、执行力强：两周内完成"API 对话 → 向量检索 RAG → 网页部署上线"全链路

---

> 备注：暂无实习经历，以"已上线项目 + 评估数据"作为核心证明；简历内容真实可验证。
