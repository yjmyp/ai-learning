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
