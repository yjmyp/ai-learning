# -*- coding: utf-8 -*-
"""
interview_drill · 面试拷问（AI 当面试官）
=========================================
用真实面试的强度问你，而不是给你一份题库让你背。

流程：
  1. 基于「画像 + 目标 JD」生成 10 个追问（分三类，每题标注考察点）
  2. 你逐个回答 → 每答一题给三段反馈：答得好在哪 / 缺什么 / 更好的答法
  3. 答完给一份总评（哪几题最危险）

硬性要求：点评只能基于你给的事实，不许替你编经历。
状态存 data/drill_{job}.json，可中断续答。
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"

QUESTION_PROMPT = """你是面试官，正在面一个应聘 AI 应用开发实习的学生。请出 10 个追问。

要求：
1. 分三类，数量 4 / 3 / 3：
   项目细节（4 题）：追问他做过的东西的实现、取舍、踩坑、边界
   技术选型与原理（3 题）：为什么这么选、原理是什么、出问题怎么办
   动机与规划（3 题）：为什么投这个方向、短板是什么、接下来怎么补
2. 必须包含这几个问题（可以换个问法）：
   "这个项目是你自己写的吗，AI 帮了多少"
   "如果检索出来的东西全是错的，你怎么办"
   "你最大的短板是什么"
3. 每个问题后面用括号标注考察点，例如（考察：你是否真的写过这段逻辑）
4. 问题要具体到他的项目和这个岗位，不要问通用八股
5. 只输出编号列表，1 到 10，不要标题不要解释

【求职者画像】
"""

FEEDBACK_PROMPT = """你在做面试复盘。下面是面试官的问题和学生的回答。

给他三段反馈，总共不超过 150 字：
1. 答得好的地方（引用他原话里的具体亮点，如果确实没有，就直说没有）
2. 缺什么（面试官接下来会追问什么，或者哪里答偏了）
3. 一个更好的答法（只能用他给的事实，不许替他编经历或数字）

格式：
✅ 好的：
⚠️ 缺的：
💡 换个说法：

问题：
"""


def _state_path(job: str) -> Path:
    safe = re.sub(r"[^\w\u4e00-\u9fa5]+", "_", job)[:50]
    return DATA_DIR / f"drill_{safe}.json"


def load_state(job: str) -> dict:
    p = _state_path(job)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"job": job, "questions": "", "items": []}


def save_state(state: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _state_path(state["job"]).write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_questions(text: str) -> list:
    """把编号列表切成题目。"""
    out = []
    for line in (text or "").splitlines():
        s = line.strip()
        m = re.match(r"^(\d+)[.、)]\s*(.+)$", s)
        if m:
            out.append(m.group(2).strip())
    return out


def make_questions(profile: str, jd: str, ask_model) -> tuple:
    """生成 10 题。返回 (原始文本, 题目列表)"""
    text = ask_model(QUESTION_PROMPT + profile + "\n\n【目标岗位 JD】\n" + jd) or ""
    return text, parse_questions(text)


def feedback(question: str, answer: str, ask_model) -> str:
    return (ask_model(FEEDBACK_PROMPT + question + "\n\n回答：" + answer) or "").strip()


SUMMARY_PROMPT = """下面是一个学生做过的面试模拟问答。请给一份总评（不超过 200 字）：

## 最危险的三个问题
（哪几题答得最弱，为什么危险）

## 最该补的一件事
（只给一件，要具体到"做什么、大概多久"）

要求：只说事实和判断，不要鼓励式的话，不要"加油"。
"""


def total_review(items: list, ask_model) -> str:
    body = "\n\n".join(
        f"问：{it.get('q')}\n答：{it.get('a')}\n点评：{it.get('f')}" for it in items)
    return (ask_model(SUMMARY_PROMPT + body) or "").strip()
