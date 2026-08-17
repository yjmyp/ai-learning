# Codex Skills 安装包（2026-08-17）

## 0. 先说清楚（诚实版）

你发的三个抖音链接（codex的skill推荐 / 霖贝塔AI日记·公认最强8个 / G先生·本周skill排行榜）在本会话**无法直接读取**（抖音反爬 + 本会话无浏览器控制工具），所以"视频里那 8 个确切是哪些"我无法 100% 还原。

但我读到了同类型的一条高播放视频《新手用codex必装的十个插件skill》并核对了全网多个榜单。结论：

1. 那类视频里列的大部分其实是 **Codex 内置插件**（computer use / chrome / github / figma / pdf / documents / spreadsheets / camera / remote），不是社区 skill——本机**已经装好**的有：browser、chrome、computer-use、documents、pdf、presentations、spreadsheets、imagegen（打开 Codex 左侧插件栏可见）。
2. 全网共识的"公认最强社区 skill"集中在下面这份清单，仓库地址都已核实。

要 100% 还原视频原文：把霖贝塔那条的文字稿/截图发我（抖音点"查看AI文稿"复制），我逐一对齐仓库。

## 1. 共识清单（仓库已核实）

| Skill | 作用 | 仓库 | 安装命令（终端跑） |
|---|---|---|---|
| Superpowers | 工程方法论+技能框架，榜单常年第一 | obra/superpowers | `npx skills add obra/superpowers -g` |
| grill-me | 写代码前被 AI 追问到方案想清楚 | mattpocock/skills | `npx skills add mattpocock/skills --skill=grill-me -g` |
| handoff | 任务交接/上下文压缩 | mattpocock/skills | `npx skills add mattpocock/skills --skill=handoff -g` |
| Humanizer-zh | 中文去 AI 味 | op7418/Humanizer-zh | `npx skills add op7418/Humanizer-zh -g` |
| Agent-Reach | 让 Agent 能读全网（推特/Reddit/YouTube/GitHub/B站/小红书） | iwachacha/Agent-Reach | 按官方文档：`git clone https://github.com/iwachacha/Agent-Reach.git` 后看 docs/install.md |
| claude-mem | 跨会话持久记忆（Claude Code/Codex 通用） | thedotmack/claude-mem | 按官方 README（含 MCP 配置） |
| 官方精选 curated | OpenAI 官方维护 | openai/skills | 在 Codex 里说"用 skill-installer 列出官方 curated skills"再挑 |

## 2. 一键执行（PowerShell，逐条复制）

```powershell
# 1) 先确认 node 可用（你机器已装）
node --version

# 2) 依次安装（装完会进入 ~/.codex/skills 或 ~/.agents/skills）
npx skills add obra/superpowers -g
npx skills add mattpocock/skills --skill=grill-me -g
npx skills add mattpocock/skills --skill=handoff -g
npx skills add op7418/Humanizer-zh -g

# 3) 验证
Get-ChildItem $HOME\.codex\skills -Name
```

Agent-Reach 和 claude-mem 需要按各自 README 配置（涉及 CLI/MCP），装前把官方文档链接发给 Codex 让它帮你装更稳。

## 3. 更省事的方式（推荐）

在电脑端 Codex 桌面应用新开会话（全权限），直接把下面这段发给它：

> 帮我安装这些 Codex skills：① npx skills add obra/superpowers -g ② npx skills add mattpocock/skills --skill=grill-me -g ③ npx skills add mattpocock/skills --skill=handoff -g ④ npx skills add op7418/Humanizer-zh -g。装完列出 ~/.codex/skills 目录确认。

安装完成后**重启 Codex / 新开会话**即可生效（下次会话可用）。

## 4. 待办（如果你要精确还原视频）
- 复制霖贝塔"公认最强8个skill"视频的"AI文稿"文字，粘贴给我
- 复制 G先生"本周skill排行榜"的文稿/截图给我
- 我收到后逐条核对仓库并补进本清单
