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
                              gate_verdict, Tool)
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
}
WORKER_TOOLS = {
    "岗位分析师": {"assess_job", "split_jd", "match_job"},
    "话术专家": {"generate_talk", "check_talk"},
    "投递复盘员": {"funnel", "needs_followup", "review_status"},
}

SUPERVISOR_SYSTEM = """你是一个求职流程的「主管」Agent。你手下有三个子 Agent，只能通过工具 dispatch 调用：
- 角色「岗位分析师」：评估岗位质量、拆解 JD、计算画像与 JD 的匹配度
- 角色「话术专家」：生成投递话术、校验话术禁用词
- 角色「投递复盘员」：复盘投递漏斗转化率、查跟进规则（投递复盘用）

工作方式：
1. 第一步：调用 dispatch 分派「岗位分析师」（role="岗位分析师"），task 里附上岗位 JD 和求职者画像，让它完成 评估质量→拆解JD→算匹配度 三步
2. 拿到分析师结果后，第二步：调用 dispatch 分派「话术专家」（role="话术专家"），让它基于画像和 JD 生成并校验话术
3. 需要复盘投递进度时，可再分派「投递复盘员」（role="投递复盘员"），task 里附上各状态岗位计数（如 {"待投":5,"已投":2,"面试中":1,"Offer":1}）
4. 全部子结果拿到后，给最终中文汇总：岗位质量结论、匹配分（含门禁投递建议）、最终话术、下一步建议

调用格式（必须遵守）：需要子 Agent 时，只输出一行合法 JSON，不要用 XML / DSML / 其他任何格式：
{"tool": "dispatch", "args": {"role": "岗位分析师", "task": "子任务说明"}}
输出 JSON 之外不要写任何多余文字。子任务说明里要把需要的文本（JD / 画像 / 岗位计数）完整附上。"""


def worker_registry(role: str, base_registry: dict) -> dict:
    """按角色过滤全量注册表 → 子 Agent 只能用自己角色的工具。"""
    allowed = WORKER_TOOLS.get(role, set())
    return {n: t for n, t in base_registry.items() if n in allowed}


WORKER_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "offeragent", "data", "memory_worker.db")


def run_worker(role: str, task: str, base_registry: dict, db_path: str = None) -> tuple:
    """跑一个子 Agent（独立状态 + 独立记忆库，防止子 Agent 抽取的事实污染用户画像库）。"""
    from agent_memory import Memory
    mem = Memory(db_path=db_path or WORKER_DB)
    mem.extract_facts("我是余剑，南京邮电大学网络工程2027届，AI应用开发实习生，正在多Agent求职流程中")
    state = AgentState(memory=mem, budget=8)
    reg = worker_registry(role, base_registry)
    full_task = WORKER_SYSTEMS[role] + "\n\n【你的任务】\n" + task
    final, state = run_agent(full_task, reg, state)
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
        "把子任务分派给子 Agent（角色：岗位分析师 / 话术专家）。子 Agent 会自主跑自己的工具链并返回结果摘要。",
        {"role": "子 Agent 角色名：岗位分析师 或 话术专家",
         "task": "交给子 Agent 的子任务说明（要具体，含需要分析的文本）"},
        _dispatch)}

    final, state = run_agent(task, reg, state, system_text=SUPERVISOR_SYSTEM)
    return final, state


if __name__ == "__main__":
    print("多 Agent 协作模块加载 OK")
    print("角色：", list(WORKER_SYSTEMS))
    print("主管工具：dispatch")
