# -*- coding: utf-8 -*-
"""
twin_core · 数字人核心（self-distill → digital twin）
=====================================================
把「自我蒸馏」产出的整套档案当人格底座，让分身：

  - 有记忆：读 6 份档案（表达风格 / 分身说明书 / 工作模式 / 画像 / 亮点 / 面试答案）
  - 多轮对话：历史落在 data/twin_chat.json，刷新和关页面都不丢
  - 有边界：只讲档案里的事实，缺的明说，不编数字，硬边界内不替本人表态
  - 可纠偏：你说一句"我不会这么说"，这条纠正会一直生效

设计原则：所有依赖模型的地方都走 ask 回调，模块本身不 import llm，
所以离线测试可以塞假模型进去。
"""
import json
import time
from pathlib import Path

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
CHAT_PATH = DATA_DIR / "twin_chat.json"

# 人格底座：顺序 = 喂给模型的顺序，也是"越靠前越决定像不像本人"
PERSONA_FILES = [
    ("style_guide.md", "表达风格与边界手册"),
    ("clone_brief.md", "数字分身说明书"),
    ("work_style.md", "工作与学习模式"),
    ("profile.md", "个人画像"),
    ("highlights.md", "亮点库"),
    ("interview_answers.md", "面试答案草稿"),
]

HISTORY_TURNS = 8   # 最多带最近 8 轮对话进 prompt（省 token）
MAX_CORRECTIONS = 20


# ============================================================
# 人格底座读取
# ============================================================
def load_persona(data_dir=None) -> dict:
    """读整套档案。返回 {文件名: 内容}，只含真实存在的、且非空的。"""
    base = Path(data_dir) if data_dir else DATA_DIR
    out = {}
    for name, _label in PERSONA_FILES:
        try:
            txt = (base / name).read_text(encoding="utf-8").strip()
        except Exception:
            txt = ""
        if txt:
            out[name] = txt
    return out


# 简历是「事实来源」：蒸馏档案讲的是他怎么想，简历讲的是他做过什么。
RESUME_CANDIDATES = [
    HERE.parent / "简历" / "我的简历.md",
    DATA_DIR / "my_resume.md",
    DATA_DIR / "resume.md",
]


def load_resume(path=None) -> str:
    """读简历原文。读不到返回空串（不报错、不编内容）。"""
    cands = [Path(path)] if path else RESUME_CANDIDATES
    for p in cands:
        try:
            if p and Path(p).is_file():
                txt = Path(p).read_text(encoding="utf-8").strip()
                if txt:
                    return txt
        except Exception:
            continue
    return ""



def readiness(data_dir=None) -> dict:
    """数字人就绪度：缺哪几份档案，别人一眼能看懂。"""
    persona = load_persona(data_dir)
    labels = dict(PERSONA_FILES)
    have = [n for n, _ in PERSONA_FILES if n in persona]
    return {
        "have": have,
        "have_labels": [labels[n] for n in have],
        "missing": [labels[n] for n, _ in PERSONA_FILES if n not in persona],
        "score": len(have),
        "total": len(PERSONA_FILES),
    }


# ============================================================
# 对话状态
# ============================================================
def blank_chat() -> dict:
    return {"v": 1, "created": time.strftime("%Y-%m-%d %H:%M"),
            "messages": [], "corrections": []}


def load_chat(path=None) -> dict:
    p = Path(path) if path else CHAT_PATH
    data = None
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = None
    if not isinstance(data, dict):
        return blank_chat()
    base = blank_chat()
    base.update({k: v for k, v in data.items() if k in base})
    if not isinstance(base.get("messages"), list):
        base["messages"] = []
    if not isinstance(base.get("corrections"), list):
        base["corrections"] = []
    return base


def save_chat(state: dict, path=None):
    p = Path(path) if path else CHAT_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def reset_chat(path=None):
    save_chat(blank_chat(), path)


def add_correction(state: dict, text: str, path=None) -> bool:
    """记一条风格纠正（"我不会这么说 / 别说这种词"）。"""
    t = (text or "").strip()
    if not t:
        return False
    cs = state.setdefault("corrections", [])
    if t in cs:
        return False
    cs.append(t)
    del cs[:-MAX_CORRECTIONS]
    save_chat(state, path)
    return True


# ============================================================
# 人格 prompt
# ============================================================
SYSTEM_TMPL = """你是「{who}」的数字分身，代表他在求职场合说话。

【说话风格】（来自他本人的表达风格手册，优先级最高）
{style}

【分身说明书：定位 / 做事原则 / 什么时候必须停下来问本人】
{clone}

【工作与学习模式】
{work}

【事实底座：只能用这里出现的事实】
{profile}

{highlights}

{interview}

【已经被纠正过的表达（最高优先级，必须遵守）】
{corrections}

硬性规则：
1. 只能使用上面出现过的事实（项目、数字、工具、经历）。没提到的，直接说"这块我还没准备"。
2. 禁止编造任何数字、公司名、奖项、时间、排名。
3. 按【说话风格】说话；风格里写了"不能说"的词，一个字都不许出现。
4. 涉及说明书里【硬边界】的事，不要替本人表态，回答"这个得他本人定"。
5. 长度 60-150 字，第一人称，口语，不用感叹号，不用表情符号。
"""


def build_system(persona: dict, who: str = "本人", corrections=None,
                 resume: str = "") -> str:
    def g(name):
        return (persona or {}).get(name, "").strip() or "（还没有这份档案）"

    cs = corrections or []
    corr = "\n".join(f"- {c}" for c in cs) if cs else "（暂无）"
    base = SYSTEM_TMPL.format(
        who=who or "本人",
        style=g("style_guide.md"), clone=g("clone_brief.md"),
        work=g("work_style.md"), profile=g("profile.md"),
        highlights=g("highlights.md"), interview=g("interview_answers.md"),
        corrections=corr,
    )
    # 简历作为事实来源追加在最后：蒸馏档案负责「像不像」，简历负责「有没有做过」
    r = (resume or "").strip()
    if r:
        base += ("\n\n【简历原文（事实来源，只用于核实经历；没写过的不许编）】\n"
                 + r[:7000])
    return base


def _history_text(messages: list, turns: int = HISTORY_TURNS) -> str:
    tail = (messages or [])[-turns * 2:]
    lines = []
    for m in tail:
        who = "本人问" if m.get("role") == "user" else "分身答"
        lines.append(f"{who}：{m.get('content', '')}")
    return "\n".join(lines)


def reply(state: dict, question: str, ask, persona=None, who: str = "本人",
          path=None) -> str:
    """多轮对话：带上历史和人格底座问一次模型，落库后返回回答。"""
    q = (question or "").strip()
    if not q:
        return ""
    persona = persona if persona is not None else load_persona()
    sys_prompt = build_system(persona, who, state.get("corrections"),
                              resume=load_resume())

    hist = _history_text(state.get("messages"))
    parts = [sys_prompt]
    if hist:
        parts.append("【之前的对话】\n" + hist)
    parts.append("【本次问题】" + q)
    prompt = "\n\n".join(parts)

    try:
        ans = (ask(prompt) or "").strip()
    except Exception as e:
        ans = ""
        state.setdefault("last_error", str(e))
    if not ans:
        ans = "（分身这次没答上来，检查一下 API Key 或稍后再试）"

    state.setdefault("messages", []).append({"role": "user", "content": q})
    state["messages"].append({"role": "assistant", "content": ans})
    del state["messages"][:-200]          # 只留最近 200 条，防止文件无限长
    state["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_chat(state, path)
    return ans
