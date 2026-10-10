# ⚠️ 投递只看这三份（其余全是历史草稿，链接已失效）

## 投递用（选一份，看场景）

| 用途 | 文件 | 说明 |
|---|---|---|
| **发给 HR / 上传附件** | `余剑-简历-AI应用开发实习-正式投递版.pdf` | **1 页**，含照片；链接只有两个：GitHub + 免密数字名片 |
| **粘贴到网申 / BOSS 正文** | `余剑-简历-AI应用开发实习-投递文本版.md` | 纯文本版，内容与 PDF 完全一致 |
| **改内容的源文件** | `余剑-简历-AI应用开发实习-v11.md` | 只改这一份，然后重新生成上两份 |

## 别用（都是历史版本，链接已失效或要密码）

- `余剑-简历-AI应用开发实习-v2 ~ v10.md`：早期草稿，里面还写着旧链接状态（根链接当时要密码、RAG 当时失效），现已全部修复并免密——以 v11 和本文件为准
- `余剑-简历-AI应用开发实习-正式版.pdf` / `-v3*.pdf` / `余剑-应聘AI应用开发实习-本科.pdf`：旧排版产物
- `简历生成器.html` / `余剑-简历-AI应用开发实习.html` / `-最终预览.html`：网页预览，不是投递件（`-最终预览.html` 已同步为最新）

## 简历里那几个链接，面试官点开会看到什么（今天实测，全部免密）

| 链接 | 打开后的样子 | 需要密码吗 |
|---|---|---|
| `https://ai-learning-c62pgpcfp7us6rztelatpj.streamlit.app/?twin=1` | 数字名片：预设问题（"介绍下你的 RAG 项目""你最大的短板是什么"）+ 学历/届别/方向/坐标 + 技术栈 + 联系方式，可以直接对着问 | **不需要**（免密专为面试官设计） |
| `https://ai-learning-c62pgpcfp7us6rztelatpj.streamlit.app/` | OfferAgent 工作台主界面（岗位库 / 匹配分析 / 简历 / 投递台 / Agent流程） | **不需要**（已免密） |
| `https://ai-learning-fphncazxmg3pnesntwchz6.streamlit.app/` | RAG 检索服务（AI学习知识库v2，当前 2644 块资料，问答 / 检索调试） | **不需要** |
| `https://github.com/yjmyp/ai-learning` | public 仓库，README 即作品集描述（含 Java API 层、评估集与压测、Docker + CI） | 不需要 |

> **休眠提示**：Streamlit 免费版闲置 15 分钟会休眠。面试官打开若看到 "Zzzz / This app has gone to sleep"，点 "Yes, get this app back up!" 等 1 分钟左右即可进入；已设置每小时自动保活，尽量保持在线。
> 三个演示链接均为免密，可直接发给面试官。

## 生成命令（改了 v11 之后重出这两份）

```powershell
cd offeragent
python -c "import sys; sys.path.insert(0,'.'); from pathlib import Path; import resume_templates as rt, make_resume_pdf as mk; RES=Path('../简历'); html=rt.render_with_photo('classic'); (RES/'余剑-简历-AI应用开发实习-最终预览.html').write_text(html, encoding='utf-8'); mk.html_to_pdf(html, RES/'余剑-简历-AI应用开发实习-正式投递版.pdf'); (RES/'余剑-简历-AI应用开发实习-投递文本版.md').write_text(rt.to_markdown(), encoding='utf-8'); print('已重出三份交付物')"
```
