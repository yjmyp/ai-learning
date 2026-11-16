# -*- coding: utf-8 -*-
"""
distill_chat · 问答式自我蒸馏（对话形态）
========================================
和填表版（distill.py）共用同一批问题和同一份答案存储思路，但呈现成聊天：
一次一个问题，我回一句，你再问下一个。答完全部问题就能生成整套档案。

语气要求（写在提示词里）：专业、自然、像同事聊天。不夸人、不评判、
不用感叹号、不用表情符号。求职是严肃场合，不端着也不贫。
"""
import json
import re
from pathlib import Path

import distill

HERE = Path(__file__).parent
STATE_PATH = HERE / "data" / "distill_chat.json"


SCHEMA = 2


def blank_state() -> dict:
    return {"v": SCHEMA, "history": [], "answers": {}, "followups": {},
            "asked_followup": [], "pending": None, "idx": 0}


def load() -> dict:
    data = None
    if STATE_PATH.exists():
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = None
    if not isinstance(data, dict):
        return blank_state()
    # 老版本 state（只有 history/answers/idx）就地升级，绝不丢用户已答内容
    base = blank_state()
    base.update({k: v for k, v in data.items() if k in base})
    if not isinstance(base.get("answers"), dict):
        base["answers"] = {}
    if not isinstance(base.get("followups"), dict):
        base["followups"] = {}
    if not isinstance(base.get("asked_followup"), list):
        base["asked_followup"] = []
    if not isinstance(base.get("history"), list):
        base["history"] = []
    try:
        base["idx"] = int(base.get("idx") or 0)
    except Exception:
        base["idx"] = 0
    base["v"] = SCHEMA
    return base


def save(state: dict):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def reset():
    save(blank_state())


def current_question(state: dict):
    i = state.get("idx", 0)
    if i >= len(distill.ALL_QUESTIONS):
        return None
    return distill.ALL_QUESTIONS[i]


def progress(state: dict) -> tuple:
    done = len([k for k, _ in distill.ALL_QUESTIONS if state["answers"].get(k)])
    return done, len(distill.ALL_QUESTIONS)


def _has_detail(text: str) -> bool:
    """粗略判断一条回答里有没有"可核对的细节"：数字、英文技术词、链接。"""
    t = text or ""
    return bool(re.search(r"\d", t)) or bool(
        re.search(r"[A-Za-z][A-Za-z0-9_+\-.#]{1,}", t)) or ("http" in t)


def coverage(state: dict) -> dict:
    """信息充分度体检（纯本地计算，不额外调模型）。

    口径：答题率 60 分 + 细节率 30 分 + 追问补充 10 分（每补充 1 条 +3，封顶 10）。
    返回分数、缺口清单、按轮完成情况——用来决定"能不能生成档案"。
    """
    answers = state.get("answers") or {}
    answered = [k for k, _ in distill.ALL_QUESTIONS
                if str(answers.get(k, "")).strip()]
    detailed = [k for k in answered if _has_detail(str(answers.get(k, "")))]
    followups = state.get("followups") or {}
    n_fu = sum(len(v or []) for v in followups.values())

    total = len(distill.ALL_QUESTIONS)
    score = 60.0 * len(answered) / total \
        + 30.0 * len(detailed) / total \
        + min(10.0, n_fu * 3.0)
    score = int(round(min(100.0, score)))

    rounds, missing = [], []
    for title, _intro, qs in distill.ROUNDS:
        done = sum(1 for k, _ in qs if str(answers.get(k, "")).strip())
        rounds.append({"title": title, "done": done, "total": len(qs)})
        for k, q in qs:
            if not str(answers.get(k, "")).strip():
                missing.append((title, q))

    return {"score": score, "answered": len(answered), "total": total,
            "detailed": len(detailed), "followups": n_fu,
            "rounds": rounds, "missing": missing}


ASSESS_PROMPT = """你在帮一个学生做信息采集。下面是刚问的问题和他的回答。

问题：{question}
回答：{answer}

判断这条回答能不能支撑一份"要交给别人看"的档案：
- 含一条以上具体细节（数字、工具名、链接、具体做法）→ 算够
- 全是"还行 / 挺好的 / 做了个项目"这类空话 → 算不够

严格按下面三行输出，每行一个标签，不要输出任何其他内容：

<ACK>一句自然的回应，不超过 30 字；不夸人、不评判、不用感叹号、不用表情</ACK>
<ENOUGH>yes 或 no</ENOUGH>
<FOLLOWUP>不够时写一个针对这条回答的追问，不超过 40 字；够时这一行留空</FOLLOWUP>
"""


def _tag(name: str):
    return re.compile(r"<%s>(.*?)</%s>" % (name, name), re.S)


def assess(question: str, answer: str, ask_model) -> dict:
    """一次调用同时拿到：回应 / 是否够 / 追问。

    解析失败或模型报错一律按"够"处理 —— 采集流程永远不能被模型输出格式卡住。
    """
    fb = {"ack": "", "enough": True, "followup": ""}
    try:
        raw = ask_model(ASSESS_PROMPT.format(
            question=question, answer=answer or "（跳过）")) or ""
    except Exception:
        return fb
    out = dict(fb)
    for key, name in (("ack", "ACK"), ("enough", "ENOUGH"), ("followup", "FOLLOWUP")):
        m = _tag(name).search(raw)
        if m:
            out[key] = m.group(1).strip()
    raw_enough = out["enough"]
    out["enough"] = (raw_enough if isinstance(raw_enough, bool)
                     else str(raw_enough).strip().lower().startswith("y"))
    if out["enough"]:
        out["followup"] = ""
    return out


_N_Q = len(distill.ALL_QUESTIONS)
_N_R = len(distill.ROUNDS)
_N_OUT = len(distill.OUTPUT_NAMES)

OPENING = (
    f"我用问答的方式帮你做一次自我蒸馏。一共 {_N_Q} 个问题，分 {_N_R} 轮："
    "你做过什么、能力边界在哪、平时怎么工作和学习、动机和压力反应、协作习惯、"
    "项目深挖、以及表达风格与边界。\n\n"
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
    f"{_N_Q} 题答完了。现在可以生成 {_N_OUT} 份档案：画像、亮点库、面试答案、"
    "差距清单、工作与学习模式说明书、数字分身说明书、表达风格与边界手册。\n\n"
    "点下面的按钮生成。生成后如果发现哪份不对，可以回来改答案再重新生成。"
)


def _next_message(state: dict) -> str:
    nxt = current_question(state)
    if not nxt:
        return CLOSING
    return f"**第 {state['idx'] + 1} 题：{nxt[1]}**"


def reply_and_ask(state: dict, answer: str, ask_model) -> str:
    """把这一轮问答写进历史，返回助手的下一条消息。

    两条路径：
      1) 上一轮是追问 → 这条是补充答案，写进 followups，然后进下一题
      2) 正常答题 → 判断信息够不够；不够就追问一层（每题最多一次），够就进下一题
    """
    answer = (answer or "").strip()
    skipped = (not answer) or answer == "跳过"
    key = state.get("pending")
    known = dict(distill.ALL_QUESTIONS)

    if key and key in known:
        if not skipped:
            state.setdefault("followups", {}).setdefault(key, []).append(answer)
        state["pending"] = None
        state["idx"] = state.get("idx", 0) + 1
        state["history"].append({"role": "user", "content": answer or "（跳过）"})
        msg = _next_message(state)
    else:
        q = current_question(state)
        if not q:
            return CLOSING
        key, qtext = q
        state["answers"][key] = "" if skipped else answer
        state["history"].append({"role": "user", "content": answer or "（跳过）"})

        verdict = {"ack": "", "enough": True, "followup": ""}
        if not skipped:
            verdict = assess(qtext, answer, ask_model)

        asked = state.setdefault("asked_followup", [])
        head = verdict["ack"] or ""
        prefix = head + "\n\n" if head else ""
        if verdict["followup"] and key not in asked:
            asked.append(key)
            state["pending"] = key
            msg = prefix + "**追问：" + verdict["followup"] + "**"
        else:
            state["idx"] = state.get("idx", 0) + 1
            state["pending"] = None
            nxt = current_question(state)
            msg = prefix + (CLOSING if not nxt
                            else f"**第 {state['idx'] + 1} 题：{nxt[1]}**")

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
