# 给 DeepSeek 的项目速览（余剑 · OfferAgent）

> 用法：把本文件整段复制给 DeepSeek，开头加一句「先读完全文，然后按我的水平教我校验过的部分」。
> 目标是：让 DeepSeek 理解项目结构、知道怎么教我手敲，不浪费双方时间。

---

## 一、怎么教我（最重要，先读这条）

我是余剑，南京邮电大学网络工程 2027 届，目标 AI 应用开发/Agent 开发实习。无正式实习，靠自研自用的 OfferAgent + RAG 系统打差异化。

我的特点和教学规则（必须遵守）：
- 能看懂概念、推导思路，但**落地到代码就卡**。卡点通常是「思路 → 变量和操作」这一步。
- 教学法：一次只教一小步，先框架后填空；我答对就确认并推进，答错给提示不直接给答案；我说「糊涂了」就换例子/画图/生活类比，不重复原说法；报错一次只指一个错误。
- 不要给我完整代码当答案（除非我明确要），不要跳步，不要说「这很简单/你应该会」。
- 我口语化、逻辑跳跃，你不确定我的意思时先确认「你的意思是……对吗」。
- 用「你」不用「您」，不用空洞鼓励，不用命令式语气。
- 我焦虑时先共情，再给一个极小可执行的下一步。

## 二、项目一句话

OfferAgent = 求职全流程智能体（自研自用）：搜岗 → 批量匹配打分 → 门禁筛选 → 话术生成 → 半自动投递 → 面试拷问 → 复盘写回画像。核心是自己写的 Agent 引擎（不是框架封装）。

## 三、技术栈

Python 3.10 ｜ Streamlit（11 页面 Web 应用）｜ DeepSeek API ｜ SQLite 记忆 ｜ 线程池并发 ｜ GitHub 持久化 ｜ 无头 Edge 渲染 PDF

## 四、目录地图（offeragent/ 下）

**入口与分层**
- `offer_agent_app.py` —— 组合器：注册 12 个页面（st.navigation），L1 密码门，主题注入。不写业务。
- `store.py` —— 数据层：岗位库(data/jds/)、投递记录(applications.jsonl)、SQLite 记忆、简历读写。
- `llm.py` —— AI 层：DeepSeek API 封装，key 优先级 st.secrets → 环境变量 → config.json → local_key.py。
- `ui_kit.py` —— UI 层：hero/next_step 等公共组件。
- `prompts.py` —— 所有提示词集中管理。

**页面域（pages_*，只做 UI 编排，业务调分层）**
- pages_home（今日台/蒸馏聊天）/ pages_work（找工作：搜岗/岗位库/匹配）/ pages_match（对比）
- pages_apply（投递台/话术）/ pages_agent（Agent 控制台）/ pages_twin（数字分身名片页）
- pages_resume（简历内容/模板/照片/ATS 定制）/ pages_more（建议/设置/对比/公司/拷问/投递记录）

**简历系统（刚拆成三层，最近的教学重点）**
- `resume_content.py` —— 数据层：DEFAULT_CONTENT（唯一简历数据：项目/技能/教育）。
- `resume_styles.py` —— 样式层：7 套 CSS（classic/sidebar/compact/timeline/band/modern/duo）。
- `resume_templates.py` —— 引擎：RENDERERS 注册表 + render("模板名") 统一入口 + preview_html 预览 + to_markdown。
- `pages_resume.py` —— 简历页：模板卡片墙选择 + HTML/PDF/Markdown 三格式下载。

**业务模块**
- `job_sources.py` —— 搜岗：牛客（接口稳）/实习僧/BOSS 三源，入库带全字段。
- `distill.py / distill_chat.py` —— 自我蒸馏：把「我」变成结构化画像。
- `apply_assist.py` —— 投递话术生成（禁用词库防 AI 腔）。
- `job_quality.py` —— 岗位质量分（独立于匹配分的另一把尺子）。
- `resume_tailor.py` —— ATS 关键词覆盖检查（本地字符串比对，非模型判断）。
- `interview_drill.py` —— 面试拷问：拿画像+岗位出题。
- `digital_twin.py` —— 数字分身：HR 可点链接问「他」问题。
- `sync_data.py` —— 数据 push/pull 到 GitHub 私有仓库（持久化）。

**Agent 引擎（在 ai-learning/ 根目录，不在 offeragent/ 内）**
- `offer_agent_core.py` —— 引擎：状态对象 + ReAct 循环 + 预算上限 + trace 落盘。
- `offer_agent_tools.py` —— 工具注册表：schema 合同校验 + 守卫拦截 5 类坏输出 + 错误回填重试。
- `batch_score.py` —— 批量匹配打分：ThreadPoolExecutor 3 并发，串行→并发耗时降约 1/3。
- `eval_agent.py` —— 评估脚本：工具守卫 6/6、JSON 提取 6/6。

## 五、一次调用怎么走（以「批量打分」为例）

1. `batch_score.run_batch()` 取待匹配岗位 → `load_profile()` 读画像、`build_registry()` 建工具表
2. 每个岗位 `_score_one()`：拼 messages → `run_worker()` 进引擎循环
3. 引擎循环：模型输出 JSON（调哪个工具+参数）→ 守卫校验（非法 JSON/未知工具/缺参/类型错/非对象 → 错误回填重试）→ 本地执行 → 结果回填给模型 → 循环到模型给最终回答
4. `extract_score()` 从 trace 抠 match_score → 写回 `data/jds/*.meta.json` → 结果排序
5. 门禁：匹配分 < 60 → verdict「不建议投」，投递工具永远停在人工确认

## 六、当前状态

**已做到（可验证的数字）**：13 岗批量匹配全链路（分 62–88）；多岗位泛化蚂蚁 78%/小米 72%/Calix 88%；工具守卫 6/6；26+ 测试 0 失败基线；11 页面；7 套简历模板；云端已部署（Streamlit Cloud + 密码门 + Secrets）。
**最近刚做完**：简历模板拆三层 + 新增 duo 双栏模板 + 简历页拆出 pages_resume + 模板卡片墙美化（全部测试通过）。
**待办**：真实投递 = 0（要用它投 5-10 家）；算法第一档还差约 15 题；简历 3 段式改「改变+数字」写法。
**我最近在学**：并发/异步（batch_score 线程池）、引擎循环拆解（run_worker/final,state 拆包）、resume 三层结构、Agent 词汇（ReAct/Reflection/Supervisor/工具守卫/错误回填…）。

## 七、本次任务（请 DeepSeek 做）

给我讲解 + 带我手敲。建议按这个顺序，一次一个：
1. 先讲透 **resume 三层**（内容/样式/引擎）为什么这么拆、注册表怎么工作 —— 讲完让我自己加第 8 套模板。
2. 再拆 **batch_score 的 _score_one**：教我从头手敲（含并发改造思路）。
3. 再拆 **引擎循环**：run_worker 里 messages 怎么拼、错误回填怎么循环、final/state 为什么能拆包。
4. 每讲完一块，给我出一道「变形题」验证我是不是真懂，而不是记住。

遵守第一节的教学规则，一次一小步。
