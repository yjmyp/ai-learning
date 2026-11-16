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

QUESTION_PROMPT = """你是面试官，正在面一个应聘 2027 校招 AI/Agent 系统交付岗位的本科生。请出 10 个追问。

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
    parts = []
    for it in items:
        blk = f"问：{it.get('q')}\n答：{it.get('a')}\n点评：{it.get('f')}"
        fu = it.get("fu") or {}
        if fu.get("a"):
            blk += (f"\n追问：{fu.get('q')}\n追问的回答：{fu.get('a')}"
                    f"\n追问点评：{fu.get('f')}")
        parts.append(blk)
    body = "\n\n".join(parts)
    return (ask_model(SUMMARY_PROMPT + body) or "").strip()


# ============================================================
# v2 追加（2026-10-19）：四维打分 + 跨场次趋势
# 原来只有一段文字点评 —— 说不出"这周比上周强在哪"。
# ============================================================
SCORE_DIMS = ("结构", "深度", "真实", "表达")

SCORE_RUBRIC = """
另外，给这个回答按 4 个维度打分（0-10 的整数，不要小数，不要哄人，宁可低）：
- 结构：有没有先说结论、再分点、最后收口
- 深度：有没有具体实现 / 取舍 / 数字 / 踩坑
- 真实：有没有具体到项目、能被追问下去（空话套话给低分）
- 表达：口语化程度、有没有废话、有没有术语堆砌

最后单独一行，严格按下面的格式输出（前后不要写别的字）：
[[SCORES]] 结构=7;深度=6;真实=9;表达=6
"""

_SCORE_RE = re.compile(r"\[\[SCORES\]\]\s*(.+)")


def parse_scores(text: str) -> tuple:
    """从点评里抠出打分行。返回 (去掉打分行的正文, {维度: 0-10})。

    模型偶尔会把打分写成 JSON 或加小数点 —— 这里只认 "名字=数字"，
    抠不出来就返回空 dict（宁可没有分，也不要编一个分）。
    """
    t = text or ""
    m = _SCORE_RE.search(t)
    scores = {}
    if m:
        for part in re.split(r"[;；,，]", m.group(1)):
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            k = k.strip().strip("*` ")
            num = re.search(r"-?\d+(?:\.\d+)?", v)
            if k and num:
                scores[k] = max(0, min(10, int(round(float(num.group(0))))))
        t = _SCORE_RE.sub("", t).strip()
    return t, scores


def feedback_scored(question: str, answer: str, ask_model) -> tuple:
    """带打分的点评。返回 (正文, {维度: 分})。解析失败时正文仍是原始回复。"""
    raw = (ask_model(FEEDBACK_PROMPT + SCORE_RUBRIC
                     + question + "\n\n回答：" + answer) or "").strip()
    text, scores = parse_scores(raw)
    return (text or raw), scores


HISTORY_PATH = DATA_DIR / "drill_history.json"


def load_history() -> list:
    if HISTORY_PATH.exists():
        try:
            data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def add_history(entry: dict, cap: int = 300) -> list:
    rows = load_history()
    rows.append(entry)
    rows = rows[-cap:]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    return rows


def dim_avg(items: list) -> dict:
    """一批题目的四维均分（没有分的题直接不算）。"""
    acc, cnt = {}, 0
    for it in items:
        s = it.get("s") or {}
        if not s:
            continue
        cnt += 1
        for k, v in s.items():
            acc[k] = acc.get(k, 0) + v
    if not cnt:
        return {}
    return {k: round(v / cnt, 1) for k, v in acc.items()}


def session_avg(items: list):
    """整场平均分（四维总均，0-10）。没打分返回 None。"""
    scores = [it["s"] for it in items if it.get("s")]
    if not scores:
        return None
    vals = [v for s in scores for v in s.values()]
    return round(sum(vals) / len(vals), 1)


# ============================================================
# v2.5 追加（2026-10-19）：追问链 + 题库沉淀
# 原来一轮到底：答完 10 题就结束，面试里最要命的"第二层追问"没练到。
# ============================================================
FOLLOWUP_PROMPT = """你是面试官，学生刚回答完上面那个问题。现在追问一层。

规则：
1. 只盯着他回答里【含糊、没有证据、或者明显绕开】的地方问
2. 不许换话题，不许问"还有什么要补充的"
3. 一句话，不超过 40 字，直接是问句
4. 只输出这个问题本身，不要编号、不要解释、不要引号

【原问题】
"""


def make_followup(question: str, answer: str, ask_model) -> str:
    """基于这一轮的回答，生成一个更深的追问。"""
    text = ask_model(FOLLOWUP_PROMPT + question
                     + "\n\n【学生的回答】\n" + (answer or "")
                     + "\n\n【你刚才的点评】\n") or ""
    return text.strip().strip('"').strip()


# ============================================================
# STAR 结构诊断（2026-10-19）
# 纯本地规则，不花模型调用：先告诉学生「你缺哪一块」，
# 再让模型去点评内容。顺序反过来会得到一堆正确但没用的废话。
# ============================================================
_STAR_MARKERS = {
    "S": ("当时", "背景", "场景", "项目里", "在上", "起初", "我们团队", "公司",
          "学校", "比赛", "实习", "一开始", "需求方"),
    "T": ("负责", "目标", "要解决", "任务是", "需要", "被要求", "我的职责",
          "要做的", "问题在于", "痛点是"),
    "A": ("我", "做了", "实现", "设计", "改成", "引入", "优化", "排查", "拆分",
          "对比", "用了", "写了", "重构", "调参", "验证"),
    "R": ("提升", "下降", "降低", "减少", "达到", "从", "到", "结果", "最终",
          "上线", "通过", "准确", "召回", "延迟", "耗时", "覆盖率"),
}
_NUM_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|％|ms|毫秒|秒|s\b|分钟|人|条|次|倍|万|k\b|qps)", re.I)


def star_check(answer: str) -> dict:
    """判断一段回答有没有把 STAR 四块讲全。

    返回 {"S":bool,"T":bool,"A":bool,"R":bool,"score":0-4,"missing":[...],
          "has_number":bool,"length":int}
    规则刻意保守：宁可判「缺」也不要虚假通过。
    """
    text = (answer or "").strip()
    n = len(re.sub(r"\s+", "", text))
    hit = {}
    for k, words in _STAR_MARKERS.items():
        hit[k] = bool(text) and (any(w in text for w in words))
    # R 必须有数字支撑，只有「提升了」不算结果
    has_num = bool(_NUM_RE.search(text))
    hit["R"] = bool(hit["R"] and has_num)
    # 太空的答案不给过：A 至少 25 个非空白字符
    if n < 25:
        hit["A"] = False
    missing = [k for k in ("S", "T", "A", "R") if not hit[k]]
    return {
        "S": hit["S"], "T": hit["T"], "A": hit["A"], "R": hit["R"],
        "score": sum(1 for k in ("S", "T", "A", "R") if hit[k]),
        "missing": missing,
        "has_number": has_num,
        "length": n,
    }


_STAR_TIP = {
    "S": "补一句背景：这是什么场景、当时卡在哪",
    "T": "说清你的任务边界：你要解决的具体问题是什么",
    "A": "讲你**具体做了什么**：改了哪一层、用了什么办法",
    "R": "给结果和数字：从多少到多少，提升/下降了几个点",
}


def star_hint(check: dict) -> str:
    """把缺失项变成一句可执行的话。"""
    miss = (check or {}).get("missing") or []
    if not miss:
        return "STAR 四块齐了，接下来拼的是证据强度。"
    return "；".join(_STAR_TIP[k] for k in miss[:2])


def debrief(items: list) -> dict:
    """本轮复盘报告：全部本地计算，没有模型调用也能出结论。

    返回 {answered, total, avg, dims, weakest, star_rate, star_missing,
          short_answers, fixes}
    """
    items = items or []
    answered = [it for it in items if (it.get("a") or "").strip()]
    total = len(items)

    dims = {}
    for k in SCORE_DIMS:
        vals = [float((it.get("s") or {}).get(k)) for it in answered
                if (it.get("s") or {}).get(k) is not None]
        if vals:
            dims[k] = round(sum(vals) / len(vals), 1)
    avg = round(sum(dims.values()) / len(dims), 1) if dims else None
    weakest = min(dims, key=dims.get) if dims else None

    checks = [(it, star_check(it.get("a") or "")) for it in answered]
    star_rate = (round(sum(c["score"] for _, c in checks) / (4 * len(checks)), 2)
                 if checks else 0.0)
    star_missing = {}
    for _, c in checks:
        for k in c["missing"]:
            star_missing[k] = star_missing.get(k, 0) + 1

    short_n = sum(1 for _, c in checks if c["length"] < 60)

    fixes = []
    if not answered:
        fixes.append("先完整答完 1 题，再谈优化。")
    else:
        if weakest == "结构":
            fixes.append("结构分最低：每答先用「背景 → 任务 → 我做了什么 → 结果」四句打底。")
        elif weakest == "深度":
            fixes.append("深度分最低：至少补一层「为什么这么做 / 换一种做法会怎样」。")
        elif weakest == "真实":
            fixes.append("真实分最低：把「我们做了」改成「我做了哪一件」，并说清边界。")
        elif weakest == "表达":
            fixes.append("表达分最低：答案压到 90 秒内，先说结论再展开。")
        if star_missing.get("R"):
            fixes.append(f"{star_missing['R']} 题没有量化结果——结果必须带数字（提升几个点 / 从多少到多少）。")
        if star_missing.get("A"):
            fixes.append(f"{star_missing['A']} 题没讲清你具体做了什么，只说了团队做了什么。")
        if short_n:
            fixes.append(f"{short_n} 题回答不足 60 字，面试官会当成「没做过」。")
        if 0 < len(answered) < total:
            fixes.append(f"还有 {total - len(answered)} 题没答，先补齐再测均分。")
        if not fixes:
            fixes.append("这一轮没有结构性硬伤，下一步加追问深度和压力题。")

    return {
        "answered": len(answered), "total": total, "avg": avg, "dims": dims,
        "weakest": weakest, "star_rate": star_rate, "star_missing": star_missing,
        "short_answers": short_n, "fixes": fixes,
    }


# ---- 题库沉淀 ----
BANK_PATH = DATA_DIR / "question_bank.json"

_KIND_RULES = [
    ("技术原理", ("为什么", "原理", "选型", "区别", "机制", "怎么保证", "怎么评估",
                  "万一", "如果检索", "如果模型", "底层")),
    ("动机规划", ("为什么投", "规划", "短板", "打算", "未来", "动机", "职业",
                  "实习", "学习路线", "怎么补")),
    ("项目细节", ("项目", "实现", "怎么做的", "踩坑", "难点", "边界", "数据",
                  "效果", "上线", "并发", "优化")),
]


def classify(q: str) -> str:
    """本地给题目粗分类（不额外花模型调用）。"""
    s = q or ""
    for kind, kws in _KIND_RULES:
        if any(k in s for k in kws):
            return kind
    return "其它"


def _norm(q: str) -> str:
    return re.sub(r"[\s。？?，,、.]+", "", q or "")[:60]


def load_bank() -> list:
    if BANK_PATH.exists():
        try:
            data = json.loads(BANK_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def save_bank(rows: list) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BANK_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2),
                         encoding="utf-8")


def save_questions(questions: list, job: str, ts: str = "") -> int:
    """把一批题沉淀进题库（同题只累加次数，不重复存）。返回新增条数。"""
    import time as _t
    ts = ts or _t.strftime("%Y-%m-%d %H:%M")
    rows = load_bank()
    index = {_norm(r.get("q", "")): r for r in rows}
    added = 0
    for q in questions or []:
        k = _norm(q)
        if not k:
            continue
        hit = index.get(k)
        if hit:
            hit["used"] = int(hit.get("used", 1)) + 1
            continue
        row = {"q": q, "kind": classify(q), "job": job, "ts": ts, "used": 1}
        rows.append(row)
        index[k] = row
        added += 1
    save_bank(rows)
    return added


def bank_stats() -> dict:
    """按分类统计题库。"""
    out = {}
    for r in load_bank():
        k = r.get("kind") or "其它"
        out[k] = out.get(k, 0) + 1
    return out


SEED_PATH = DATA_DIR / "question_bank_seed.json"


def load_seed() -> list:
    """读预置种子题库（data/question_bank_seed.json）。没有就当空。"""
    if SEED_PATH.exists():
        try:
            data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def ensure_seed() -> int:
    """把预置种子题并入题库：同题不重复，已有记录（含用过次数）一律不动。

    幂等 —— 每次进页面调用都安全，返回本次新增条数。
    """
    seeds = load_seed()
    if not seeds:
        return 0
    rows = load_bank()
    index = {_norm(r.get("q", "")): r for r in rows}
    added = 0
    for s in seeds:
        q = (s.get("q") if isinstance(s, dict) else str(s)) or ""
        k = _norm(q)
        if not k or k in index:
            continue
        row = {"q": q,
               "kind": (s.get("kind") if isinstance(s, dict) else "") or classify(q),
               "job": (s.get("job") if isinstance(s, dict) else "") or "通用",
               "ts": "预置",
               "used": 0,
               "src": "seed"}
        rows.append(row)
        index[k] = row
        added += 1
    if added:
        save_bank(rows)
    return added


def row_tag(r: dict) -> str:
    """题库条目的来源标签：预置题 vs 自己练过的题。"""
    if r.get("src") == "seed" and not int(r.get("used", 0) or 0):
        return "预置"
    return "用过 %d 次" % int(r.get("used", 1) or 1)
