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

## 接下来计划（2026-08-15 起，v4）

> 完整方案见 `PLAN.md`（综合 30+ JD + 学习路径 + 学习方式）；每日进度见 `学习进度日志.md`

0. 【8/15 完成】赛道定位：JD 调研 30+ 家（A/B/C 档）+ 三视频核对 + PLAN v4 定稿
1. 【8/16-8/20】RAG 重构 v2：rag2 代码已写完，跑通验证 + eval 评估集 + 10 Q&A，第二版上线（硬截止 8/20）
2. 【8/21-9/5】Agent 核心 + LangChain + 自动化 Agent 项目上线
3. 【9/6-9/15】打磨 + 简历 + 面试 50 问 + LeetCode 40 题；9/10-9/15 第二次试投
4. 【9/16-10 月】批量投递 + 面试复盘
5. 【每周固定】LeetCode 3 题 + 面试 5 问；【每日】学习结束更新进度日志 + 微信反馈

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
