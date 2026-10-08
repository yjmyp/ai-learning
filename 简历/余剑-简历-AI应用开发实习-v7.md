# 余剑

**AI 应用开发实习生（LLM 应用 / RAG / Agent）**

南京邮电大学 · 网络工程 · 2027 届本科（2023.09–2027.06）

17578999648 ｜ yj2994762833@gmail.com ｜ 南京（南京 onsite 优先，可远程）

到岗 2026.09 下旬起 · 4–5 天/周 · 可连续实习 6 个月以上（毕业可无缝转正）

上线项目：OfferAgent 求职智能体（https://ai-learning-c62pgpcfp7us6rztelatpj.streamlit.app/） ｜ RAG 知识库（https://ai-learning-fphncazxmg3pnesntwchz6.streamlit.app/） ｜ GitHub：https://github.com/yjmyp/ai-learning

---

## 项目经历

### OfferAgent 求职智能体（自研 + 自用，持续迭代）　2026.09 至今

**自研 8 工具 Agent 引擎并上线自用：把「模型随口打分」改成五维本地加权后，重复打分方差从 3.31 降到 0.00；工具守卫 6/6 拦截全部坏调用；硬门槛自动拦下「硕士线 / 届别不符 / 方向偏算法」；跨岗位泛化实测蚂蚁 78 / 小米 72 / Calix 88 分；22 个真实岗位全链路跑通。**

技术栈：Python ｜ DeepSeek API ｜ Streamlit ｜ SQLite ｜ ReAct / Function Calling / 多 Agent / LangGraph

- **自研 Agent 引擎（非框架封装）**：8 工具统一 Schema 注册表 + ReAct 循环 + 预算上限防死循环；Plan / Reflect 两个节点（先出 3-6 步计划并校验工具名合法性；收尾自评目标是否达成，解析失败保守兜底不假装成功）；五类坏输出守卫（非法 JSON / 未知工具 / 缺参 / 类型错 / 非对象）+ 错误回填自纠错
- **工具层双来源：内置注册表 + 自研 MCP server**（stdio + JSON-RPC 2.0，暴露 10 个工具，任何支持 MCP 的客户端可挂载）；执行类工具（投递）带 humanConfirm 标注，发送永远停在人确认——Supervisor 模式下投递工具不在子 Agent 工具集里
- **匹配分结构化（可复算、可解释）**：本地五维加权（硬技能 0.30 / 项目证据 0.25 / 地点 0.15 / 时间 0.15 / 门槛 0.15），每维给出命中与缺失证据；一致性评估方差 0.00 vs 模型法 3.31 分（最大波动 10 分）；22 岗位实测自动筛出 6 个不该投的
- **数字分身（可面试演示）**：15 题自我蒸馏生成结构化画像 → 渲染为可交互分身页；HR / 考官在知情前提下点进链接，分身基于画像实时回答并展示项目证据，答案与画像数据一致可核验
- **投递流程状态机化**：用 LangGraph StateGraph 把「链接核验 → 门禁评分 → 话术生成 → 投递 → 记录回写」建成显式状态机，节点可单独复用与测试；投递前自动重访 URL 拦截失效链接，避免投空
- **长期记忆语义化 + 并发优化**：事实与复盘写入向量记忆（bge 语义召回，支持「上次那个高匹配的南京岗位」模糊指代），三档降级保证离线可用；批量打分线程池 3 并发（写回主线程防竞争），13 岗耗时降至约 1/3
- **可观测与产品闭环**：trace 落盘 JSONL + 可视化页（工具调用分布 / 覆盖率 / 每次运行时间线）+ 成本计量；自我蒸馏 → 岗位匹配 → 话术生成 → 半自动投递 → 面试拷问 → 复盘写回画像；简历支持 HTML / PDF / Markdown 三格式一键下载
- **工程化交付**：11 页面应用，数据 / AI / UI 三层拆分可独立测试；run_tests.py 统一测试入口 26 个测试 0 失败基线；GitHub Actions CI 三档（offline / service / docker）全绿；密钥走 Streamlit Secrets 不落代码

### RAG 知识库问答系统（已上线，可点开验证）　2026.07 – 2026.08

**独立实现并上线可评估的 RAG 检索服务：28 篇资料切 622 块，自建 54 条评估集（每条绑定 ground-truth 块）做四模式消融，混合检索 + 重排把 top-5 命中率从 86% 做到 98%（MRR 0.757 → 0.832）；加拒答门禁后库外问题 100% 拦截、误拒 2%。**

技术栈：Python ｜ bge-small-zh-v1.5 ｜ Chroma ｜ FastAPI ｜ Streamlit ｜ DeepSeek API

- **端到端链路自己实现**：解析（txt/md/pdf/docx/html/csv/xlsx，其中 xlsx 手写 zip+XML 解析、不依赖 openpyxl）→ 结构感知切分 → bge 向量化 → Chroma → **BM25 + 向量 RRF 融合** → 多特征重排 → **句级引用定位**（从命中块里挑出真正支撑答案的那句 + 字符偏移，前端可高亮）；不套 LangChain 封装
- **评估驱动优化（不靠感觉）**：54 条评估集做消融，量化出「混合召回解决没召回到、重排解决没排前面」的分工；多查询改写实测性价比低（top-5 反降、P95 +1.2s）所以不默认开——取舍有数据支撑
- **可信层（拒答 + 答案级自检）**：拒答阈值用评估集网格搜索校准（库内最低覆盖率 0.211 / 库外最高 0.125 → 取 0.13）；对「问具体数值」的问题再加答案级自检，把「词都命中但答案不存在」的难负例从 0% 拦到 100%，误拒仅 2%
- **工程化交付**：FastAPI 服务化（SSE 流式 + X-API-Key）+ 增量索引（改一篇只重算一篇）+ trace 计量（P95 1.4s、单次成本 0.0003 元）+ Docker 一键起服务

### Agent 工具调用（Function Calling 工程化）　2026.08

**实现"模型自主选工具 → 参数校验 → 执行 → 结果回填"完整链路，参数守卫拦截 5 类坏调用，错误回填后模型可自纠错重试；已演进为 OfferAgent 的引擎核心。**

技术栈：Python ｜ DeepSeek API ｜ JSON 协议 / 参数合同校验

---

## 教育背景

**南京邮电大学** ｜ 网络工程 ｜ 本科 ｜ 2027 届（相关课程：计算机网络、数据结构、操作系统、数据库原理）

---

## 技能

- **语言 / 基础**：Python、SQL、HTTP 协议、数据结构与算法
- **Agent / 大模型**：ReAct / Reflection / Plan-and-Execute 设计模式、多 Agent 协作（Supervisor）、Function Calling 与参数合同校验、Prompt 工程、MCP 工具接入协议、DeepSeek API 全链路、RAG 全链路（切分 / 向量化 / 召回 / 重排 / 生成）、Chroma、检索效果评估、LoRA 等微调方式原理
- **工程 / 部署**：FastAPI、Streamlit、SQLite、Git / GitHub、Docker 容器化、LangGraph 编排、LangSmith 可观测、并发 / 异步编程、Streamlit Cloud 部署 + Secrets 管理、GitHub Actions CI
- **工具链**：熟练使用 Codex / Cursor / Claude Code 等 AI 编程工具提效，全程用于项目开发与调试

---

## 一句话

自研并自用的 Agent 系统 + 可复现量化评估 + 真实 debug 记录；简历里每个数字、每条链接都可当场验证——代码在 GitHub，应用能打开，评估脚本在仓库里。
