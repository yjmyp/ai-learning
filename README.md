# 余剑 · AI 应用开发作品集（Agent + RAG）

**南京邮电大学 · 网络工程 · 2027 届** — 求职方向：AI 应用开发 / Agent 开发 / RAG 检索（实习）

独立完成两个可上线、可量化的 LLM 应用项目，均带自建评估集、压测报告、Docker 部署与 CI：

| 项目 | 说明 | 亮点 |
|---|---|---|
| [OfferAgent 求职工作台](offeragent/) | Agent 工具调用与工作流引擎：画像蒸馏 → 岗位匹配 → 话术生成 → 投递 → 复盘 全链路 | 打分从不可复现改为可复算（标准差 10 → 0.00）；30/30 工具守卫；Java/SpringBoot 3 + MySQL + Redis 对外 API 层 |
| [RAG 检索问答服务](rag2/) | 私有资料检索问答：多格式解析 → 结构切分 → 混合召回 → 多特征重排 → 句级引用 | R@5 95% / MRR 0.856（240 条自建评估集）；可信拒答误拒率 2%；稳态 20 QPS |
| [Java API 层](java-api/) | OfferAgent 对外服务：SpringBoot 3 + JDK 21 + MySQL(JPA) + Redis + Docker | 缓存 464ms→51ms；API Key 鉴权 + 限流；Prometheus + Swagger；17 项单测通过，5 项集成无 Docker 自动跳过 |
| [Vela 长任务 Harness](https://github.com/yjmyp/vela) | Agent 循环/震荡治理、租约与三方合并、快照回滚、技能门禁、审计链 | 76 tests；eval 6/6；真实 DeepSeek 2 轮 1444 tokens；快照回滚逐字节校验 |

## 在线演示

- OfferAgent 求职工作台：https://ai-learning-c62pgpcfp7us6rztelatpj.streamlit.app/
- RAG 检索服务：https://ai-learning-fphncazxmg3pnesntwchz6.streamlit.app/

> 两个演示均可免密体验；为保护 API 成本（公开部署曾被刷），均设有每日调用限额，超限次日自动恢复。

## 技术栈

Python（FastAPI / Streamlit）· Java（SpringBoot 3 / JDK 21）· DeepSeek API · LangGraph · MCP · Chroma / bge · MySQL · Redis · Docker · Git / GitHub Actions · SSE · 线程池并发

## 工程与质量

- CI 四 job 全绿（单测 / Java API / 服务验收 / 镜像构建）
- 两个项目均有离线回归测试、一致性评估脚本与压测报告（见各项目 `docs/`、`eval/`）
- 各项目证据与复现命令见对应 `docs/`、`eval/` 目录

## 目录结构

```
offeragent/    Agent 工作台（Streamlit 应用 + 引擎 + 工具注册表 + 简历子系统）
rag2/          检索问答服务（FastAPI + 检索链路 + 评估集）
java-api/      Java API 层（SpringBoot 3 + MySQL + Redis + Docker + 测试）
interview-prep/ 面试深挖材料（各模块 STORY + 追问）
```
