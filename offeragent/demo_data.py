# -*- coding: utf-8 -*-
"""demo_data.py —— 演示数据：空库时一键把界面填满（演示 / 截图 / 面试现场展示）。

原则（红线）：
- **绝不覆盖真实数据**：岗位库非空时拒绝写入（seed_demo 返回提示），除非显式 force=True。
- 每条演示岗位的 meta 带 `demo=True` 标记；「清除演示数据」**只删带这个标记的**，
  所以先载入演示、后来自己搜的岗，清演示时不会被误删。
"""
from store import (JDS_DIR, MATCH_DIR, META_SUFFIX, PROFILE_PATH,
                   list_jobs, save_new_job)

# (岗位名, 城市, 公司, 匹配分, 状态, JD 文本)
DEMO_JOBS = [
    ("AI/Agent 应用开发（2027 校招）", "南京", "示例科技 A", 88, "待投",
     "岗位职责：\n1. 参与 LLM 应用（Agent / RAG）的设计与实现；\n"
     "2. 负责知识库检索链路（切分、向量化、召回重排）的调优；\n"
     "3. 与产品一起把 AI 能力落到具体业务场景。\n\n"
     "任职要求：\n1. 计算机相关专业本科及以上，2027 届优先；\n"
     "2. 熟悉 Python，了解 LangChain / LlamaIndex 等框架；\n"
     "3. 有 RAG 或 Agent 项目经验者优先；\n4. 每周到岗 4 天以上，可转正。"),
    ("大模型应用开发（实习）", "南京", "示例智能 B", 86, "待投",
     "工作内容：\n- 基于大模型 API 开发对话与工具调用能力；\n"
     "- 搭建 Prompt 评测集，做效果迭代；\n- 参与前后端联调与部署。\n\n"
     "要求：熟悉 Python / FastAPI，了解向量检索与流式输出；"
     "有开源项目或博客加分。"),
    ("RAG 检索工程师（实习）", "杭州", "示例数据 C", 82, "待投",
     "职责：负责企业知识库的检索质量，包含文本切分策略、embedding 选型、"
     "召回与重排、评估集建设。\n要求：熟悉 Python，了解 BM25 / 向量检索，"
     "有 R@k / MRR 等检索指标调优经验优先。"),
    ("AI 产品经理（技术型·实习）", "上海", "示例产品 D", 78, "待投",
     "职责：\n1. 负责 AI 功能的场景调研与需求定义；\n"
     "2. 与算法、工程同学一起推进落地，写清输入输出与失败兜底；\n"
     "3. 用数据验证功能效果。\n"
     "要求：能看懂接口与数据，有技术背景或 AI 项目经历优先。"),
    ("Python 后端开发（AI 平台）", "南京", "示例平台 E", 72, "待投",
     "职责：负责 AI 平台的后端接口、鉴权、限流与可观测性。\n"
     "要求：熟悉 Python、MySQL、Redis，了解 Docker 与 CI；"
     "有 FastAPI 项目经验优先。"),
    ("算法实习生（大模型微调）", "北京", "示例研究院 F", 65, "已投",
     "职责：参与指令微调数据构造与训练评估。\n"
     "要求：熟悉 PyTorch，了解 LoRA / SFT，有论文或竞赛经历优先。"),
]

DEMO_PROFILE = """# 个人画像（演示数据）

> 这是一份**示例画像**，用于演示。删掉换成你自己的即可（「自我蒸馏」答 15 题自动生成）。

## 基本信息
- 目标岗位：AI/Agent 系统交付、Python 后端与智能运维（2027 校招）
- 城市：南京优先，可远程
- 届别：2027 届本科

## 技术栈
- 语言：Python（熟练）、SQL（会写）
- 大模型应用：Prompt 工程、RAG（切分/向量化/召回重排/评估）、Agent（工具调用、ReAct、多 Agent）
- 工程：FastAPI、Streamlit、Docker、GitHub Actions、SQLite

## 项目
1. **OfferAgent 求职智能体**：自我蒸馏画像 → 岗位匹配打分 → 话术生成 → 半自动投递 →
   面试拷问 → 复盘。含匹配一致性评估（2.36 → 0.00）、工具调用守卫、每日额度保护。
2. **RAG 检索问答服务**：33 篇 / 740 块语料，240 条评估集；默认重排档 R@5 95%、MRR 0.856，
   P95 88ms；冷启动 15.3s → 62ms。

## 优势
- 能把 AI 能力落到可验证的数字上（评估集、压测、一致性）
- 自己做过完整闭环，懂"从画像到投递"的全部环节

## 待补
- Java 生态（SpringBoot / MySQL / Redis）正在补
"""


def demo_job_names() -> list:
    """当前岗位库里带演示标记的岗位名。"""
    return [n for n, m, _ in list_jobs() if m.get("demo")]


def real_job_count() -> int:
    """非演示的真实岗位数。"""
    return sum(1 for _, m, _ in list_jobs() if not m.get("demo"))


def seed_demo(force: bool = False) -> str:
    """载入演示数据。岗位库非空（有真实岗位）时拒绝，避免覆盖。"""
    if real_job_count() > 0 and not force:
        return (f"岗位库里已经有 {real_job_count()} 个你真实的岗位，"
                f"先清空或手动删除再载入演示数据（不会自动覆盖）。")
    added = 0
    for name, city, company, score, status, jd in DEMO_JOBS:
        save_new_job(name, city, jd, source_url="",
                     extra={"company": company, "match_score": score,
                            "status": status, "demo": True,
                            "source": "演示数据"})
        added += 1
    prof_note = ""
    if not PROFILE_PATH.exists():
        PROFILE_PATH.write_text(DEMO_PROFILE, encoding="utf-8")
        prof_note = "，并写入了一份示例画像"
    return f"已载入 {added} 个演示岗位{prof_note}。"


def clear_demo() -> str:
    """只清除带 demo 标记的演示岗位与示例画像（自己的数据不动）。"""
    names = demo_job_names()
    for name in names:
        for p in (JDS_DIR / f"{name}.txt", JDS_DIR / f"{name}{META_SUFFIX}"):
            if p.exists():
                p.unlink()
    prof_note = ""
    if PROFILE_PATH.exists() and "演示数据" in PROFILE_PATH.read_text(encoding="utf-8")[:200]:
        PROFILE_PATH.unlink()
        prof_note = "，示例画像也删了"
    if not names:
        return "没有找到演示数据（可能已经清过了）。"
    return f"已清除 {len(names)} 个演示岗位{prof_note}。"
