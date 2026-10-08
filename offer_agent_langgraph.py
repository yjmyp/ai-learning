# -*- coding: utf-8 -*-
"""OfferAgent 投递流程 · LangGraph 图编排版
================================================
为什么写这一版：面试 JD 高频要求「熟悉 LangChain / LangGraph 底层原理」。
自研引擎（offer_agent_core 的 ReAct 循环）能讲概念，但用真实框架把流程
画成一张图，才是硬证据。本文件用 LangGraph StateGraph 重写投递链路：

    load → assess → split → match → gate ──(≥60)──→ generate → check ──(通过)──→ open
                              └( <60 )→ END                  └(禁用词→重写≤3次)→ generate
                                                             └(放弃)→ END

特点：
  1. 状态 = TypedDict（LangGraph 的 State 概念），每个节点只改自己那几格
  2. 条件边 = 门禁（匹配分）/ 自纠错（话术重写），这就是 Graph 的"分支"
  3. 所有节点复用 offer_agent_tools 的注册表工具（一个都不新造）
  4. 每步记 trace（可观测），打印完整执行轨迹

用法：
    python offer_agent_langgraph.py --selftest   # 不调 LLM，只验证图能编译能跑通
    python offer_agent_langgraph.py --job "岗位名"  # 真实跑一个岗位（会调 DeepSeek）
"""
import json
import os
import sys
from typing import TypedDict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "offeragent"))

from langgraph.graph import StateGraph, END

from offer_agent_tools import build_registry
from offer_agent_core import gate_verdict
import store


# ============================================================
# 1) State：整个流程共享的一张"工作表"（LangGraph 的核心概念）
# ============================================================
class JobState(TypedDict):
    job_name: str          # 岗位名（从岗位库选的）
    jd_text: str           # JD 原文
    profile: str           # 个人画像
    quality: dict          # assess_job 结果：{score, verdict, flags}
    split: dict            # split_jd 结果：职责/要求/其他
    match: dict            # match_job 结果：{score, report, verdict}
    talk: str              # generate_talk 产出的话术
    talk_ok: bool          # check_talk 是否通过
    talk_attempts: int     # 话术重写次数（防死循环）
    open_result: dict      # open_application 结果
    trace: list            # 每步记录（可观测）


# ============================================================
# 2) 节点：每个节点 = 图里的一个"工位"，只改自己负责的那几格
# ============================================================
def _log(state: JobState, name: str, note: str) -> JobState:
    state["trace"].append({"step": name, "note": note})
    return state


def node_load(state: JobState) -> JobState:
    reg = build_registry()
    state["profile"] = store.read_text(store.PROFILE_PATH) or store.read_text(store.ME_PATH)
    jd_path = store.JDS_DIR / (state["job_name"] + ".txt")
    state["jd_text"] = store.read_text(jd_path, "")
    return _log(state, "load", "读画像 %.0f 字 / JD %.0f 字" % (len(state["profile"]), len(state["jd_text"])))


def node_assess(state: JobState) -> JobState:
    reg = build_registry()
    state["quality"] = reg["assess_job"].func(jd_text=state["jd_text"])
    return _log(state, "assess_job", "质量分 %s · %s" % (state["quality"].get("score"), state["quality"].get("verdict")))


def node_split(state: JobState) -> JobState:
    reg = build_registry()
    state["split"] = reg["split_jd"].func(jd_text=state["jd_text"])
    return _log(state, "split_jd", "职责/要求/其他 三块已拆解")


def node_match(state: JobState) -> JobState:
    reg = build_registry()
    state["match"] = reg["match_job"].func(profile=state["profile"], jd_text=state["jd_text"])
    return _log(state, "match_job", "匹配分 %s" % state["match"].get("score"))


def node_gate(state: JobState) -> JobState:
    """门禁节点：只判断，不执行。决定走哪条边。"""
    score = state["match"].get("score")
    state["trace"].append({"step": "gate", "note": gate_verdict(score)})
    return state


def node_generate(state: JobState) -> JobState:
    reg = build_registry()
    r = reg["generate_talk"].func(profile=state["profile"], jd_text=state["jd_text"], variant="boss")
    state["talk"] = r["talk"]
    state["talk_attempts"] = state.get("talk_attempts", 0) + 1
    return _log(state, "generate_talk", "第 %d 版话术 %d 字" % (state["talk_attempts"], len(state["talk"])))


def node_check(state: JobState) -> JobState:
    reg = build_registry()
    r = reg["check_talk"].func(text=state["talk"], variant="boss")
    state["talk_ok"] = bool(r["ok"])
    return _log(state, "check_talk", "通过" if state["talk_ok"] else "命中禁用词：%s" % (r.get("hits") or []))


def node_open(state: JobState) -> JobState:
    reg = build_registry()
    url = state["jd_text"]  # 真实版：从岗位 meta 拿 url
    meta = store.load_meta(state["job_name"]) if hasattr(store, "load_meta") else None
    if meta:
        url = meta.get("url") or meta.get("source_url") or url
    state["open_result"] = reg["open_application"].func(url=url)
    return _log(state, "open_application", state["open_result"].get("note", ""))


# ============================================================
# 3) 条件路由（LangGraph 的 conditional_edges）
# ============================================================
def gate_router(state: JobState) -> str:
    """门禁：匹配分 < 60 → 结束（不建议投）；否则 → 写话术。"""
    score = state["match"].get("score")
    if score is None or score < 60:
        return "fail"
    return "pass"


def check_router(state: JobState) -> str:
    """话术校验：通过 → 投递；命中禁用词 → 重写（≤3 次）；超限 → 放弃。"""
    if state.get("talk_ok"):
        return "ok"
    if state.get("talk_attempts", 0) >= 3:
        return "giveup"
    return "retry"


# ============================================================
# 4) 构图（这就是"把流程画成图"）
# ============================================================
def build_app():
    g = StateGraph(JobState)
    g.add_node("load", node_load)
    g.add_node("assess", node_assess)
    g.add_node("split", node_split)
    g.add_node("match", node_match)
    g.add_node("gate", node_gate)
    g.add_node("generate", node_generate)
    g.add_node("check", node_check)
    g.add_node("open", node_open)

    g.set_entry_point("load")
    g.add_edge("load", "assess")
    g.add_edge("assess", "split")
    g.add_edge("split", "match")
    g.add_edge("match", "gate")
    g.add_conditional_edges("gate", gate_router,
                            {"pass": "generate", "fail": END})
    g.add_edge("generate", "check")
    g.add_conditional_edges("check", check_router,
                            {"ok": "open", "retry": "generate", "giveup": END})
    g.add_edge("open", END)
    return g.compile()


# ============================================================
# 5) 入口：自测（不调 LLM）/ 真实跑
# ============================================================
def selftest():
    """只验证图能编译 + 结构正确 + 路由逻辑对，不调用真实 LLM。"""
    app = build_app()
    print("图编译 OK")
    # 门禁路由逻辑（离线验证，不跑图）
    for score, expect in [(88, "pass"), (45, "fail"), (None, "fail")]:
        got = gate_router({"match": {"score": score}})
        assert got == expect, (score, got, expect)
    print("gate_router：88→pass / 45→fail / None→fail  ✓")
    for ok, n, expect in [(True, 1, "ok"), (False, 1, "retry"), (False, 3, "giveup")]:
        got = check_router({"talk_ok": ok, "talk_attempts": n})
        assert got == expect, (ok, n, got, expect)
    print("check_router：通过→ok / 1次失败→retry / 3次→giveup  ✓")
    nodes = sorted(app.get_graph().nodes.keys()) if hasattr(app, "get_graph") else None
    print("节点：", nodes)
    print("selftest OK")


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        selftest()
        return
    job_name = None
    if "--job" in args:
        job_name = args[args.index("--job") + 1]
    if not job_name:
        jobs = store.list_jobs()
        if not jobs:
            print("岗位库为空，先加岗位。")
            return
        job_name = jobs[0][0]
        print("未指定岗位，默认取第一个：%s" % job_name)

    app = build_app()
    print("=== 开始执行 LangGraph 投递流程 · 岗位：%s ===" % job_name)
    final = app.invoke({
        "job_name": job_name,
        "jd_text": "",
        "profile": "",
        "quality": {},
        "split": {},
        "match": {},
        "talk": "",
        "talk_ok": False,
        "talk_attempts": 0,
        "open_result": {},
        "trace": [],
    })
    print("\n=== 执行轨迹（可观测） ===")
    for step in final["trace"]:
        print("  · %-16s %s" % (step["step"], step["note"]))
    print("\n=== 结果 ===")
    if final.get("match", {}).get("score") is not None:
        print("匹配分：%s ｜ %s" % (final["match"]["score"], final["match"].get("verdict")))
    if final.get("talk"):
        print("话术（第 %d 版，%d 字）：%s" % (final["talk_attempts"], len(final["talk"]), final["talk"][:80]))
    if final.get("open_result"):
        print("投递：%s" % final["open_result"].get("note", ""))
    print("\n结束。")


if __name__ == "__main__":
    main()
