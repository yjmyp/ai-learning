# 代码包：内容生成与数字分身（蒸馏 / 简历生成 / 持久化）

> 内容包括：自我蒸馏（画像生成/聊天）、数字分身（HR 问答）、简历问答生成与清洗、PDF 生成、OCR/文件读取、邮件解析、GitHub 数据同步。目标是让 AI 讲透「把用户变成结构化画像 → 复用到投递/分身」这条线。

## 怎么喂
把本文件全文复制给 DeepSeek，开头加一句：
> 「先读完全文代码，再按我的水平逐块讲解，一次一小步，先框架后填空，不直接给完整答案。」

## 包含的文件

| 文件 | 行数 | 说明 |
|---|---|---|
| `offeragent/distill.py` | 229 | 见下方代码 |
| `offeragent/distill_chat.py` | 124 | 见下方代码 |
| `offeragent/self_distill.py` | 120 | 见下方代码 |
| `offeragent/digital_twin.py` | 177 | 见下方代码 |
| `offeragent/resume_builder.py` | 160 | 见下方代码 |
| `offeragent/resume_clean.py` | 65 | 见下方代码 |
| `offeragent/make_resume_pdf.py` | 99 | 见下方代码 |
| `offeragent/doc_io.py` | 92 | 见下方代码 |
| `offeragent/inbox_parse.py` | 56 | 见下方代码 |
| `offeragent/sync_data.py` | 197 | 见下方代码 |

**合计 1319 行**（约 5KB），在 DeepSeek 上下文内。

---

## ===== offeragent/distill.py（229 行）=====

```python
# -*- coding: utf-8 -*-
"""
distill · 自我蒸馏模块
======================
分 4 轮问答把你自己蒸馏成结构化档案，产出 4 份文件（都存在 data/）：

  profile.md            结构化画像（供匹配分析用）
  highlights.md         亮点库（供话术用）
  interview_answers.md  面试答案草稿（自我介绍 / 为什么这个方向 / 项目最难的点）
  gaps.md               差距清单（目标要求 vs 你现在有的 + 补法）

状态存在 data/distill_state.json，随时可以中断，下次接着填。
设计原则：不编事实。所有结论必须来自用户自己的回答。
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
STATE_PATH = DATA_DIR / "distill_state.json"

# ============================================================
# 四个轮次的问题
# ============================================================
# 设计依据：能力事实（做过的）+ 心理维度（动机、压力反应、价值观）
#          + 协作维度（沟通、分工、决策）+ 模式维度（学习路径、启动方式、能量曲线）
# 目标是产出能"替你做事"的说明书，所以每轮都问可观察的行为，不问自我评价。
ROUNDS = [
    (
        "事实与作品",
        "先把你做过的事说清楚。不用修饰词，说数字和事实。",
        [
            ("q1", "最拿得出手的两件事分别是什么？（项目名 + 一句话说明它做什么）"),
            ("q2", "这两件事能给出什么具体数字？（多少条数据、多少命中率、几天做完）"),
            ("q3", "有上线或能演示的东西吗？链接是什么？"),
        ],
    ),
    (
        "能力与边界",
        "这一轮说能力和边界。诚实比好听重要，写不出可以空着。",
        [
            ("q4", "哪件事你做起来最顺、最有把握？为什么？"),
            ("q5", "哪一步最容易卡住？（调 bug、写新功能、看懂别人的代码……）"),
            ("q6", "有哪些技术是你没做过、但别人简历上常写的？"),
        ],
    ),
    (
        "工作与学习模式",
        "这一轮很重要：说清你实际上怎么干活、怎么学东西。照实说，不用说得好看。",
        [
            ("q7", "拿到一个从没做过的新任务，你第一步做什么？"
                   "（先把方案想清楚 / 直接动手试 / 先搜参考 / 先问人）"),
            ("q8", "学一个新东西时你通常怎么学？"
                   "（看官方文档 / 看视频 / 抄改现成代码 / 做最小 demo / 找人问）"),
            ("q9", "什么情况下你效率最高？什么情况下最容易卡住不动？"
                   "（时间段、环境、任务类型、有没有人催）"),
        ],
    ),
    (
        "动机与压力",
        "这一轮问动机和你扛压时的真实反应，用来判断你适合什么团队。",
        [
            ("q10", "你为什么想做这个方向？是好奇、想挣钱、想被认可，还是别的？"),
            ("q11", "卡住或者做失败的时候，你通常怎么反应？"
                   "（硬扛 / 换任务缓缓 / 找人聊 / 停几天）"),
            ("q12", "你最不能接受的工作是什么样的？"
                   "（长期加班 / 无意义重复 / 没人带 / 目标老变 / 单独干）"),
        ],
    ),
    (
        "协作与决策",
        "最后一轮问协作和决策习惯，这部分决定别人怎么跟你配合。",
        [
            ("q13", "和别人一起做东西时，你喜欢哪种分工？"
                   "（各做一块最后合 / 频繁同步 / 别人定方向我来执行 / 我来定方向）"),
            ("q14", "做选择时你靠什么？（数据对比 / 直觉 / 问别人 / 列清单打分）"),
            ("q15", "同学、队友或者朋友说过你什么？好的和不好的都说说。"),
        ],
    ),
]

ALL_QUESTIONS = [(k, q) for _, _, qs in ROUNDS for k, q in qs]


# ============================================================
# 状态读写
# ============================================================
def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"answers": {}, "followups": {}}


def save_state(state: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def progress(state: dict):
    """返回 (已回答数, 总题数, 百分比)"""
    done = sum(1 for k, _ in ALL_QUESTIONS if state["answers"].get(k, "").strip())
    total = len(ALL_QUESTIONS)
    return done, total, int(done / total * 100)


# ============================================================
# 追问：挑回答最含糊的那条，让模型问一个更具体的问题
# ============================================================
FOLLOWUP_PROMPT = """下面是求职者对几个问题的回答。挑其中一条最含糊、最缺具体信息的，
写一个追问，逼他说出具体细节（数字、工具名、时间、结果）。
要求：只输出这一个问题，一句话，不要解释、不要点评、不要鼓励。如果所有回答都已经很具体，输出"（这轮够了）"。"""


def make_followup(state: dict, round_index: int, ask_model) -> str:
    _, _, qs = ROUNDS[round_index]
    lines = []
    for key, q in qs:
        a = state["answers"].get(key, "").strip()
        if a:
            lines.append(f"问：{q}\n答：{a}")
    if not lines:
        return ""
    try:
        return ask_model(FOLLOWUP_PROMPT + "\n\n" + "\n\n".join(lines)).strip()
    except Exception:
        return ""


# ============================================================
# 生成四份产物
# ============================================================
OUTPUT_PROMPT = """你是资深职业顾问，同时懂一点组织心理学。下面是求职者对 15 个问题的原始回答（口语、可能零散）。

把它整理成六份 Markdown 文档。**硬性要求：只用他给出的话，不许编造经历、数字、公司名、性格。
没提到的就写"（未提供，待补）"，宁可留空，不要替他发挥。**

严格按下面的顺序和分隔符输出，分隔符必须单独一行（等号数量一致）：

=== profile.md ===
（结构化画像，二级标题分节：基本信息 / 技能清单 / 项目经历 / 求职目标 / 优势 / 不足。
项目经历保留原始数字）

=== highlights.md ===
（3 到 6 条最值得对 HR 讲的亮点，每条一句话，带数字，不夸张。编号列表）

=== interview_answers.md ===
（三段问答，二级标题：## 30 秒自我介绍 / ## 为什么投这个方向 / ## 项目里最难的点。
每个答案第一人称口语，60 到 150 字，能直接背出来）

=== gaps.md ===
（差距清单：目标是 AI 应用开发实习，对照他现在有的，列 3 到 6 条。
表格三列：差距 / 怎么补 / 大概多久。
"怎么补"可以给通用建议（例如"读官方文档后做一个最小 demo"），但不要写成他已经做过的事；
"大概多久"给区间估计，并标注这是估计）

=== work_style.md ===
（**工作与学习模式说明书**。这是给"未来要和他协作的人或 agent"看的，必须可操作，不是性格描述。
用二级标题分这几节：
## 怎么启动一个新任务
## 怎么学新东西
## 什么条件下效率高
## 卡点特征（他卡住时是什么表现，别人怎么帮他最快）
## 协作偏好（分工方式、同步频率）
## 决策依据
## 不能接受的工作方式
每节 2 到 4 句，只写他回答里能支撑的内容）

=== clone_brief.md ===
（**数字分身说明书**：压缩成一份"如果本人不在，照着这份代他做事"的指令。用二级标题分：
## 一句话定位
## 他的表达风格（怎么说话、避免什么）
## 做事原则（先做什么、怎么取舍）
## 遇到不确定时怎么做（问谁、按什么判断、什么时候停）
## 硬边界（哪些事不能替他决定）
## 他的常用素材（可复用的经历和数字，列成条目）
要求：像给一个新同事的交接文档，具体、可执行，不要形容词堆砌）
"""


def build_materials(state: dict) -> str:
    parts = []
    for key, q in ALL_QUESTIONS:
        a = state["answers"].get(key, "").strip()
        parts.append(f"问：{q}\n答：{a if a else '（未回答）'}")
    fu = state.get("followups", {})
    for k, v in fu.items():
        if v:
            parts.append(f"补充追问 {k}：{v}")
    return "\n\n".join(parts)


def split_outputs(text: str) -> dict:
    """把模型输出按 === 分隔符切成 6 份。"""
    names = ["profile.md", "highlights.md", "interview_answers.md", "gaps.md",
             "work_style.md", "clone_brief.md"]
    out, current, buf = {}, None, []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("===") and s.endswith("==="):
            if current:
                out[current] = "\n".join(buf).strip()
            inner = s.strip("= ").strip()
            current = inner if inner in names else None
            buf = []
            continue
        if current:
            buf.append(line)
    if current:
        out[current] = "\n".join(buf).strip()
    return out


def distill(state: dict, ask_model, out_dir: Path = None) -> dict:
    """跑一次生成，把 6 份文件写进 out_dir（默认 data/）。返回 {文件名: 内容}。"""
    text = ask_model(OUTPUT_PROMPT + "\n\n" + build_materials(state))
    outputs = split_outputs(text)
    if not outputs:
        raise RuntimeError("模型输出里没找到分隔符，生成失败")
    target = Path(out_dir) if out_dir else DATA_DIR
    target.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (target / name).write_text(content, encoding="utf-8")
    return outputs
```

## ===== offeragent/distill_chat.py（124 行）=====

```python
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
```

## ===== offeragent/self_distill.py（120 行）=====

```python
# -*- coding: utf-8 -*-
"""
self_distill.py —— Self-Distill 第一步：读 me.txt → 调大模型 → 生成个人画像

v1 完成定义：跑通「读文件 → 调模型 → 存 profile.md」，输出一份像“我”的画像。

读这份文件时，你要能回答三个问题（守则第 4 条要求的“讲得出”）：
  1. 输入是什么？ → offeragent/me.txt 里的文字
  2. 输出是什么？ → offeragent/profile.md（模型生成的个人画像）
  3. 失败会怎样？ → 文件不存在 / 没 key / 网络断 / 模型报错，分别在哪一行崩
"""
import os
import sys

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BASE_DIR)
ME_PATH = os.path.join(BASE_DIR, "me.txt")
OUT_PATH = os.path.join(BASE_DIR, "profile.md")

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"


def load_api_key():
    """取 key：环境变量 → 根目录 local_key.py（不把 key 写死在代码里）"""
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key

    local_key = os.path.join(REPO_ROOT, "local_key.py")
    if os.path.exists(local_key):
        ns = {}
        with open(local_key, encoding="utf-8") as f:
            exec(f.read(), ns)          # 执行这个文件，把里面的变量取出来
        return str(ns.get("API_KEY", "")).strip()
    return ""


def read_me(path=ME_PATH):
    """读素材：和你今天写的 practice_02.py 是同一件事"""
    with open(path, encoding="utf-8") as f:
        return f.read()


PROFILE_SECTIONS = """1. 一句话定位（你是谁，一句话说清）
2. 优势（每条必须带 me.txt 里的具体事实或数字）
3. 短板（诚实，不许安慰）
4. 适配岗位方向（按匹配度排序，给理由）"""

# ===== prompt 模板（改动实验 2 改这里；{me} 和 {sections} 会被自动填进去）=====
PROMPT_TEMPLATE = """你是一位做过大量技术岗招聘的职业顾问，擅长从原始材料里提炼真实的个人画像。

下面是一个学生的个人素材：

<素材>
{me}
</素材>

请严格按以下板块输出画像：
{sections}

硬性要求：
1. 每个结论都要引用素材里的具体事实（项目名、数字、技术栈），不许空泛
2. 素材里没有的信息写“未知”，不要编造
3. 语言直接，不要励志，不要安慰
4. 每个结论前必须标注【事实】或【推断】，判定标准：
   【事实】= 素材里直接写出的客观信息（学校、项目、数字、技术栈、做过/没做过什么）
   【推断】= 涉及未来、他人反应、能力评价、竞争力的判断
   示例：素材写"算法只完成 8 题" → 【事实】算法只完成 8 题
        由此推出"笔试过不了" → 【推断】笔试大概率过不了
   如果一句话里既有事实又有推断，拆成两句分别标注
"""


def call_llm(prompt, api_key):
    """把 prompt 发给 DeepSeek，拿回回答"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    r = requests.post(API_URL, headers=headers, json=data, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def main():
    api_key = load_api_key()
    if not api_key:
        print("找不到 API key：检查根目录 local_key.py 或环境变量 DEEPSEEK_API_KEY")
        sys.exit(1)

    me = read_me()
    print(f"[1/3] 读完 me.txt：{len(me)} 个字符")

    prompt = PROMPT_TEMPLATE.format(me=me, sections=PROFILE_SECTIONS)
    print(f"[2/3] prompt 拼好：{len(prompt)} 个字符，正在调模型 ...")

    try:
        profile = call_llm(prompt, api_key)
    except Exception as e:
        print(f"[2/3] 调模型失败：{e}")
        sys.exit(1)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(profile)

    print(f"[3/3] 画像已保存：{OUT_PATH}")
    print("-" * 40)
    print(profile)


if __name__ == "__main__":
    main()
```

## ===== offeragent/digital_twin.py（177 行）=====

```python
# -*- coding: utf-8 -*-
"""
digital_twin · 数字分身（合规版）
================================
不是替你本人去面试——是替你完成所有「准备与复盘」，
把真人留给你自己。四个能力：

  make_intro         按目标公司定制 3 个时长的自我介绍（30s/60s/90s）
  questions_to_ask   基于画像 + JD 的反问清单（分四类）
  twin_answer        「扮演我」模式：分身只用画像事实回答，供你学参考话术
  save_review        面试复盘入库（data/reviews.jsonl，可追溯）
  evolve_profile     复盘 → 提炼「被认可/被挑战」→ 回写画像（数字分身的记忆）
  job_radar          反向岗位雷达：从画像反推适合的岗位类型/关键词/城市

硬性要求：所有生成只基于画像里的真实事实，禁止替用户编造经历、数字、奖项。
"""
import json
import time
from pathlib import Path

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
REVIEWS_PATH = DATA_DIR / "reviews.jsonl"

INTRO_PROMPT = """你是求职教练。为下面的求职者针对【目标公司】定制自我介绍。

要求：
1. 只使用画像里的事实，禁止编造任何经历、数字、项目、奖项
2. 三个时长版本，每个都要自然口语、不像背稿：
   - 30 秒版（约 90 字）：身份 + 一句最相关亮点 + 一句为什么想投这家
   - 60 秒版（约 180 字）：身份 + 最相关的 1-2 段经历（怎么做+结果）+ 与这家公司的关系
   - 90 秒版（约 270 字）：完整叙事 + 一个可迁移能力 + 求职意愿
3. 重点讲"和这家公司最相关"的点，不是"最厉害"的点
4. 结尾不要"谢谢聆听"这类套话

输出格式：
【30 秒版】
...
【60 秒版】
...
【90 秒版】
...

【求职者画像】
"""

ASK_BACK_PROMPT = """你是求职教练。为下面的求职者针对【目标岗位 JD】生成反问清单。

要求：
1. 10 个问题，分四类：岗位与工作内容（3）/ 团队与技术栈（3）/ 成长与转正（2）/ 业务与公司（2）
2. 问题要结合他的画像特点（网络工程 × AI 应用），能体现他做过功课
3. 禁止问"薪资多少""加班多不多"这类会让印象减分的问题
4. 编号输出，每行一个：数字. 问题（类别）

【求职者画像】
"""

TWIN_ANSWER_PROMPT = """你现在是「求职者数字分身」，代表下面的求职者回答问题。

规则：
1. 只能用画像里的事实回答；画像里没有的，就明确说"这个我还没准备好"或给合理推测但标注是推测
2. 语气是第一人称、像真实求职者（学生、坦诚、不吹）
3. 回答里可以带具体数字（只限画像里有的）
4. 如果问题跟画像完全不相关，就回答"这个不在我目前的准备范围内"
5. 回答长度 50-150 字

【求职者画像】
"""

RADAR_PROMPT = """你是求职方向分析师。从下面的画像中反推「最适合他的岗位雷达」。

输出：
## 最佳岗位类型（3 类，说明为什么匹配他的画像）
## 关键词组合（3 组，用于搜岗）
## 推荐城市与公司类型
## 加分叙事点（2-3 个他在投递/面试中必须主动讲的优势）
## 避坑（1-2 个不适合的方向）

要求：全部基于画像事实推断，不编造市场数据。
【求职者画像】
"""

EVOLVE_PROMPT = """下面是求职者的一份面试复盘记录。请提炼成「画像更新建议」。

输出（总计不超过 200 字）：
## 被认可
（面试中他做得好/被肯定的点，1-2 条）
## 被挑战
（被追问/答不上的点，1-2 条，要具体）
## 画像更新
（1-2 条可直接写进画像的新事实或改进项，格式：技能/项目/优势 任选其一 + 一句话）

要求：只基于复盘原文，不脑补。
【复盘记录】
"""


def read_text(p):
    try:
        return Path(p).read_text(encoding="utf-8")
    except Exception:
        return ""


def write_text(p, s):
    try:
        Path(p).write_text(s, encoding="utf-8")
        return True
    except Exception:
        return False


# ---------- 1. 定制自我介绍 ----------

def make_intro(profile: str, company: str, jd: str, ask) -> str:
    """公司 + JD → 三版自我介绍。ask: fn(prompt)->str"""
    prompt = (INTRO_PROMPT + profile + "\n\n【目标公司】" + company
              + "\n\n【目标岗位 JD】\n" + (jd or "（无 JD，按公司方向写）"))
    return (ask(prompt) or "").strip()


# ---------- 2. 反问清单 ----------

def questions_to_ask(profile: str, jd: str, ask) -> str:
    prompt = ASK_BACK_PROMPT + profile + "\n\n【目标岗位 JD】\n" + jd
    return (ask(prompt) or "").strip()


# ---------- 3. 扮演我模式 ----------

def twin_answer(profile: str, question: str, ask) -> str:
    prompt = TWIN_ANSWER_PROMPT + profile + "\n\n【问题】" + question
    return (ask(prompt) or "").strip()


# ---------- 4. 面试复盘入库 + 进化画像 ----------

def save_review(job: str, company: str, text: str) -> dict:
    """存一条复盘。返回记录 dict。"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rec = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "date": time.strftime("%Y-%m-%d"),
        "job": job,
        "company": company,
        "review": text.strip(),
    }
    with REVIEWS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def load_reviews() -> list:
    if not REVIEWS_PATH.exists():
        return []
    out = []
    for line in REVIEWS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return list(reversed(out))


def evolve_profile(profile: str, review_text: str, ask) -> str:
    """复盘 → 提炼更新建议（不自动改画像，由用户确认后写）。"""
    return (ask(EVOLVE_PROMPT + review_text) or "").strip()


# ---------- 5. 反向岗位雷达 ----------

def job_radar(profile: str, ask) -> str:
    return (ask(RADAR_PROMPT + profile) or "").strip()
```

## ===== offeragent/resume_builder.py（160 行）=====

```python
# -*- coding: utf-8 -*-
"""
resume_builder · 问答式生成简历
===============================
你没有现成简历、或者旧简历太烂不想改的时候，用这个：一次问一题，答完生成一份草稿。

设计要点：
  1. 一次只问一题（避免面对长表单就关掉）
  2. 每题都写清"为什么问这个"和"怎么答才有用"（给例子）
  3. 答完可以生成草稿；草稿会明确标注"哪些内容是空的需要你补"，不会自己编
  4. 状态存 data/resume_build.json，随时中断续答
"""
import io
import json
from pathlib import Path

from resume_clean import clean  # noqa: E402  简历文本清洗（去掉本地路径乱码）

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
STATE_PATH = DATA_DIR / "resume_build.json"
PHOTO_PATH = HERE.parent / "简历" / "照片.jpg"

# (键, 问题, 为什么问 / 怎么答)
QUESTIONS = [
    ("name", "你的姓名？", "简历抬头要用。"),
    ("school", "学校、专业、届别？", "例：南京邮电大学 / 网络工程 / 2027 届。"),
    ("contact", "手机号和邮箱？", "HR 联系你要用，写一个常用的。"),
    ("photo", "有没有能用的一寸照 / 半身照？",
     "很多简历要贴照片。这一步会直接出现上传按钮，传了我就存成「简历/照片.jpg」，"
     "简历和公开名片都会自动用上；没有就点「跳过这题」，简历照样能用。"),
    ("available", "什么时候能到岗、一周几天、能实习多久？",
     "例：2026 年 9 月下旬到岗，一周 4-5 天，能实习 3-6 个月。实习岗特别看这个。"),
    ("skills", "你会哪些技术？按熟练程度说，会就是会，不会就是不会。",
     "例：Python 能独立写完整脚本；Chroma 用过；LangChain 没做过。**没做过的别写。**"),
    ("proj1_name", "第一个项目叫什么？一句话说它是做什么的？",
     "例：RAG 知识库问答系统，把我自己的笔记变成能问答的知识库。"),
    ("proj1_tech", "这个项目用了什么技术？", "例：Python / bge-small / Chroma / FastAPI / Streamlit。"),
    ("proj1_data", "这个项目有什么具体数字？（多少条数据、多少命中率、几天做完）",
     "数字是简历里最值钱的东西。例：11 篇资料切 254 块，自建 12 条评估集，top-3 命中 83%。"),
    ("proj1_hard", "这个项目里你解决了什么难的问题？",
     "面试会追问这里。例：检索总不准，定位到是切分把定义块稀释了。"),
    ("proj2", "还有第二个项目/经历吗？（课程设计、竞赛、开源都算）",
     "没有就写「无」，我会在简历里留空位。"),
    ("target", "你想找什么岗位？",
     "例：AI 应用开发实习（RAG / 大模型应用 / Agent 方向）。"),
    ("about", "一句话形容你自己（不要写性格，写你做事的方式）",
     "反例：性格开朗、学习能力强。正例：习惯用数据验证效果，项目跑通再迭代。"),
]


def load() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"answers": {}, "idx": 0}


def save(state: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def current(state: dict):
    i = state.get("idx", 0)
    if i >= len(QUESTIONS):
        return None
    return {"k": QUESTIONS[i][0], "q": QUESTIONS[i][1], "why": QUESTIONS[i][2]}


def answer(state: dict, value: str):
    q = current(state)
    if not q:
        return
    # 用户可能把本地文件拖进来，先把路径乱码清掉再存
    state["answers"][q["k"]] = clean((value or "").strip())[0]
    state["idx"] = state.get("idx", 0) + 1
    save(state)


def has_photo() -> bool:
    return PHOTO_PATH.exists() and PHOTO_PATH.is_file()


def save_photo(data: bytes) -> Path:
    """上传的照片统一处理成标准证件照（3:4 竖版、居中偏上裁剪、缩到 600×800），
    名片页和简历共用这一张；处理失败（坏图/无 PIL）则原样保存，不阻塞上传。"""
    PHOTO_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image, ImageOps
        im = Image.open(io.BytesIO(data))
        im = ImageOps.exif_transpose(im)  # 修正手机照片旋转
        im = im.convert("RGB")
        w, h = im.size
        target = 3 / 4  # 证件照宽高比（宽:高）
        if w / h > target:  # 太宽 → 裁左右，保住中间的竖条
            nw = int(h * target)
            x0 = max(0, (w - nw) // 2)
            im = im.crop((x0, 0, x0 + nw, h))
        else:  # 太高 → 裁上下，焦点偏上 35%（大头照脸偏上，保住脸）
            nh = int(w / target)
            y_top = max(0, int((h - nh) * 0.35))
            im = im.crop((0, y_top, w, y_top + nh))
        im = im.resize((600, 800), Image.LANCZOS)
        im.save(PHOTO_PATH, "JPEG", quality=92)
    except Exception:
        PHOTO_PATH.write_bytes(data)  # 处理失败就存原图
    return PHOTO_PATH


def reset():
    save({"answers": {}, "idx": 0})


def progress(state: dict):
    done = sum(1 for k, _, _ in QUESTIONS if state["answers"].get(k))
    return done, len(QUESTIONS)


BUILD_PROMPT = """把下面的问答内容整理成一份**中文技术实习简历草稿**（Markdown）。

硬性要求：
1. **只能用他答过的内容**。没答的字段写「（未提供）」，绝对不要编造经历、数字、学校、奖项。
2. 项目描述按 STAR 思路压缩：做什么 → 用什么做的 → 结果（有数字就放数字，没数字就不编）。
3. 不要写性格和软素质（"性格开朗""学习能力强"一律不写）。
4. 结尾加一个「⚠️ 待补充」小节，列出哪些字段是空的、建议怎么补。
5. **绝对不要写文件路径、盘符、`file://` 链接、`%E7%AE%80` 这类编码乱码**；
   要放链接就放 https 开头的公开链接（GitHub / 部署地址）。

结构：
# 姓名 · 求职意向
## 基本信息（学校专业届别 / 电话邮箱 / 到岗时间）
## 技能
## 项目经历
## 其他经历
## 一句话自我介绍
## ⚠️ 待补充

问答内容：
"""


def build(state: dict, ask_model) -> str:
    body = "\n".join(f"问：{q}\n答：{state['answers'].get(k) or '（未答）'}"
                     for k, q, _ in QUESTIONS)
    raw = (ask_model(BUILD_PROMPT + body) or "").strip()
    text, _ = clean(raw)          # 兜底：模型有时会把路径抄进正文
    if has_photo():
        note = "> 📷 照片已就绪（简历/照片.jpg）——打印版简历会自动带上这张照片。"
    else:
        note = "> 📷 照片未提供——需要的话到「我的简历」页上传一张即可。"
    # 插在标题之后，方便看简历的人第一时间知道照片情况
    lines = text.splitlines()
    if lines and lines[0].startswith("#"):
        return "\n".join([lines[0], "", note] + lines[1:])
    return note + "\n\n" + text
```

## ===== offeragent/resume_clean.py（65 行）=====

```python
# -*- coding: utf-8 -*-
"""
resume_clean · 简历文本清洗
===========================
解决的问题：简历里混进本地文件路径的乱码，例如
    file:///C:/Users/29947/Documents/Codex/ai-learning/%E7%AE%80%E5%8E%86/%E4%BD%99%E5%89%91-%E7%AE%80%E5%8E%86-AI%E5%B...
这种串是「把本地文件拖进浏览器/编辑器」时生成的，对人没有意义，出现在简历里只会显得不专业。

清洗规则（只删明显无意义的，不动正文）：
  1. file:///... 整条链接删掉
  2. Windows 绝对路径 C:\\Users\\... 或 C:/Users/... 删掉
  3. 孤立的百分号编码串（%E7%AE%80 这类连续 3 组以上）删掉
  4. 零宽字符、控制字符、连续 4 个以上空行清理

用法：
    from resume_clean import clean
    text, report = clean(text)      # report 列出都删了什么，方便提示用户
"""
import re

RE_FILE_URL = re.compile(r"file:///\S+")
RE_WIN_PATH = re.compile(r"[A-Za-z]:[\\/](?:[^\s，。；)】\]]+[\\/])*[^\s，。；)】\]]*")
RE_PCT_RUN = re.compile(r"(?:%[0-9A-Fa-f]{2}){3,}")
RE_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]")
RE_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
RE_BLANK_RUN = re.compile(r"\n{4,}")


def clean(text: str) -> tuple:
    """返回 (清洗后的文本, [(规则名, 命中次数, 样例)])。"""
    if not text:
        return text or "", []
    report = []

    def _sub(pattern, text_in, name):
        hits = pattern.findall(text_in)
        if hits:
            report.append((name, len(hits), str(hits[0])[:60]))
            text_in = pattern.sub("", text_in)
        return text_in

    out = _sub(RE_FILE_URL, text, "本地文件链接 file:///")
    out = _sub(RE_WIN_PATH, out, "本机绝对路径（C:\\…）")
    out = _sub(RE_PCT_RUN, out, "百分号编码乱码（%E7%AE%80…）")
    out = _sub(RE_ZERO_WIDTH, out, "零宽字符")
    out = _sub(RE_CTRL, out, "控制字符")

    blank_hits = len(RE_BLANK_RUN.findall(out))
    if blank_hits:
        report.append(("多余空行", blank_hits, ""))
        out = RE_BLANK_RUN.sub("\n\n\n", out)

    out = "\n".join(line.rstrip() for line in out.splitlines())
    out = re.sub(r"\n[ \t]*[-*]\s*\n", "\n", out)
    return out, report


def has_junk(text: str) -> bool:
    """快速判断有没有需要清洗的东西。"""
    if not text:
        return False
    return bool(RE_FILE_URL.search(text) or RE_WIN_PATH.search(text)
                or RE_PCT_RUN.search(text) or RE_ZERO_WIDTH.search(text)
                or RE_CTRL.search(text))
```

## ===== offeragent/make_resume_pdf.py（99 行）=====

```python
# -*- coding: utf-8 -*-
r"""
make_resume_pdf · 简历 HTML → PDF（支持多模板 + 自动嵌照片）
========================================================
用法：
    python offeragent\make_resume_pdf.py                      # 默认 classic 模板
    python offeragent\make_resume_pdf.py --template sidebar
    python offeragent\make_resume_pdf.py --template compact --out 简历\试试.pdf
    python offeragent\make_resume_pdf.py --template sidebar --no-default   # 只看，不换默认

说明：
  · 三种模板：classic（单栏）/ sidebar（左侧栏）/ compact（极简黑白）
  · 有 简历/照片.jpg（或 offeragent/assets/avatar.png）就自动嵌进照片位
  · 生成的同名 PDF 会同时写一份「默认版」到 简历/余剑-简历-AI应用开发实习-v3.pdf，
    名片页的下载按钮就是取这份；--no-default 可以跳过
"""
import argparse
import base64
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent
RESUME_DIR = REPO / "简历"
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import browser_fetch as bf          # noqa: E402
import resume_templates as rt       # noqa: E402

DEFAULT_OUT = RESUME_DIR / "余剑-简历-AI应用开发实习-v3.pdf"


def html_to_pdf(html: str, out: Path) -> int:
    """用无头 Edge 把 HTML 打成 A4 PDF，返回 KB 数。"""
    tmp = RESUME_DIR / "_render_tmp.html"
    tmp.write_text(html, encoding="utf-8")
    if not bf.launch(headless=True):
        raise SystemExit("❌ Edge 启动失败")
    ws = bf._new_tab(tmp.as_uri())
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    time.sleep(4)
    res = cdp.call("Page.printToPDF", {
        "printBackground": True,
        "paperWidth": 8.27, "paperHeight": 11.69,          # A4
        "marginTop": 0.35, "marginBottom": 0.35,
        "marginLeft": 0.30, "marginRight": 0.30,
        "preferCSSPageSize": False,
    }, timeout=60)
    cdp.close()
    tmp.unlink(missing_ok=True)
    data = base64.b64decode(res.get("data", ""))
    if not data:
        raise SystemExit("❌ 没拿到 PDF 数据")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return max(1, round(len(data) / 1024))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default="classic", choices=list(rt.TEMPLATES.keys()))
    ap.add_argument("--out", default="")
    ap.add_argument("--no-default", action="store_true",
                    help="只生成模板版，不覆盖名片页用的默认 PDF")
    args = ap.parse_args()

    photo = rt.find_photo()
    print("模板：", args.template, "|", rt.TEMPLATES[args.template])
    print("照片：", photo if photo else "未找到（PDF 右上角会没有照片）")

    html = rt.render_with_photo(args.template)
    out = Path(args.out) if args.out else RESUME_DIR / (
        "余剑-简历-AI应用开发实习-v3.pdf" if args.template == "classic"
        else f"余剑-简历-AI应用开发实习-v3-{args.template}.pdf")
    kb = html_to_pdf(html, out)
    print(f"✅ 已生成：{out}（{kb} KB）")

    try:
        from pypdf import PdfReader
        pages = len(PdfReader(str(out)).pages)
        print("页数：", pages, "（1 页最佳）")
    except Exception:
        pages = None

    if not args.no_default and out != DEFAULT_OUT:
        shutil.copyfile(out, DEFAULT_OUT)
        print(f"↪ 已同步为默认版：{DEFAULT_OUT.name}（名片页下载的就是这份）")


if __name__ == "__main__":
    main()
```

## ===== offeragent/doc_io.py（92 行）=====

```python
# -*- coding: utf-8 -*-
"""
doc_io · 简历/资料读取（PDF / Word / 文本 / 图片 OCR）
======================================================
支持格式与实现方式：
  .pdf            pypdf 逐页抽文字（扫描版 PDF 抽不出文字，会提示）
  .docx           python-docx 逐段抽文字
  .txt / .md      多编码尝试（utf-8-sig → utf-8 → gb18030）
  .png/.jpg/.jpeg/.webp/.bmp   RapidOCR 离线识别（中英混排）

设计原则：**识别失败要说清楚失败原因和替代方案**，不要静默返回空字符串。
"""
import io

TEXT_EXT = {".txt", ".md", ".markdown"}
DOC_EXT = {".docx"}
PDF_EXT = {".pdf"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
ALL_EXT = TEXT_EXT | DOC_EXT | PDF_EXT | IMG_EXT


def _read_text(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="ignore")


def _read_pdf(data: bytes) -> tuple:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    pages = [(p.extract_text() or "") for p in reader.pages]
    text = "\n".join(pages).strip()
    if len(text) < 40:
        return text, ("这份 PDF 里几乎抽不到文字，可能是扫描/图片版。"
                      "可以改用截图上传（走 OCR），或直接把文字粘进来。")
    return text, ""


def _read_docx(data: bytes) -> tuple:
    from docx import Document
    doc = Document(io.BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts).strip(), ""


def _read_image(data: bytes) -> tuple:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception:
        return "", ("没装 OCR 组件。在本机跑一次："
                    "python -m pip install rapidocr-onnxruntime")
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp()) / "upload.png"
    tmp.write_bytes(data)
    try:
        engine = RapidOCR()
        result, _ = engine(str(tmp))
    except Exception as e:
        return "", f"OCR 识别失败：{type(e).__name__}"
    lines = [x[1] for x in (result or [])]
    text = "\n".join(lines).strip()
    warn = "" if len(text) > 20 else "OCR 只识别出很少文字，图片可能太模糊或字太小。"
    return text, warn


def read_any(data: bytes, filename: str) -> dict:
    """统一入口。返回 {text, method, warning}"""
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext in TEXT_EXT:
        return {"text": _read_text(data), "method": "文本直读", "warning": ""}
    if ext in PDF_EXT:
        t, w = _read_pdf(data)
        return {"text": t, "method": "PDF 抽文字", "warning": w}
    if ext in DOC_EXT:
        t, w = _read_docx(data)
        return {"text": t, "method": "Word 抽文字", "warning": w}
    if ext in IMG_EXT:
        t, w = _read_image(data)
        return {"text": t, "method": "图片 OCR", "warning": w}
    return {"text": "", "method": "不支持",
            "warning": f"不支持的文件类型 {ext or '（无扩展名）'}。"
                       f"支持：{'、'.join(sorted(ALL_EXT))}"}
```

## ===== offeragent/inbox_parse.py（56 行）=====

```python
# -*- coding: utf-8 -*-
"""
inbox_parse · 邮件/消息 → 自动识别状态
=======================================
不接邮箱、不要授权（隐私第一）。你把邮件或聊天内容粘贴进来，程序帮你判断：
  · 这是什么类型的消息（面试邀请 / 拒信 / 笔试 / HR 沟通 / 其他）
  · 涉及哪家公司、哪个岗位、什么时间
  · 要不要把岗位库里的状态改掉（只给建议，改不改你点）

为什么用粘贴而不是读邮箱：
  1. 读邮箱需要 OAuth 授权，权限过大，一旦泄露影响面很高
  2. 招聘邮件里常含身份证号、手机号等敏感信息，不该进第三方服务
  3. 粘贴方式零权限、零留存（除非你自己点保存），出错也不会造成损失
"""
import re

CLASSIFY_PROMPT = """判断下面这段消息属于哪一类，并抽取关键信息。

类别只能是这五种之一：
面试邀请 / 拒信 / 笔试或测评 / HR 沟通 / 其他

严格按四行输出，没有的信息留空：
类型：xxx
公司：
岗位：
时间：（面试时间或截止时间，原文怎么写就怎么抄）

不要解释，不要多余的话。

消息原文：
"""

HINTS = {
    "面试邀请": "建议把状态改成「面试中」，并尽快回复确认时间",
    "拒信": "建议把状态改成「已拒」。如果连着被拒 3 个以上，去「投递记录」跑一次归因",
    "笔试或测评": "建议先确认截止时间，再决定要不要做",
    "HR 沟通": "建议把状态保持「已投」，留意后续消息",
    "其他": "先看清楚再说，不急着改状态",
}


def classify(text: str, ask_model) -> dict:
    """返回 {type, company, job, time, hint}"""
    out = ask_model(CLASSIFY_PROMPT + text[:4000]) or ""
    info = {"type": "", "company": "", "job": "", "time": ""}
    for line in out.splitlines():
        s = line.strip().lstrip("*-· ").strip()
        for key, field in [("类型", "type"), ("公司", "company"),
                           ("岗位", "job"), ("时间", "time")]:
            if s.startswith(key):
                info[field] = re.sub(r"^" + key + r"[：:]\s*", "", s).strip()
    if info["type"] not in HINTS:
        info["type"] = "其他"
    info["hint"] = HINTS[info["type"]]
    return info
```

## ===== offeragent/sync_data.py（197 行）=====

```python
# -*- coding: utf-8 -*-
"""
sync_data.py —— OfferAgent 数据持久化（Streamlit Cloud 无持久磁盘的根治方案）
============================================================================
问题：Streamlit Cloud 每次重启都回到仓库代码，data/ 里的岗位库/记忆/日志全部丢失。
根治：把 data/ 放进私有 GitHub 仓库（yjmyp/offeragent-data），本地是权威，云端启动自动拉取。

三种模式：
  python sync_data.py push       本地 data/ 打包 → 提交私有仓库（zip 备份，需网络可达 github.com）
  python sync_data.py pull       git 拉取私有仓库 zip 恢复；git 不通自动降级 api_pull
  python sync_data.py api_pull   走 GitHub API 拉 offeragent_data.json 数据包解包（云端推荐）

环境变量（或 .streamlit/secrets.toml）：
  GITHUB_PAT   访问私有仓库的 token（没有时本机走 Git Credential Manager）
  DATA_REPO    私有仓库名（默认 yjmyp/offeragent-data）

敏感隔离：edge_profile（BOSS 登录态 534MB）、shots/、*.png 永不进入仓库。
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SKIP_DIRS = {"edge_profile", "shots", "distill_test", "__pycache__"}
SKIP_EXTS = (".png", ".jpg", ".jpeg")


def _repo_url() -> str:
    pat = os.environ.get("GITHUB_PAT", "")
    repo = os.environ.get("DATA_REPO", "yjmyp/offeragent-data")
    if pat:
        return f"https://{pat}@github.com/{repo}.git"
    return f"https://github.com/{repo}.git"


def _git(*args, cwd=None):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 失败：{r.stderr.strip()[:300]}")
    return r


def _zip_data(dest_dir: Path) -> Path:
    """把 data/ 打包成 zip（排除敏感/超大项；zip 内路径以 offeragent/data/ 开头防逃逸）。"""
    out = dest_dir / f"offeragent_data_{time.strftime('%Y%m%d_%H%M%S')}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(DATA):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in files:
                if fn.lower().endswith(SKIP_EXTS):
                    continue
                full = Path(root) / fn
                z.write(full, Path("offeragent") / full.relative_to(HERE))
    return out


def _unzip_data(zip_path: Path, dest: Path = HERE) -> int:
    """只解压 offeragent/data/ 前缀条目到 dest（防路径逃逸）。"""
    restored = 0
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if not n.startswith("offeragent/data/"):
                continue
            target = dest / n
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(n) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            restored += 1
    return restored


def _unzip_data_into(zip_path: Path, repo_dir: Path):
    """解压 zip 的 data 部分到仓库工作区（push 用）。"""
    with zipfile.ZipFile(zip_path) as z:
        for n in z.namelist():
            if not n.startswith("offeragent/data/"):
                continue
            target = repo_dir / n
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(n) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


def push():
    """本地是权威：打包 data/ → clone 私有仓库 → 覆盖 → push。"""
    pat = os.environ.get("GITHUB_PAT", "")
    if not pat:
        print("ℹ️ 未配置 GITHUB_PAT，改用本机 git 凭据（Git Credential Manager）")
    print("📦 打包本地 data/ …")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        z = _zip_data(tmp)
        repo_dir = tmp / "repo"
        print("⏬ clone 私有仓库 …")
        _git("clone", "--depth", "1", _repo_url(), str(repo_dir))
        bk_dir = repo_dir / "offeragent" / "backups"
        bk_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(z, bk_dir / z.name)
        data_dir = repo_dir / "offeragent" / "data"
        if data_dir.exists():
            for p in data_dir.iterdir():
                if p.name == ".gitkeep":
                    continue
                p.unlink() if p.is_file() else shutil.rmtree(p)
        _unzip_data_into(z, repo_dir)
        _git("add", "-A", cwd=repo_dir)
        _git("commit", "-m", f"data sync {time.strftime('%Y-%m-%d %H:%M:%S')}", cwd=repo_dir)
        print("🚀 push …")
        _git("push", "origin", "HEAD", cwd=repo_dir)
    print("✅ 数据已同步到私有仓库")


def _git_pull():
    """git 模式：clone 私有仓库 → 用最新 zip 恢复。"""
    print("⏬ clone 私有仓库 …")
    with tempfile.TemporaryDirectory() as td:
        repo_dir = Path(td) / "repo"
        _git("clone", "--depth", "1", _repo_url(), str(repo_dir))
        zips = sorted((repo_dir / "offeragent" / "backups").glob("*.zip"))
        if not zips:
            raise RuntimeError("私有仓库里没有数据备份 zip（先在本地跑 push）")
        n = _unzip_data(zips[-1])
        print(f"✅ git 恢复 {n} 个文件")


def _api_pull_data(pat: str) -> int:
    """GitHub Contents API 拉 offeragent_data.json → 解包回 data/（云端推荐，无需 git）。"""
    repo = os.environ.get("DATA_REPO", "yjmyp/offeragent-data")
    url = f"https://api.github.com/repos/{repo}/contents/offeragent_data.json"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {pat}",
                                               "User-Agent": "offeragent"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        meta = json.load(resp)
    pack = json.loads(base64.b64decode(meta["content"]))
    restored = 0
    for rel, content in pack.get("files", {}).items():
        # rel 形如 offeragent/data/...（相对项目根），HERE 已是 offeragent/，去掉前缀防路径重复
        relp = Path(rel)
        if relp.parts and relp.parts[0] == "offeragent":
            relp = Path(*relp.parts[1:])
        target = HERE / relp
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str) and content.startswith("b64:"):
            target.write_bytes(base64.b64decode(content[4:]))
        else:
            target.write_text(content, encoding="utf-8")
        restored += 1
    return restored


def api_pull():
    pat = os.environ.get("GITHUB_PAT", "")
    if not pat:
        print("❌ api_pull 需要 GITHUB_PAT（Secrets / 环境变量）")
        sys.exit(1)
    print("⬇️ API 拉取数据包 …")
    n = _api_pull_data(pat)
    print(f"✅ 已恢复 {n} 个文件（岗位库/画像/报告/日志）")


def pull():
    """git 优先，失败自动降级 api_pull。"""
    pat = os.environ.get("GITHUB_PAT", "")
    if not pat:
        print("ℹ️ 未配置 GITHUB_PAT，改用本机 git 凭据（Git Credential Manager）")
    try:
        _git_pull()
    except Exception as e:
        print(f"⚠️ git 拉取失败（{str(e)[:100]}），降级 api_pull")
        if pat:
            n = _api_pull_data(pat)
            print(f"✅ API 恢复 {n} 个文件")
        else:
            print("❌ 无 GITHUB_PAT 无法降级：网络恢复后重试，或配置 PAT")
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "push":
        push()
    elif len(sys.argv) >= 2 and sys.argv[1] == "pull":
        pull()
    elif len(sys.argv) >= 2 and sys.argv[1] == "api_pull":
        api_pull()
    else:
        print("用法：python sync_data.py push | pull | api_pull\n"
              "环境变量：GITHUB_PAT、DATA_REPO（默认 yjmyp/offeragent-data）")
```
