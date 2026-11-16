# -*- coding: utf-8 -*-
"""
offer_agent_multi.py —— 多 Agent 协作（Supervisor → 子 Agent 分派）
====================================================================
对应客观差距清单："无子 Agent 协作 / 无跨任务持久规划"。

设计（面试可讲，参考 LangGraph supervisor pattern / CrewAI role-based agents）：
  - 主管（Supervisor）：拆解任务 → 决定把子任务交给谁 → 汇总。只有一个工具：dispatch。
  - 子 Agent（Worker）：每个角色是**独立的 run_agent 实例**（独立状态、独立工具集、独立 system prompt）。
      岗位分析师：assess_job → split_jd → match_job（只做分析）
      话术专家  ：generate_talk → check_talk（只做话术）
  - 记忆：Worker / Supervisor 都接 SQLite（db_path），跨会话记住用户事实。
  - 安全：投递动作（open_application）不在 Worker 工具集里，只在单 Agent 全量流程中由人确认。
"""
from offer_agent_core import (AgentState, run_agent, extract_score,
                              gate_verdict, Tool, GATE_SCORE)
import os

# 子 Agent 角色注册表：角色名 → 系统提示 + 允许的工具子集
WORKER_SYSTEMS = {
    "岗位分析师": (
        "你是 OfferAgent 的「岗位分析师」子 Agent。你的职责：评估岗位质量（assess_job）、"
        "拆解 JD（split_jd）、计算求职者画像与岗位 JD 的匹配度（match_job）。"
        "只做岗位分析，不生成话术。完成后给中文小结：岗位质量结论、匹配分、投递建议（引用工具的 verdict 字段）。"
    ),
    "话术专家": (
        "你是 OfferAgent 的「话术专家」子 Agent。你的职责：根据画像和 JD 生成投递话术（generate_talk）、"
        "校验话术里的禁用词（check_talk）。只做话术，不做岗位分析。完成后给出最终话术全文。"
    ),
    "投递复盘员": (
        "你是 OfferAgent 的「投递复盘员」子 Agent。你的职责：复盘投递进度——用 funnel 计算投递漏斗转化率、"
        "用 needs_followup 查跟进规则（已投超 N 天无动静的岗位要跟进）。"
        "先调用 review_status 读取真实岗位库的投递状态（不用等别人给计数），再用 funnel 算转化率、needs_followup 查跟进规则。"
        "只做复盘分析，不做岗位匹配也不生成话术。完成后给中文小结：各环节转化率、需要跟进的岗位、下一步动作建议。"
    ),
    "评审员": (
        "你是 OfferAgent 的「评审员」子 Agent。你不改写岗位分析，也不重写话术。"
        "你的职责是验收交付包：用 check_talk 检查最终话术是否有禁用词，并检查匹配分、投递建议、话术是否齐全、"
        "是否存在无事实依据的夸大。只报问题和结论，不改写原文。"
        "输出格式必须是：判定：通过/不通过；问题：逐条列出；依据：引用你检查到的工具结果。"
    ),
}
WORKER_TOOLS = {
    "岗位分析师": {"assess_job", "split_jd", "match_job"},
    "话术专家": {"generate_talk", "check_talk"},
    "投递复盘员": {"funnel", "needs_followup", "review_status"},
    "评审员": {"check_talk"},
}

SUPERVISOR_SYSTEM = """你是一个求职流程的「主管」Agent。你手下有四个子 Agent，只能通过工具 dispatch 调用：
- 角色「岗位分析师」：评估岗位质量、拆解 JD、计算画像与 JD 的匹配度
- 角色「话术专家」：生成投递话术、校验话术禁用词
- 角色「评审员」：验收分析结果和最终话术，只报问题，不改写
- 角色「投递复盘员」：复盘投递漏斗转化率、查跟进规则（投递复盘用）

工作方式（按任务选择，不要无脑跑全套）：
- 完整岗位交付包：第一步分派「岗位分析师」，第二步分派「话术专家」，第三步分派「评审员」
- 只复盘投递进度：直接分派「投递复盘员」，不要先跑分析或话术
- 只评估岗位/批量打分：只分派「岗位分析师」
- 全部子结果拿到后，给最终中文汇总：岗位质量结论、匹配分（含门禁投递建议）、最终话术、评审问题、下一步建议

调用格式（必须遵守）：需要子 Agent 时，只输出一行合法 JSON，不要用 XML / DSML / 其他任何格式：
{"tool": "dispatch", "args": {"role": "岗位分析师", "task": "子任务说明"}}
输出 JSON 之外不要写任何多余文字。子任务说明里要把需要的文本（JD / 画像 / 岗位计数）完整附上。"""


def worker_registry(role: str, base_registry: dict) -> dict:
    """按角色过滤全量注册表 → 子 Agent 只能用自己角色的工具。"""
    allowed = WORKER_TOOLS.get(role, set())
    return {n: t for n, t in base_registry.items() if n in allowed}


WORKER_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "offeragent", "data", "memory_worker.db")


def run_worker(role: str, task: str, base_registry: dict, db_path: str = None,
               required_tools: list = None) -> tuple:
    """跑一个子 Agent（独立状态 + 独立记忆库，防止子 Agent 抽取的事实污染用户画像库）。"""
    from agent_memory import Memory
    mem = Memory(db_path=db_path or WORKER_DB)
    mem.extract_facts("我是余剑，南京邮电大学网络工程2027届，AI应用开发实习生，正在多Agent求职流程中")
    state = AgentState(memory=mem, budget=8)
    reg = worker_registry(role, base_registry)
    full_task = WORKER_SYSTEMS[role] + "\n\n【你的任务】\n" + task
    final, state = run_agent(full_task, reg, state, required_tools=required_tools)
    return final, state


def _as_dict(value) -> dict:
    """工具结果可能是 dict，也可能是模型回填后的 repr 字符串。"""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            import ast
            obj = ast.literal_eval(value)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}
    return {}


def _tool_result(state: AgentState, tool_name: str) -> dict:
    """取最后一个成功工具调用的结构化结果；没有就返回空 dict。"""
    for item in reversed(state.trace):
        if item.get("tool") == tool_name and item.get("ok", True):
            return _as_dict(item.get("result"))
    return {}


def _append_dispatch(state: AgentState, role: str, task: str, final: str,
                     worker_state: AgentState, extra: dict = None) -> None:
    """把子 Agent 的结果记进主管 trace，格式与现有日志/统计兼容。"""
    score = extract_score(worker_state.trace)
    worker_ok = not _worker_failed(final)
    prompt_tokens = sum((t.get("tokens") or {}).get("prompt_tokens", 0) or 0
                        for t in worker_state.trace)
    completion_tokens = sum((t.get("tokens") or {}).get("completion_tokens", 0) or 0
                            for t in worker_state.trace)
    payload = {
        "role": role,
        "summary": (final or "")[:600],
        "steps": len(worker_state.trace),
        "match_score": score,
        "verdict": gate_verdict(score),
    }
    if extra:
        payload.update(extra)
    state.trace.append({
        "step": len(state.trace) + 1,
        "tool": "dispatch",
        "args": {"role": role, "task": (task or "")[:800]},
        "ok": worker_ok,
        "result": payload,
        "tokens": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
    })


def _worker_failed(final: str) -> bool:
    """子 Agent 的最终回复是否表示它没有完成（而不是正常交付）。"""
    text = (final or "").strip()
    return any(mark in text for mark in ("任务未完成", "达到最大循环次数", "运行中断"))


def review_job_package(match_score, talk: str, banned_hits, reviewer_text: str = "",
                       reviewer_failed: bool = False) -> dict:
    """确定性验收：不依赖模型心情。模型评审是补充，硬规则才是门禁。"""
    issues = []
    if match_score is None:
        issues.append("缺少匹配分：岗位分析师没有完成 match_job")
    else:
        try:
            score_int = int(match_score)
        except (TypeError, ValueError):
            issues.append(f"匹配分不是有效数字：{match_score!r}")
        else:
            if score_int < GATE_SCORE:
                issues.append(f"匹配分 {score_int} 低于投递门禁 {GATE_SCORE}")
    if not (talk or "").strip():
        issues.append("没有生成可用的投递话术")
    if banned_hits:
        issues.append(f"话术命中禁用词：{banned_hits}")

    text = (reviewer_text or "").strip()
    if reviewer_failed or _worker_failed(text):
        issues.append("评审员没有完成验收（达到预算或运行中断），不能视为通过")
    if text and ("判定：不通过" in text[:300] or "判定:不通过" in text[:300]):
        issues.append("评审员判定不通过，需要按问题清单修改")
    return {"passed": not issues, "issues": issues,
            "gate_score": GATE_SCORE, "reviewer_text": text}


def run_job_pipeline(profile: str, jd_text: str, base_registry: dict,
                     state: AgentState = None, db_path: str = None,
                     job_label: str = "岗位", url: str = "") -> tuple:
    """确定性多 Agent 流水线：岗位分析师 → 话术专家 → 评审员。

    为什么不用让主管自由决定顺序：求职交付包是固定流程，顺序稳定、可测试、
    可审计比“让模型自己排”更重要。主管自主分派模式仍保留，作为探索型入口。
    投递动作不在任何 Worker 工具集里，最后一步仍由人确认。
    """
    from agent_memory import Memory
    if state is None:
        mem = Memory(db_path=db_path)
        mem.extract_facts("我是余剑，南京邮电大学网络工程2027届，AI应用开发实习生，正在用确定性多Agent流水线")
        state = AgentState(memory=mem, budget=3)

    profile = (profile or "")[:2500]
    jd_text = (jd_text or "")[:4000]

    analyst_task = (
        f"【岗位】{job_label}\n【JD】\n{jd_text}\n\n【求职者画像】\n{profile}\n\n"
        "请严格依次调用 assess_job、split_jd、match_job 三个工具，只做岗位分析，不生成话术。"
    )
    analyst_final, analyst_state = run_worker(
        "岗位分析师", analyst_task, base_registry,
        required_tools=["assess_job", "split_jd", "match_job"])
    assess = _tool_result(analyst_state, "assess_job")
    split = _tool_result(analyst_state, "split_jd")
    match = _tool_result(analyst_state, "match_job")
    score = match.get("score")
    if score is None:
        score = extract_score(analyst_state.trace)
    verdict = match.get("verdict") or gate_verdict(score)
    match_report = match.get("report") or analyst_final
    _append_dispatch(state, "岗位分析师", analyst_task, analyst_final, analyst_state,
                     {"match_score": score, "verdict": verdict})

    writer_task = (
        f"【岗位】{job_label}\n【JD】\n{jd_text}\n\n【求职者画像】\n{profile}\n\n"
        f"【岗位分析师结论】\n{match_report[:1600]}\n\n"
        "请严格调用 generate_talk 生成 BOSS 版投递话术，再调用 check_talk 校验。"
        "不要编造简历里没有的经历，不要替用户点击投递。"
    )
    writer_final, writer_state = run_worker(
        "话术专家", writer_task, base_registry,
        required_tools=["generate_talk", "check_talk"])
    talk_result = _tool_result(writer_state, "generate_talk")
    check_result = _tool_result(writer_state, "check_talk")
    talk = talk_result.get("talk") or ""
    banned_hits = talk_result.get("banned_hits") or check_result.get("hits") or []
    _append_dispatch(state, "话术专家", writer_task, writer_final, writer_state,
                     {"talk_preview": talk[:500], "banned_hits": banned_hits})

    reviewer_task = (
        f"【岗位】{job_label}\n【匹配分】{score}\n【投递建议】{verdict}\n"
        f"【岗位分析摘要】\n{match_report[:1200]}\n\n【待评审话术】\n{talk[:2000]}\n\n"
        "请只调用 check_talk 校验这段话术：参数 text 传话术全文，variant 可省略；"
        "拿到结果后按格式输出：判定：通过/不通过；问题：逐条列出。"
        "不要重写话术。"
    )
    reviewer_final, reviewer_state = run_worker(
        "评审员", reviewer_task, base_registry, required_tools=["check_talk"])
    review = review_job_package(score, talk, banned_hits, reviewer_final,
                                reviewer_failed=_worker_failed(reviewer_final))
    _append_dispatch(state, "评审员", reviewer_task, reviewer_final, reviewer_state,
                     {"passed": review["passed"], "issues": review["issues"]})

    quality = assess.get("verdict") or "未评估"
    flags = assess.get("flags") or []
    split_summary = (split.get("duty") or split.get("职责")
                     or split.get("responsibilities") or [])
    review_issues = review["issues"] or ["无"]
    final = (
        f"## 多 Agent 交付包 · {job_label}\n\n"
        f"### 岗位分析\n"
        f"- 质量：{quality}\n"
        f"- 匹配分：{score if score is not None else '缺失'}（{verdict}）\n"
        f"- 风险标记：{flags or '无'}\n"
        f"- JD 职责摘要：{str(split_summary)[:500]}\n\n"
        f"### 投递话术\n{talk or '未生成'}\n\n"
        f"### 评审\n"
        f"- 结论：{'通过' if review['passed'] else '需修改'}\n"
        f"- 问题：{review_issues}\n\n"
        f"### 下一步\n"
        f"- 投递链接：{url or '未提供'}\n"
        f"- 最后一步仍由你确认：核对链接、检查话术、亲手点击投递。"
    )
    state.artifacts = {
        "job_label": job_label, "url": url, "score": score, "verdict": verdict,
        "assess": assess, "split": split, "match": match, "talk": talk,
        "banned_hits": banned_hits, "review": review,
        "worker_finals": {"岗位分析师": analyst_final, "话术专家": writer_final,
                          "评审员": reviewer_final},
    }
    state.memory.add_turn(f"多 Agent 流水线：{job_label}", final[:800])
    return final, state


def run_supervisor(task: str, base_registry: dict, state: AgentState = None,
                   db_path: str = None, budget: int = 10) -> tuple:
    """跑多 Agent 协作流程。返回 (最终回复, state)。

    主管循环（复用 run_agent 引擎）：模型决定 dispatch(role, task) 或直接回答；
    dispatch 内部启动独立子 Agent，子结果回填后主管继续，直到给出最终汇总。
    """
    from agent_memory import Memory
    mem = Memory(db_path=db_path)
    mem.extract_facts("我是余剑，南京邮电大学网络工程2027届，AI应用开发实习生，正在用多Agent求职流程")
    state = state or AgentState(memory=mem, budget=budget)

    def _dispatch(role: str, task: str) -> dict:
        if role not in WORKER_SYSTEMS:
            return {"error": f"未知角色：{role}，可选：{list(WORKER_SYSTEMS)}"}
        final, wstate = run_worker(role, task, base_registry)   # worker 用独立库，不污染主管记忆
        return {"role": role,
                "summary": final[:500],
                "steps": len(wstate.trace),
                "match_score": extract_score(wstate.trace),
                "verdict": gate_verdict(extract_score(wstate.trace))}

    reg = {"dispatch": Tool(
        "dispatch",
        "把子任务分派给子 Agent（角色：岗位分析师 / 话术专家 / 评审员 / 投递复盘员）。"
        "子 Agent 会自主跑自己的工具链并返回结果摘要。",
        {"role": "子 Agent 角色名：岗位分析师 / 话术专家 / 评审员 / 投递复盘员",
         "task": "交给子 Agent 的子任务说明（要具体，含需要分析的文本）"},
        _dispatch)}

    final, state = run_agent(task, reg, state, system_text=SUPERVISOR_SYSTEM)
    return final, state


if __name__ == "__main__":
    print("多 Agent 协作模块加载 OK")
    print("角色：", list(WORKER_SYSTEMS))
    print("主管工具：dispatch")
