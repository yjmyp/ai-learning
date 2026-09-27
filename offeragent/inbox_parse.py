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
