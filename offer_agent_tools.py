# -*- coding: utf-8 -*-
"""
offer_agent_tools.py —— 把 OfferAgent 现有能力注册成 Agent 工具
=================================================================
关键设计：**一个都不新造**——把 OfferAgent 已经写好的函数（岗位质量 7 规则、
JD 解析、漏斗、话术 v5、话术校验）包装成统一 schema 的工具，Agent 通过注册表发现并调用。

工具清单：
  纯规则（免费、确定性、可解释）: assess_job / split_jd / check_talk / funnel / needs_followup
  LLM 工具（内部调一次模型）   : match_job / generate_talk
  执行动作（human_confirm）    : open_application（打开岗位链接，投递前必须人确认）
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "offeragent"))

import requests
from local_key import API_KEY
from offer_agent_core import Tool, make_registry, gate_verdict

import job_quality
import job_detail
import pipeline
import prompts
import apply_assist


def _ask_model(prompt, *materials):
    """工具内部的 LLM 调用。
    Key 优先级：环境变量 DEEPSEEK_API_KEY（Streamlit 部署时由 Secrets 注入）→ local_key.py（本地 CLI）。
    """
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        try:
            from local_key import API_KEY
            key = API_KEY
        except Exception:
            raise RuntimeError("未找到 DEEPSEEK_API_KEY（环境变量或 local_key.py）")
    messages = [{"role": "user", "content": prompt}]
    for m in materials:
        if m and m.strip():
            messages.append({"role": "user", "content": m})
    from offer_agent_core import call_llm      # 复用引擎的重试 + usage 逻辑
    content, _usage = call_llm(messages)
    return content


# ============================================================
# 纯规则工具（复用 offeragent 现成函数，一个都不新造）
# ============================================================

def _tool_assess_job(jd_text: str) -> dict:
    """岗位质量评估：JD 过短/无公司/薪资异常/模板复读/挂太久/无链接。"""
    job = {"jd": jd_text, "extra": "", "company": "示例公司", "city": "南京",
           "salary": "", "posted_days": 0, "url": "https://example.com/job"}
    r = job_quality.assess(job)
    return {"score": r["score"], "verdict": r["verdict"],
            "flags": [f["problem"] for f in r["flags"]]}


def _tool_split_jd(jd_text: str) -> dict:
    """把 JD 拆成 职责 / 要求 / 其他 三块。"""
    return job_detail.split_jd(jd_text)


def _tool_check_talk(text: str, variant: str = "boss") -> dict:
    """检查话术有没有禁用词（书面八股/报年级/堆技能）。"""
    hits = prompts.check_talk(text, variant)
    return {"ok": not hits, "hits": hits}


def _tool_funnel(states_json: str) -> dict:
    """输入岗位状态计数 JSON（如 {"待投":5,"已投":2,"面试中":1,"Offer":1}），算转化率。"""
    try:
        counts = json.loads(states_json)
    except json.JSONDecodeError:
        return {"error": "states_json 不是合法 JSON"}
    jobs = []
    for st, n in counts.items():
        for _ in range(int(n)):
            jobs.append((f"岗位{n}", {"status": st}, ""))
    return pipeline.funnel(jobs)


def _tool_needs_followup(days: int = 7) -> str:
    """说明：跟进提醒需要岗位数据，这里返回规则说明。"""
    return {"note": f"已投超过 {days} 天无动静的岗位需要跟进",
            "rule": "状态='已投' 且 距投递日 >= days 天 → 建议跟进"}


# ============================================================
# LLM 工具（内部调一次模型，把能力封装成可编排工具）
# ============================================================

def _tool_match_job(profile: str, jd_text: str) -> dict:
    """画像 vs JD 匹配分析：输出匹配度分 + 结构化报告摘要 + 投递建议（匹配分门禁）。"""
    report = _ask_model(prompts.PROMPT_MATCH, profile, jd_text)
    m = re.search(r"匹配度[:：]?\s*(\d{1,3})\s*%", report)
    score = min(100, max(0, int(m.group(1)))) if m else None
    return {"score": score, "report": report[:900],
            "verdict": gate_verdict(score)}


def _tool_generate_talk(profile: str, jd_text: str, variant: str = "boss") -> dict:
    """生成投递话术（v5 真人风格），命中禁用词自动带反馈重写，返回最终话术。"""
    talk, hits = prompts.generate_talk(_ask_model, variant, profile, jd_text)
    return {"variant": variant, "talk": talk, "banned_hits": hits}


# ============================================================
# 执行动作（human_confirm：停在人确认，发送前那一下永远由人做）
# ============================================================

def _check_url(url: str):
    """投递前自动核验链接：返回 (状态码 or None, 说明)。None = 网络/超时无法访问。"""
    try:
        r = requests.get(url, timeout=10, allow_redirects=True, stream=True,
                         headers={"User-Agent": "Mozilla/5.0"})
        return r.status_code, "正常" if r.status_code < 400 else f"HTTP {r.status_code}"
    except requests.exceptions.RequestException as e:
        return None, f"无法访问（{type(e).__name__}）"


def _tool_forget_fact(fact: str) -> dict:
    """删除一条长期记忆事实（记忆纠错：抽错了 / 过时了可以删）。"""
    from agent_memory import Memory
    mem = Memory(db_path=os.path.join(HERE, "offeragent", "data", "memory.db"))
    ok = mem.forget(fact)
    return {"deleted": ok, "提示": f"已删除事实：{fact}" if ok else f"未找到事实：{fact}"}


def _tool_review_status() -> dict:
    """读取岗位库真实投递状态：各状态计数 + 岗位清单（公司/状态/匹配分）。"""
    jds_dir = os.path.join(HERE, "offeragent", "data", "jds")
    if not os.path.isdir(jds_dir):
        return {"error": f"岗位数据目录不存在：{jds_dir}"}
    counts, items = {}, []
    for p in sorted(os.listdir(jds_dir)):
        if not p.endswith(".meta.json"):
            continue
        name = p[: -len(".meta.json")]
        try:
            meta = json.load(open(os.path.join(jds_dir, p), encoding="utf-8"))
        except Exception:
            continue
        status = meta.get("status", "待投")
        counts[status] = counts.get(status, 0) + 1
        items.append({"岗位": name, "公司": meta.get("company", ""),
                      "状态": status, "匹配分": meta.get("match_score")})
    for st in ("待投", "已投", "面试中", "Offer", "排除"):
        counts.setdefault(st, 0)
    return {"counts": counts, "items": items, "total": sum(counts.values())}


def _tool_open_application(url: str) -> dict:
    """打开岗位投递页面。执行前自动核验链接：失效（404/410）或无法访问 → 不打开、明确提示，避免投空。"""
    code, note = _check_url(url)
    if code is None:
        return {"opened": False, "url": url, "note": f"链接核验失败：{note}——先确认网络或换个入口"}
    if code in (404, 410):
        return {"opened": False, "url": url,
                "note": f"链接已失效（HTTP {code}）：岗位可能已下架，先找真实投递入口，不要投空"}
    ok = apply_assist.open_url(url)
    return {"opened": ok, "url": url, "note": f"链接核验 HTTP {code} 正常，已打开浏览器"}


# ============================================================
# 注册表（Agent 从这里发现工具）
# ============================================================
def build_registry() -> dict:
    return make_registry([
        Tool("assess_job", "评估一个岗位的质量（JD 文本 → 分数/结论/风险标记）",
             {"jd_text": "岗位 JD 全文"}, _tool_assess_job),
        Tool("split_jd", "把 JD 拆成 职责/要求/其他 三块，方便快速看清岗位要什么",
             {"jd_text": "岗位 JD 全文"}, _tool_split_jd),
        Tool("match_job", "对比求职者画像与岗位 JD，输出匹配度和匹配报告",
             {"profile": "求职者画像文本", "jd_text": "岗位 JD 全文"}, _tool_match_job),
        Tool("generate_talk", "为岗位生成投递话术（BOSS/微信版），真人风格、自动去禁用词",
             {"profile": "求职者画像文本", "jd_text": "岗位 JD 全文", "variant": "话术场景：boss/email/referral"}, _tool_generate_talk),
        Tool("check_talk", "检查话术文本里有没有禁用词（书面八股/报年级/堆技能）",
             {"text": "话术文本", "variant": "场景：boss/email/referral"}, _tool_check_talk),
        Tool("funnel", "输入各状态岗位数量 JSON，计算投递漏斗转化率",
             {"states_json": "如 {\"待投\":5,\"已投\":2,\"面试中\":1,\"Offer\":1}"}, _tool_funnel),
        Tool("needs_followup", "查询跟进提醒规则（已投超过 N 天无动静的岗位）",
             {"days": "超过多少天算需要跟进"}, _tool_needs_followup),
        Tool("review_status", "读取岗位库真实投递状态：各状态计数 + 岗位清单（公司/状态/匹配分）",
             {}, _tool_review_status),
        Tool("forget_fact", "删除一条长期记忆事实（记忆纠错）",
             {"fact": {"type": "string", "required": True}}, _tool_forget_fact),
        Tool("open_application", "打开岗位投递链接（执行动作，需用户确认后才会真正打开）",
             {"url": "岗位投递链接"}, _tool_open_application, human_confirm=True),
    ])


if __name__ == "__main__":
    reg = build_registry()
    print(f"注册表共 {len(reg)} 个工具：")
    for t in reg.values():
        print(f"  {'🔒' if t.human_confirm else '  '} {t.name}({list(t.params)})  {'[需用户确认]' if t.human_confirm else ''}")
