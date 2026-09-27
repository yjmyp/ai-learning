# -*- coding: utf-8 -*-
"""
distill_chat · 问答式自我蒸馏（对话形态）
========================================
和填表版（distill.py）共用同一批问题和同一份答案存储思路，但呈现成聊天：
一次一个问题，我回一句，你再问下一个。答完 15 题就能生成 6 份档案。

语气要求（写在提示词里）：专业、自然、像同事聊天。不夸人、不评判、
不用感叹号、不用表情符号。求职是严肃场合，不端着也不贫。
"""
import json
from pathlib import Path

import distill

HERE = Path(__file__).parent
STATE_PATH = HERE / "data" / "distill_chat.json"


def load() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"history": [], "answers": {}, "idx": 0}


def save(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def reset():
    save({"history": [], "answers": {}, "idx": 0})


def current_question(state: dict):
    i = state.get("idx", 0)
    if i >= len(distill.ALL_QUESTIONS):
        return None
    return distill.ALL_QUESTIONS[i]


def progress(state: dict):
    done = len([k for k, _ in distill.ALL_QUESTIONS if state["answers"].get(k)])
    return done, len(distill.ALL_QUESTIONS)


OPENING = (
    "我用问答的方式帮你做一次自我蒸馏。一共 15 个问题，分五轮："
    "你做过什么、能力边界在哪、平时怎么工作和学习、动机和压力反应、以及协作习惯。\n\n"
    "答得越具体越好（数字、工具名、当时怎么想的）。写不出可以回「跳过」。"
    "中途关掉页面也没事，答案会存下来。\n\n"
    "**第 1 题：{q}**"
)

REPLY_PROMPT = """你是求职陪跑顾问，正在用问答方式帮一个学生整理自己的信息。

上一轮问答：
问题：{question}
回答：{answer}

接下来要问的问题：{next_q}

请写一条回复，包含两部分：
1. 对刚才的回答给一句自然的回应。要求：专业、简短、不夸人、不评判。
   如果回答里有具体的数字或细节，可以点一下那个细节（说明你听进去了）；
   如果回答很空，就平静地指出"这条信息偏少，后面生成档案时这块会是空的"，不要追问第二遍。
2. 换行，然后问出下一个问题，用加粗写问题本身。

硬性要求：总共不超过 90 字；不用感叹号；不用表情符号；不写"很棒""很好""加油"；
不说"我理解你的感受"这类空话；像同事聊天，但保持求职场合的分寸。
"""

CLOSING = (
    "15 题答完了。现在可以生成 6 份档案：画像、亮点库、面试答案、差距清单、"
    "工作与学习模式说明书、数字分身说明书。\n\n"
    "点下面的按钮生成。生成后如果发现哪份不对，可以回来改答案再重新生成。"
)


def reply_and_ask(state: dict, answer: str, ask_model) -> str:
    """把这一轮问答写进历史，返回助手的下一条消息。"""
    q = current_question(state)
    if not q:
        return CLOSING
    key, qtext = q
    answer = (answer or "").strip()
    state["answers"][key] = "" if answer == "跳过" else answer
    state["idx"] = state.get("idx", 0) + 1
    state["history"].append({"role": "user", "content": answer or "（跳过）"})

    nxt = current_question(state)
    if not nxt:
        msg = CLOSING
    else:
        try:
            msg = (ask_model(REPLY_PROMPT.format(
                question=qtext,
                answer=answer or "（跳过）",
                next_q=nxt[1])) or "").strip()
        except Exception:
            msg = ""
        if not msg:
            msg = f"**第 {state['idx'] + 1} 题：{nxt[1]}**"
    state["history"].append({"role": "assistant", "content": msg})
    save(state)
    return msg


def start(state: dict, ask_model=None) -> str:
    """第一次进来时给的开场消息。"""
    if state["history"]:
        return state["history"][-1]["content"]
    q = current_question(state)
    if not q:
        return CLOSING
    msg = OPENING.format(q=q[1])
    state["history"].append({"role": "assistant", "content": msg})
    save(state)
    return msg
