# 学习上下文存档（CONTEXT）

> 作用：给 Codex 快速对齐"我是谁、学到哪了、接下来干什么"。微信里发消息前先让它读这个文件。

## 我是谁

- 男，南京邮电大学（南邮）大四学生（2027 届），网络工程专业，坐标南京
- 目标：2026 年 9-10 月投到 AI 应用开发实习（自己投，学校不安排），最终目标是正式工作
- 求职方向：AI 应用开发 + 懂技术的 AI 产品经理（双轨）

## 我已经掌握的（按时间顺序）

1. **Python 调用大模型 API**：`chat.py` —— DeepSeek 对话程序（连续对话、退出逻辑、异常处理）
2. **RAG 基础版**：`rag/rag_chat.py` —— TF-IDF 字符 n-gram（2~3 字）检索 + 拼 Prompt 让模型回答
3. **向量检索 RAG**：`rag/rag_vector.py` + `rag/rag_chat_vector.py` —— 用多语言向量模型（bge）做语义检索
4. **Streamlit 网页版**：`rag/rag_app.py` —— 网页界面 + 可溯源折叠面板，本地可跑
5. **Agent 工具调用**：`agent_calc.py` —— 让模型按 JSON 格式调用 add/subtract/multiply 工具
6. **Git 基础**：init / add / commit / push，仓库 `ai-learning`（GitHub 用户名 yjmyp）
7. **微信接入本机 Codex**：codex-weixin（Node 服务 + 扫码登录 + 微信指挥本机 Codex）
8. **Streamlit Cloud 部署上线**：`rag_app.py` 已部署到公开网址 https://ai-learning-rkcci4rwsv6aewbthzbvvc.streamlit.app/ —— 学会用 requirements.txt 管依赖、st.secrets 管密钥、修复云端相对路径；教训：API key 不能硬编码进代码（会随 GitHub 泄露）
9. **微信全权限遥控**：codex-weixin 已配置为 exec + danger-full-access，微信会话可写文件、推 GitHub（踩坑：codexExecSandbox 修改后必须重启服务才生效；workspace-write + approval never 会被 Codex CLI 降级为只读；目录需在 ~/.codex/config.toml 标记 trusted）
10. **RAG v2 重构 + 检索评估**：`rag2/` 全流程跑通（解析 → 300字/块切分 → bge 向量化 → Chroma 251 块 → 召回+TF-IDF 重排 → DeepSeek 问答带溯源）；写了 12 条 eval 评估集，基线 top-1 75% / top-3 83% / top-5 92%，并定位"关键词饱和 + 混合切分稀释"两个检索问题
11. **工具调用守卫（Agent 工程化）**：`agent_tool_guard.py`（TOOL_SCHEMAS 参数合同 + safe_call 校验）已集成进 `agent_calc.py`，修复嵌套对象 JSON 解析（extract_json），实测"345 减 67 = 278"通过——能讲清模型输出的 5 类坏调用
12. **简历 + 投递材料**：简历 v2（RAG 项目 STAR + 数字 254 块/top-3 83% + 技术债务小节 + GitHub/上线链接），一页 PDF 已导出；8/18 首投清单（Calix/萌想/GoalfyAI/硅基）与 5 分钟操作卡已备好
13. **手机学习助手 + 8/18 检索校准**：`学习笔记/AI学习助手-手机版-v2.html`（6 tab：地图/概念/面试/弹药/守则/打卡，含大厂真题、W 学姐复盘、偏印学习法）；8/18 抖音 11 条检索与 PLAN 追加见 `学习笔记/抖音链接读取结果-20260818.md`
14. **OfferAgent（求职工作台）v4**：`offeragent/` 跑在 localhost:8501。五个导航（今日 / 我的资料 / 岗位 / 投递 / 设置）；联网搜岗（牛客+实习僧+BOSS CDP）、岗位质量识别、岗位档案（筛选依据）、匹配分析、ATS 覆盖检查、话术生成（禁模板腔 + 自动重写）、问答式简历生成、PDF/Word/图片 OCR 读简历、自我蒸馏 15 题→6 份档案、面试拷问、投递漏斗/跟进提醒/邮件识别、公司速查。9/27 完成流程改造：顶部流程条（找岗→匹配→已投→有回应）、岗位卡片「一站式：匹配→ATS→话术→已投」、动作后「下一步」提示、简历提到第一层。验收脚本 `test_app_pages.py`（逐页巡检）+ `test_flow_check.py`（流程验收），均通过。
15. **9/28-10/1 工程收尾 + 简历 v4 + 第 1 周运营启动**（含与豆包对话决策，详见 AGENTS.md）：
   - **工程收尾全推云端**：`run_tests.py` 统一测试入口（26 测试，基线 15 通过/0 失败/11 跳过，`--live`/`--browser` 开关）；修 `test_undefined_names.py` 的 `import *` 误报（ast 收集源模块顶层名 + 容器内赋值）；新增 `docs/interview_talk.md`（30 秒陈述 + 8 个可深挖技术点：单一权威源/投递防抖/Supervisor 多 Agent/门禁 60/链接核验/SQLite 记忆/禁用词 v6/数字分身）+ `docs/weekly_ops.md`（每周 30 分钟运营：搜 10 岗→批量打分→投 5 个→复盘，跑 4 周）
   - **简历 v4**（`简历/余剑-简历-AI应用开发实习-v4.md`，已推云端）：OfferAgent 顶置第一项目 + 13 岗量化 + 三段式叙事
   - **岗位库 13 岗全部批量打分**（62–88 全待投）：AI应用开发可转正 88 > 蔚蓝 86 > Calix 82 > 小米/南大/三和 78 > 蚂蚁/纷子/境瞳/产品经理 72 > 亚信 62；彩讯排除。批量打分命令 `python batch_score.py --force --limit N`（每次 N 次 API 调用，测试费用可花）
   - **第 1 周运营已启动**：牛客搜岗 100 条 → 筛南京+非嵌入式 → 入库 3 岗（`AI应用开发（可转正）-464641` 88 分等）→ 已打分。投递动作留给用户（红线：最后一下永远人点）
   - **推送通道**：git→github.com:443 长期不通，写 GitHub 用 api.github.com REST（GET blob sha→PUT；新文件先 GET 捕 404→PUT 不带 sha；中文路径用 urllib.parse.quote；推完 Python 校验字节一致）
   - **对标罗宇豪简历的结论**：差在"三段式优化叙事（基线→动作→结果）+ 真实业务规模"，不差技术栈；学历（南邮一本 vs 民办）+ 自研可验证 + OfferAgent 差异化是占优项；补叙事 60% 即可追平，不追"1 年经验"
16. **2026-10-02 简历模板预览两个真 bug + 三套模板美化**（`offeragent/resume_templates.py`、`pages_more.py`）：
   - **bug1：作用域 class 带了点** —— `scope = ".oa-pv-classic"` 同时被当 CSS 前缀和 DOM class 用，DOM 里成了 `class=".oa-pv-classic"`，**所有预览样式全部匹配不上**：照片按原图 600×800 撑开、`.page` 内边距全丢 → 看起来"排版乱 + 图片加载错"。修法：CSS 用 `.{cls}`，DOM class 用 `{cls}`（不带点）。
   - **bug2：同一模板在一页出现两次会互相覆盖** —— 三列缩略（zoom 0.42）和放大预览（0.78）都写 `.oa-pv-classic { zoom: … }`，后定义的会同时盖住两个元素，导致缩略里的 classic 按 0.78 渲染、宽 624px 溢出 336px 的列被切 → 表现为"classic 被裁"。修法：`preview_html(..., instance="grid"/"zoom")`，class 带实例后缀。
   - **顺带**：缩放从 `transform: scale` 改成 CSS `zoom`（transform 不改变文档流占位高度，容器会按未缩放高度撑开 → 缩略图下面一大片空白）；`clip_height` 参数替代写死的 min-height；加"三列统一高度对比"开关（裁切+底部渐隐，默认关=完整显示）。
   - **美化**：按 ATS 简历通行规范（单栏/左对齐/靠字重与细线分层/量化结果前置）重做三套模板——职位胶囊、章节标题左侧蓝条、技术栈拆成 chip 标签、结果条圆角、照片 3:4 圆角+白边阴影、技能标签加宽对齐；宋体版（compact）保持黑白无装饰。三套打印态**实测各 1 页**（sidebar/compact 一开始变 2 页，收紧了打印字号与侧栏宽度后回到 1 页）。
   - **验收**：新增 `offeragent/test_resume_preview.py`（量 DOM：容器高 vs 内容视觉高、页脚是否可见、照片渲染尺寸与 3:4 比例）→ 四块预览全部"容器=内容、页脚可见"，照片 44×59 / 50×66 / 40×54 / 81×109 全部正确；`run_tests.py` 统一入口从"12 通过/3 失败"修到 **15 通过 / 0 失败 / 12 跳过**（那 3 个失败其实是测试脚本把 emoji 打到 GBK 控制台崩了，已统一加 `sys.stdout.reconfigure(utf-8)`）。
   - **云端没生效的排查结论**：逐行比对后发现**云端仓库其实已经有这次修复**（远端 `preview_html` 与本地逐字节一致），本地磁盘文件也与远端一致 → 问题不在代码，在"云端没跑到新代码"。为此加了**版本指纹**：`resume_templates.build_tag()`（本文件 md5 前 8 位），「我的简历 → 简历模板」页会显示 `模板引擎版本 xxxxxxxx`，**本地和云端数字不一致 = 云端还在跑旧代码，去 Manage app → Reboot**（当前本地指纹 `1a7bf2b5`）。
   - **补上云端推送通道脚本** `tools/push_to_github.py`：从 Windows 凭据管理器读 token（`git credential fill`，不落盘不打印），走 api.github.com 按文件 PUT/DELETE 并**逐字节校验**；支持 `--dry-run`、`--files a,b`（本地 refs 落后时直接推指定文件）。用的是 `python tools/push_to_github.py --files "offeragent/resume_templates.py,offeragent/pages_more.py"`，实测 2/2 成功、字节一致。
17. **2026-10-08 RAG v3 第一阶段：可评估的检索服务**（`rag2/`，用户要求"把项目完全做了"）：
   - **索引升级**：语料 11 篇/254 块 → **28 篇/622 块**（`python rag2/build_eval_set.py --rebuild`）
   - **新增模块**：`fusion.py`（RRF 融合）、`query_rewrite.py`（multi-query + HyDE）、`rerank_v3.py`（多特征重排 + 预留 cross-encoder/LLM listwise 两档）、`retriever_v3.py`（`vector`/`hybrid`/`hybrid_rerank`/`full` 四模式 + 拒答门禁）、`selfcheck.py`（答案级自检，只对事实型问题触发）、`calibrate_refusal.py`（阈值网格搜索）
   - **评估基建**：`build_eval_set.py` 自动生成 **54 条评估集**（42 条可回答，每条绑定 ground-truth 块 id；8 条明显库外 + 4 条难负例）→ `eval_v3.py` 跑四模式消融 + 出报告（`eval/report_v3.md`、`eval/refusal_calibration.md`）
   - **实测数字（top_k=5）**：纯向量 R@1/3/5 = 69/81/86%、MRR 0.757；**混合(RRF) 74/86/95%、MRR 0.808**；**混合+重排 74/93/98%、MRR 0.832、误拒 0%、P95 63ms**（默认档）；多查询档 R@1 有波动（74~81%）、R@5 95%、P95 1242ms（**结论：性价比低，默认不开**）
   - **拒答从 0% → 100%**：第一版拍的阈值（rerank<0.28）实测完全失效；改为在评估集上网格搜索 → **coverage<0.13** 拦掉全部明显库外问题；再加"**答案级自检**"（只对多少/几/哪年/薪资/参数类问题触发）把 4 条难负例从 0% 拦到 **100%**，误拒仅 2%
   - **面试文档**：`rag2/docs/rag_v3_upgrade.md`（改动清单 + 数据表 + 三条结论 + 四条已知局限 + 三句话讲法 + 追问准备）
18. **2026-10-08 RAG v3 第二阶段：服务化 + 面试文档升级到 v3**：
   - **FastAPI 服务化** `rag2/service.py`：`/health` `/stats` `/search` `/ask`（**SSE 流式**）`/reindex`，`SERVICE_API_KEY` 保护写操作
   - **trace 可观测** `rag2/trace.py`：每次问答落 JSONL（问题/改写/候选/引用来源/耗时/token/**成本**），`/stats` 直接给 **P50/P95 延迟、拒答率、单次成本**（实测单次 ~1.4s / ~0.0003 元）
   - **增量索引** `rag2/index_incr.py`：按 source 先删旧块再写新块，改一篇不用全量重建（`store.delete_by_source`）
   - **Docker 化** `rag2/Dockerfile` + `docker-compose.yml` + `.dockerignore` + `requirements-service.txt`（CPU 版 torch，密钥走环境变量，data 挂 volume）
   - **QA 层** `rag2/qa_v3.py`：检索 → 拒答门禁 → 答案级自检 → **结构化引用**（编号/来源/片段/分数/chunk_id）→ 流式生成
   - **验收** `rag2/test_service.py` **7/7 通过**（健康/索引统计/检索带分/问答带引用/库外拒答/SSE 187 个增量块/trace 指标聚合）
   - **面试文档升级**：`interview-prep/01-rag-deep-dive.md` 加"八、v3 升级补充"（数据表 + 三个必讲决策 + v3 高频追问 6 条）；`interview-prep/03-offeragent-deep-dive.md` 加"八、Agent 四层框架对照"（Planning/Memory/Tool/Reflection + 工程化 + 部署的现状/缺口/补法，含 LangGraph 对标话术与生态现状：AutoGen 已维护模式等）
19. **2026-10-08 OfferAgent P0：结构化匹配打分 + 一致性评估 + trace 可视化**：
   - **`match_score.py`（仓库根）结构化打分**：五维本地加权（硬技能 0.30 / 项目证据 0.25 / 地点 0.15 / 时间 0.15 / 门槛 0.15），**不调模型**；每维给命中/缺失证据；门槛维单独拦「硕士」「2028 届」「方向偏算法」这类硬冲突。踩坑记录：① 画像开头有「| 项目 | 内容 |」表格表头，直接找"项目"会把技能区切没 → 只在明确分节标题切；② 纯覆盖率会让所有岗位都低分（最高才 55）→ 改成饱和式（命中 4~8 个核心词即满分）；③ 方向判断要用**岗位标题**而不是 JD 正文（正文里"工程/开发"太泛）
   - **一致性评估 `eval_match_consistency.py`**：同一岗位两法各跑 5 次 → **旧法（模型直接给分）平均标准差 3.31 分（最大波动 10 分），新法（结构化）0.00 分**，报告 `offeragent/docs/match_consistency.md`
   - **接入界面**：`pages_match.py` 新增 `render_struct_score()`，**进页面立刻显示**结构化分 + 五维证据 + 硬门槛红字 + 一键写回岗位库（不再依赖模型报告先跑）
   - **trace 可视化** `offeragent/agent_trace_view.py`：作为「今天」页第三个 tab「Agent 运行记录」，给运行次数 / 平均步数 / 工具调用分布 / 工具覆盖率 / 每次运行时间线（步 → 工具 → 参数摘要 → 结果）
   - **验收**：全量 10 页巡检无报错；Match 页实测显示"结构化总分 89 / 命中 python、大模型、agent…/ 缺 llm、prompt…"；今日页三个 tab 都在
20. **2026-10-08 欠账六项全部完成（RAG P3 + OfferAgent P1）**：
   - **RAG P3-a 句级引用定位** `rag2/locate.py`：从命中块里再挑"真正回答问题的那句"（词面覆盖 0.75 + 长度 + 数字加权），返回 `quote/offset/score`；`qa_v3.citations()` 升级成带句级引文与字符偏移（前端可高亮）
   - **RAG P3-b 多格式解析** `rag2/loader.py`：新增 `.html/.htm`（标准库 HTMLParser 剥标签、丢 script/style）、`.csv`（列名:值 可读化）、`.xlsx`（**手写 zip+XML 解析，本机没有 openpyxl 也能读**，兼容 sharedStrings 与 inlineStr）
   - **OfferAgent Plan/Reflect 节点** `offer_agent_plan.py`：`make_plan()` 先出 3-6 步计划并**校验工具名**（模型编造的非法工具会被单独标出）；`reflect()` 任务收尾自评 goal_met/evidence/gaps/next_action，**解析失败保守兜底不假装成功**
   - **OfferAgent MCP 工具层** `offer_agent_mcp.py`：手写 MCP（stdio + JSON-RPC 2.0）暴露 10 个工具，`initialize / tools/list / tools/call` 全部可用，执行类工具 `open_application` 带 `humanConfirm` 标注。踩坑：**Windows 控制台默认 GBK，MCP 必须强制 UTF-8**（否则客户端按 utf-8 解码直接报错）
   - **OfferAgent 记忆 embedding 化** `offeragent/memory_vec.py`：长期记忆三档自动降级（bge 向量 → TF-IDF → 词面重合），`context_block()` 召回结果注入 Agent system；并接入 `run_agent`。踩坑：**加载 bge 前必须先设 HF_HUB_OFFLINE，否则联网查版本会卡死几分钟**（这次真卡了 10 分钟）
   - **OfferAgent Docker 化** `offeragent/Dockerfile` + `docker-compose.yml`：构建上下文=仓库根、密钥走环境变量、`offeragent/data` 挂 volume；本机没装 Docker，用 `test_docker_static.py` 做静态校验（12/12）
   - **验收**：`rag2/test_p3.py` **7/7**、`offeragent/test_agent_v3.py` **11/11**（含真起 MCP 子进程跑 JSON-RPC）、`test_docker_static.py` **12/12**
  - **另交付**：`学习笔记/任务提示词模板.md`（从真实对话提炼的 6 个模式 + 优化点 + 任务卡模板 + 5 个高频任务提示词 + 4 条硬约束）

21. **2026-10-08 晚 生产级补齐 + 简历数字同步 + 讲法补齐**：
   - **简历数字同步**：`简历/余剑-简历-AI应用开发实习-v6.md` 与 `offeragent/resume_content.py`（模板/PDF 数据源）同步为 **28 篇 / 622 块 / 54 条评估集 / 混合+重排 top-5 98% / 拒答 100% / 结构化打分方差 0.00 vs 旧法 3.31**；内容变长后收紧 `resume_styles.py` 打印样式，三套模板各 1 页
   - **interview-prep 六项讲法**：`01-rag-deep-dive.md` 加 8.6（句级引用定位/多格式解析/服务化/Docker + 3 条追问）；`03-offeragent-deep-dive.md` 加 8.4（四层框架补齐：Plan/Reflect/MCP/记忆/工程化/部署 + 2 个踩坑）；本轮再加 **8.7 生产化** 与 **8.5 商业化就绪度**
   - **RAG 服务生产化（有数字）**：压测脚本 `rag2/loadtest.py` → 报告 `rag2/eval/loadtest_report.md`：**冷启动 15 333ms → 加 `SERVICE_WARMUP=1` 启动预热后首请求 62ms**；稳态并发 1/2/4/8 = 14/18/20/**22.6 QPS**（P95 86→388ms，瓶颈=单进程 CPU 向量推理）
   - **探针分工 + 限流**：新增 `/live`（秒回不碰模型）、`/ready`（索引空 503）；`/health` 保持详情；探针端点不占限流额度（探针挤爆用户配额的坑）；429 带 Retry-After + 结构化错误
   - **验收**：`rag2/test_service_prod.py` **13/13**（401/422/429/503/探针不占额度/X-Request-ID/剩余额度头）；`run_tests.py` **18 通过 / 0 失败 / 12 跳过**（新增 `--service` 开关跑 rag2 服务测试）
   - **CI + Docker 真构建**：`.github/workflows/ci.yml` 三档（离线单测 / 真建索引+服务验收 / Docker 真构建）；`test_docker_build.py`（没 Docker 自动降级静态校验，`RUN_DOCKER_BUILD=1` 才真构建）
   - **仓库卫生门禁** `test_repo_hygiene.py` 5/5：已跟踪文件无真 key、secrets/data 未入库、.gitignore 覆盖（把早期"key 随 push 泄露"的教训固化成测试）
   - **商业化评估** `offeragent/docs/production_readiness.md`：判定标准 + 逐项证据 + 剩余缺口。结论：技术侧到生产级；产品侧仍是"单人工具"（缺多用户数据隔离 2-3 天、隐私合规 1 天）；商业化程度约 30%

## 接下来计划（2026-08-15 起，v4）

> 完整方案见 `PLAN.md`（综合 30+ JD + 学习路径 + 学习方式）；每日进度见 `学习进度日志.md`
> **2026-10-08 状态（最新）**：两个项目的技术侧已到生产级（可部署/可观测/可验证/有容量数字），**唯一硬缺口仍是"真实投递数 = 0"**。立即做：① 每天真实投 3-5 家（从 88 分可转正岗开始，发送动作永远人点）② 每投一家就记结果，攒 4 周真实数据 ③ 商业化的两个非技术缺口（多用户数据隔离、隐私合规）排在投递之后，见 `offeragent/docs/production_readiness.md`。
> 2026-10-01 状态：OfferAgent 功能已收口。① 每天真实投 3-5 家 ② 跑满 4 周运营流程 ③ 简历/README 数字同步到云端。别再规划，只执行。
> 2026-08-17 裁决：外部方案评估 + 全网交叉验证已定稿，见 `学习笔记/最终裁决与证据链.md`；执行节奏 = 8/18 首投 3-4 家 → 8/25 前 RAG 收尾（BM25+Ragas+必杀题）→ 9/5 前 Agent 项目 2 → 9/16 批量投。停止再规划，只执行。守卫已验证、简历一页 PDF 已出，明天只做首投 + RAG D2。
> 2026-08-18 追加：抖音 11 条检索校准（7 项采纳）已写入 PLAN；手机助手升 v2。待办顺延：Calix 首投 + BM25 eval 验证。

0. 【8/15 完成】赛道定位：JD 调研 30+ 家（A/B/C 档）+ 三视频核对 + PLAN v4 定稿
> 2026-09-14 现实校正：8/19-9/14 出现 26 天执行断层（0 投递 / 项目 0 行代码 / 日志停更）。当天唯一一次计划修订已写入 PLAN：投递优先、项目锁定、算法降为高频 30 题、记账恢复。

0. 【8/15 完成】赛道定位：JD 调研 30+ 家（A/B/C 档）+ 三视频核对 + PLAN v4 定稿
1. 【9/15 起 · 最高优先】投递：简历一页 PDF 已就绪，每天 3-5 家（南京中小厂 + 远程 + 外企），不等项目完成；大厂 9 月下旬按分波投
2. 【9/14-9/30】项目锁定 OfferAgent（Self-Distill 求职 Agent）：9/30 前可演示（个人画像 → 岗位匹配 → 简历建议 三闭环），中途不换项目
3. 【9/15-9/28】算法：高频 30 题 + 每题能讲，每周 ≥8 题；顺序 链表/二叉树/DP 入门 前置
4. 【一次性】Datawhale 教程对照式收尾：跳第 4-6 章对照 rag2 自己的实现，产出差异表后关闭教程任务
5. 【每天】进度日志 1 条；【每周】git commit ≥1 次

> 2026-09-27 追加（OfferAgent 收口）：功能迭代到此为止，**不再加功能**。当前唯一硬缺口 = 投递数为 0。下一步只有三件事：① 用 OfferAgent 每天投 3-5 家 ② 岗位库跑完匹配后立刻投 ③ 简历里的 Streamlit 链接已失效（9/19 被人刷爆 pro 费后删app），要重新上线必须加密码 + 限额 key。
> 2026-09-27 晚（部署收尾）：面试拷问→复盘库闭环已打通；README 功能表已对齐真实导航；新增 `test_cloud_boot.py`（临时目录空数据启动 + 五页巡检）实测通过——说明云端首访不会崩。代码已推 GitHub（`4dbe36a`，只提交 offeragent/，个人简历与学习笔记没进公开仓库）。部署只差本人登录 share.streamlit.io 点 5 步：Repo `yjmyp/ai-learning` / Branch `master` / Main file `offeragent/offer_agent_app.py` / Secrets 填 `DEEPSEEK_API_KEY` + `APP_PASSWORD` / Deploy；HR 名片页 = 链接 + `/?twin=1`。云端版受限项要提前知道：BOSS 抓取（依赖本机 Edge）和图片 OCR 在云上不可用，云端是展示版，真实使用在本机 8501。
> 2026-09-27 深夜（简历线）：① 新增 `resume_clean.py`——自动剔除简历里的 `file:///` 本地链接、`C:\` 盘符路径、`%E7%AE%80` 编码乱码（不影响正常百分比）；已接进「问答生成 / 保存我的简历 / ATS 检查」三处。② 问答式生成简历新增「照片」一题（直接给上传按钮，存成 `简历/照片.jpg`，名片页与打印版共用）。③ 简历重做为 v3（`简历/余剑-简历-AI应用开发实习-v3.md/.html/.pdf`）：删掉「自我评价」和自曝式备注，改成「求职说明」，项目结果前置成绿色结论条，实测 **1 页 A4**。④ 新增 `make_resume_pdf.py`：HTML → PDF 一键重生成，有照片会自动嵌进右上角（脚本实测：带照片 1 页、PDF 内含 1 张图）。**待办：本人照片还没提供**，把图放到 `简历/照片.jpg`（或在设置页上传）后跑一次 `python offeragent\make_resume_pdf.py` 即可出带照片版本。
> 2026-09-27 更晚（模板）：① 新增 `resume_templates.py`——三套模板 classic（单栏·结果前置，推荐）/ sidebar（左侧栏放照片+技能）/ compact（极简黑白），内容统一在 `DEFAULT_CONTENT`。② 照片上传从「设置」搬到「我的简历」页（顶部区块，带预览）。③ 「我的简历」页新增模板选择 + 下载 HTML；`make_resume_pdf.py --template xxx` 三种模板**实测各 1 页**，PDF 同时输出一份默认版给名片页下载按钮。验收脚本：`test_my_resume_page.py`（9/9）、`test_twin_portal.py`（11/11）、`test_resume_clean.py`（10/10）、`test_app_pages.py`（5 页无报错）、`test_auth_gate.py`（3/3）。**待办还是那张照片**。
> 2026-09-27 收尾（v5 结构重排，用户说"全做"）：导航从"按对象分"改成"按任务链分"，五个一级分区 = 🚀 今天 / 🎯 找工作 / 🧬 我的 / 📇 展示 / ⚙️ 设置；每个分区用会话级二级导航，支持跨分区「跳过去并定位到那一条」（`goto()` + `_go_nav/_go_sub/_go_focus` 待处理标记机制）。两条硬规则落地：**一个动作只有一个入口**（话术只在「找工作 → 投递台」生成，今日行动卡片与岗位卡片改成跳转+定位）、**同一个数字只有一个出处**（漏斗/趋势/岗位排名/日报统一到「今天 → 数据与日志」）。顺带：设置页收编「每日投递目标」并移出「分享链接」、展示页新增"对外素材自检"、清理 400 行 legacy 函数（文件从 3300 行降到 2878 行）、顶部流程条从四个 metric 卡改成一行细条。验收：`test_nav_structure.py` 18/18、`test_flow_check.py` 12/12、`test_my_resume_page.py` 12/12、`test_twin_portal.py` 11/11、`test_resume_clean.py` 10/10、`test_cloud_boot.py`（云端空数据五页无报错）、`test_auth_gate.py` 3/3。已推 GitHub `5363821`。
> 2026-09-27 深夜（v5.1 导航换血）：用户反馈"二级子页用得别扭、不实用"。原因查清了——自定义 segmented 二级导航没有 URL、层级不清、切分区还记着上次的子页。改成 **Streamlit 原生多页 `st.navigation`**：每页真实 URL（`/jobs`、`/match`、`/resume`、`/apply`、`/records`、`/distill`、`/interview`、`/show`、`/settings`），侧边栏按分区显示，跨页跳转用 `st.switch_page`（`goto_page("apply", talk_pick=xxx)`）。另外发现 Streamlit 侧边栏**最多直接显示 10 个页面**，多的会折叠成「View more」——所以刻意压到 10 页：数据与日志并进「今天」的第二个页签，拷问/陪练/复盘并进「面试准备」的三个页签。验收：`test_all_pages_sweep.py`（10 页 URL 巡检）全绿、`test_nav_structure.py` 20/20、`test_flow_check.py` 13/13（含"点匹配真的跳到 /match"）、`test_cloud_boot.py` 云端空数据 10 页无报错。已推 `95ea755`。
## 我的特点（回答时要考虑）

- 学习方法：项目驱动、成果导向；先给全景图，再讲细节；要动手，不要只讲理论
- 精力：下午/晚上最好；一天能保证 2 小时以上，状态好可以 4 小时
- 性格：容易三分钟热度 + 完美主义 + 犹豫；计划跟不上进展会焦虑，所以别把任务排太满
- 要求：回答**客观**，不要无脑顺着我，要直接指出我的错误和遗漏；全程中文
- 箴言：多做事少说话，向前走别回头

## 怎么配合我

- 给任务前先给整体框架，再一步步来
- 一次只给一小步，确认后再继续
- 涉及命令或代码，直接给可复制的完整内容
- 每完成一步给明确的正反馈，再给下一步
- 每天学习结束：更新 `学习进度日志.md`，并给我客观反馈（完成/评价/卡点/明天一步）
- **执行守则**：每天开始前读 `学习笔记/学习守则.md`（v2，2026-10-02）；我是执行者，会主动拦截换话题/无限返工/规划上瘾。**分工（按复杂度）**：新功能/复杂模块 AI 写初版 + 我做改动实验 + 讲清输入/输出/失败；简单改动/核心链路我自己写，AI 只 review。**节奏**：混合自适应（每周保底目标，不断层即可）。**投递门禁**：3 条可验证标准，满足 2 条即可投（详见守则）
