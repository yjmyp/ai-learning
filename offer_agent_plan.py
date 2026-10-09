# -*- coding: utf-8 -*-
"""Plan / Reflect 两个节点 —— 补齐 Agent 四层框架里缺的两层

现状（v1 引擎）：只有 ReAct —— 边走边看，模型自己决定下一步。缺的两层：
  · Planning（Plan-and-Execute）：先给一份显式计划（3-6 步，每步用哪个工具、为什么），
    再执行。好处：过程可解释、可中断、人还能提前拦掉错误路线。
  · Reflection（自评-修正）：收尾时自评"目标达成没、证据够不够、下一步做什么"，
    而不是把模型最后一句直接当结论。

两个函数都是"纯函数 + 一次模型调用"，方便离线 mock 测试：
    make_plan(task, registry, ask_model)    -> dict
    reflect(task, trace, final, ask_model)  -> dict
"""
import json
import re

PLAN_PROMPT = """你是任务规划器。用户给了一个求职相关任务，可用工具如下：

{tools}

请给出一个 3-6 步的执行计划，每一步说明：用哪个工具、要拿到什么结果。
要求：
1. 只输出 JSON 数组，元素形如 [{{"step": 1, "tool": "工具名", "goal": "这一步要拿到什么"}}]
2. tool 必须来自上面列出的工具名，不要发明新工具
3. 执行类工具（标记已投 / 打开投递页）必须放在最后一步，并注明需要人确认
4. 不要解释，不要代码块

用户任务：{task}
"""

REFLECT_PROMPT = """你是任务复盘者。下面是任务目标、实际调用过的工具、以及最终输出。

只输出 JSON：
{{"goal_met": true 或 false, "evidence": "支撑判断的关键事实（引用实际调用的工具或数据）",
 "gaps": "还缺什么、哪一步信息不足", "next_action": "下一步该做什么（一句话、可执行）"}}

任务目标：{task}
实际调用：{trace}
最终输出：{final}
"""


def _tool_lines(registry):
    lines = []
    for name, t in (registry or {}).items():
        confirm = "（执行类，需人确认）" if getattr(t, "human_confirm", False) else ""
        lines.append("- %s：%s%s" % (name, getattr(t, "description", ""), confirm))
    return "\n".join(lines)


def _parse_json(raw, kind="array"):
    pat = r"\[.*\]" if kind == "array" else r"\{.*\}"
    m = re.search(pat, raw or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def make_plan(task, registry, ask_model):
    """返回 {steps, valid_tools, unknown_tools, raw}；模型乱给工具名会被单独标出来。"""
    prompt = PLAN_PROMPT.format(tools=_tool_lines(registry), task=task)
    try:
        raw = ask_model(prompt) or ""
    except Exception as e:
        return {"steps": [], "valid_tools": [], "unknown_tools": [],
                "error": str(e)[:120], "raw": ""}
    rows = _parse_json(raw, "array") or []
    steps, valid, unknown = [], [], []
    known = set((registry or {}).keys())
    for i, r in enumerate(rows, start=1):
        if not isinstance(r, dict):
            continue
        tool = str(r.get("tool") or "").strip()
        steps.append({"step": r.get("step", i), "tool": tool,
                      "goal": str(r.get("goal") or "")[:120]})
        (valid if tool in known else unknown).append(tool)
    return {"steps": steps, "valid_tools": valid, "unknown_tools": unknown,
            "raw": raw[:800]}


def reflect(task, trace, final, ask_model):
    """返回 {goal_met, evidence, gaps, next_action}；解析失败给保守值，不假装成功。"""
    used = " → ".join(str(t.get("tool") or t.get("step")) for t in (trace or [])) or "（无）"
    prompt = REFLECT_PROMPT.format(task=task, trace=used, final=(final or "")[:600])
    try:
        raw = ask_model(prompt) or ""
    except Exception as e:
        return {"goal_met": None, "evidence": "", "gaps": str(e)[:120],
                "next_action": "重试一次"}
    d = _parse_json(raw, "object")
    if not isinstance(d, dict):
        return {"goal_met": None, "evidence": "",
                "gaps": "复核失败：模型输出不是 JSON", "next_action": "人工看 trace 判断"}
    return {
        "goal_met": bool(d.get("goal_met")),
        "evidence": str(d.get("evidence") or "")[:300],
        "gaps": str(d.get("gaps") or "")[:300],
        "next_action": str(d.get("next_action") or "")[:200],
    }
