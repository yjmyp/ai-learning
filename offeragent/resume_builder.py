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
