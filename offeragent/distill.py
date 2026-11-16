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
import difflib
import hashlib
import json
import time
from pathlib import Path

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
STATE_PATH = DATA_DIR / "distill_state.json"
VERSIONS_DIR = DATA_DIR / "distill_versions"
VERSION_KEEP = 20

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

    (
        "项目深挖（一个项目说透）",
        "挑最拿得出手的那个项目，按真实发生的过程说。这一轮采的东西直接决定数字人能不能替你把项目讲清楚。",
        [
            ("q16", "这个项目当时要解决什么问题？谁在用、不用会怎样？（一两句）"),
            ("q17", "你具体做了哪几步？每一步用了什么工具 / 模型 / 库？"),
            ("q18", "结果怎么衡量？有数字就写数字（命中率、耗时、条数、人数）。"),
            ("q19", "你中途放弃过什么方案？为什么放弃？"),
            ("q20", "最难的一个坑是什么？你最后怎么定位到原因的？"),
        ],
    ),
    (
        "表达风格与边界",
        "最后一轮决定数字人说话像不像你、以及哪些事它必须停下来问你。",
        [
            ("q21", "你平时说话什么风格？（长句还是短句、爱不爱用术语、有没有口头禅）"),
            ("q22", "有哪些话你绝对不会说？（不想吹的、觉得假的、说不出口的）"),
            ("q23", "哪些事别人或者 AI 绝对不能替你决定？"),
            ("q24", "如果只让别人记住你三点，是哪三点？"),
        ],
    ),
]

ALL_QUESTIONS = [(k, q) for _, _, qs in ROUNDS for k, q in qs]

# 一次蒸馏产出的档案清单（顺序 = 模型输出顺序）
OUTPUT_NAMES = ["profile.md", "highlights.md", "interview_answers.md", "gaps.md",
                "work_style.md", "clone_brief.md", "style_guide.md"]


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

把它整理成七份 Markdown 文档。**硬性要求：只用他给出的话，不许编造经历、数字、公司名、性格。
没提到的就写"（未提供，待补）"，宁可留空，不要替他发挥。**

严格按下面的顺序和分隔符输出，分隔符必须单独一行（等号数量一致）：

=== profile.md ===
（结构化画像，二级标题分节：基本信息 / 技能清单 / 项目经历 / 求职目标 / 优势 / 不足。
项目经历里，主要那个项目要按 STAR 展开成三级小节：背景 / 任务 / 行动 / 结果 / 取舍 / 踩坑，
每节只写他有原话支撑的内容，缺的写「（未提供，待补）」；原始数字一律保留）

=== highlights.md ===
（3 到 6 条最值得对 HR 讲的亮点，每条一句话，带数字，不夸张。编号列表）

=== interview_answers.md ===
（三段问答，二级标题：## 30 秒自我介绍 / ## 为什么投这个方向 / ## 项目里最难的点。
每个答案第一人称口语，60 到 150 字，能直接背出来）

=== gaps.md ===
（差距清单：目标是 2027 校招 AI/Agent 系统交付方向，对照他现在有的，列 3 到 6 条。
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
要求：像给一个新同事的交接文档，具体、可执行，不要形容词堆砌。
表达风格一节必须写清：句子长短、要不要用术语、有没有口头禅、以及他明确说过"绝不会说"的话）

=== style_guide.md ===
（**表达风格与边界手册**，给数字人当"说话约束"用。用二级标题分：）
## 说话风格（句子长短 / 术语密度 / 口头禅 / 有没有语气词）
## 绝对不能说的话（把他原话列出来，一条一行）
## 必须停下来问本人的事（列条目，这是硬边界）
## 三个记忆点（别人该记住他的三点，每条一句话）
要求：全部来自他的原话，不许替他润色成"更好的版本"）
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
    names = OUTPUT_NAMES
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


def _sha(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:12]


def save_version(state: dict, outputs: dict) -> str:
    """把本次生成的 6 份档案 + 当时的回答存成一个版本，返回版本 id。

    为什么要存回答：档案里的每句结论都必须能追到用户自己说过的话。
    模型不产引用时，至少做到"这一版基于哪些回答"可回查，避免档案越改越像编的。
    """
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    vid = stamp
    d = VERSIONS_DIR / vid
    n = 1
    while d.exists():                    # 同一秒生成两次也不覆盖
        n += 1
        vid = f"{stamp}-{n}"
        d = VERSIONS_DIR / vid
    d.mkdir(parents=True, exist_ok=True)

    answers = dict(state.get("answers") or {})
    followups = dict(state.get("followups") or {})
    for name, content in (outputs or {}).items():
        (d / name).write_text(content or "", encoding="utf-8")
    (d / "answers.json").write_text(
        json.dumps({"answers": answers, "followups": followups},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    answered = [k for k, v in answers.items() if str(v or "").strip()]
    manifest = {
        "version": vid,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "answered": len(answered),
        "total": len(answers),
        "answer_keys": answered,
        "files": {name: {"sha1": _sha(content), "chars": len(content or "")}
                  for name, content in (outputs or {}).items()},
    }
    (d / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _prune_versions()
    return vid


def _prune_versions():
    try:
        dirs = sorted((p for p in VERSIONS_DIR.iterdir() if p.is_dir()),
                      key=lambda p: p.name, reverse=True)
        for p in dirs[VERSION_KEEP:]:
            import shutil
            shutil.rmtree(p, ignore_errors=True)
    except Exception:
        pass


def list_versions(limit: int = VERSION_KEEP) -> list:
    """返回版本列表（新→旧）。只读 manifest，不加载大文本。"""
    out = []
    try:
        dirs = sorted((p for p in VERSIONS_DIR.iterdir() if p.is_dir()),
                      key=lambda p: p.name, reverse=True)
    except Exception:
        return out
    for d in dirs[:max(1, int(limit or VERSION_KEEP))]:
        try:
            m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        except Exception:
            m = {"version": d.name, "created_at": d.name, "answered": 0, "total": 0}
        m["version"] = m.get("version") or d.name
        out.append(m)
    return out


def load_version(version: str) -> dict:
    """读一个版本：manifest + 每份档案内容 + 当时的回答。"""
    d = VERSIONS_DIR / str(version)
    if not d.is_dir():
        return {}
    try:
        manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    except Exception:
        manifest = {"version": str(version)}
    files = {}
    for p in d.glob("*.md"):
        try:
            files[p.name] = p.read_text(encoding="utf-8")
        except Exception:
            continue
    try:
        answers = json.loads((d / "answers.json").read_text(encoding="utf-8"))
    except Exception:
        answers = {}
    return {"manifest": manifest, "files": files, "answers": answers}


def diff_versions(old: str, new: str, max_chars: int = 12000) -> str:
    """逐份文件做 unified diff，给"这版改了什么"看。"""
    a, b = load_version(old), load_version(new)
    if not a or not b:
        return ""
    chunks = []
    for name in sorted(set(a["files"]) | set(b["files"])):
        d = difflib.unified_diff(
            (a["files"].get(name) or "").splitlines(),
            (b["files"].get(name) or "").splitlines(),
            fromfile=f"{old}/{name}", tofile=f"{new}/{name}", lineterm="", n=2)
        text = "\n".join(d).strip()
        if text:
            chunks.append(text)
    out = "\n\n".join(chunks)
    return out[:max_chars] + ("\n…（已截断）" if len(out) > max_chars else "")


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
    try:
        save_version(state, outputs)
    except Exception:
        pass          # 版本存档失败不能影响本次生成
    return outputs
