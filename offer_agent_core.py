# -*- coding: utf-8 -*-
"""
offer_agent_core.py —— OfferAgent 真正的 Agent 引擎
=====================================================
为什么说原来的 OfferAgent"不算 Agent"：它是"规则函数 + LLM 单次调用 + 人点按钮"的应用，
模型没有"自主决定调什么工具、按顺序编排、根据中间结果继续"的闭环。

本引擎把市面最佳 Agent 框架的设计模式落进来：
  1. LangGraph           —— 状态对象 AgentState（消息/记忆/预算/trace），节点=工具调用，边=流转
  2. OpenAI Agents SDK  —— 工具注册表 ToolRegistry：统一 schema，模型从注册表发现工具
  3. Nvidia OpenShell   —— 安全边界：工具白名单 + human_confirm 分级（执行类动作停在人确认）

复用已验证模块：agent_tool_guard.safe_call（参数守卫）+ agent_memory.Memory（记忆）。
"""
import json
import os
import re
import time

import requests
from agent_tool_guard import safe_call
from agent_memory import Memory

try:
    from local_key import API_KEY
except ImportError:
    API_KEY = ""

API_URL = "https://api.deepseek.com/chat/completions"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 匹配分门禁：低于该分数 → 建议不投（机器给结论，人做决定）
GATE_SCORE = 60


def gate_verdict(score) -> str:
    """把匹配分转成投递建议。score=None → 待评估。"""
    if score is None:
        return "待评估（本轮无匹配分）"
    if score >= GATE_SCORE:
        return f"建议投（匹配分 {score}）"
    return f"不建议投（匹配分 {score} < {GATE_SCORE}）"


# ============================================================
# 1) 工具注册表（LangChain/OpenAI SDK 风格：统一 schema）
# ============================================================
class Tool:
    def __init__(self, name, description, params, func, human_confirm=False):
        self.name = name            # 工具名（模型用这个调用）
        self.description = description  # 给模型看的说明（决定它会不会选这个工具）
        self.params = params        # {"参数名": "类型说明", ...}
        self.func = func            # 实际执行函数
        self.human_confirm = human_confirm  # True = 执行类动作，必须停在用户确认

    def schema(self):
        return {"name": self.name, "description": self.description,
                "params": self.params, "human_confirm": self.human_confirm}


def make_registry(tools: list) -> dict:
    """把 Tool 列表变成 {name: tool} 注册表。"""
    return {t.name: t for t in tools}


def _schemas(registry: dict) -> dict:
    """把注册表转成 safe_call 需要的参数合同格式。"""
    out = {}
    for t in registry.values():
        out[t.name] = {"required": list(t.params), "types": {k: str for k in t.params}}
    return out


def _tools_map(registry: dict) -> dict:
    return {t.name: t.func for t in registry.values()}


# ============================================================
# 2) Agent 状态（LangGraph 的 State 概念）
# ============================================================
class AgentState:
    def __init__(self, memory=None, budget=12):
        self.memory = memory or Memory()   # 短期+长期记忆（复用 agent_memory）
        self.messages = []                 # 完整对话消息（含工具回填）
        self.trace = []                    # 每步工具调用记录（可观测/评估）
        self.budget = budget               # 最大循环轮数（防死循环）
        self.pending = None                # 待用户确认的执行动作 {tool, args}

    def dump_trace(self) -> str:
        """输出 trace（面试讲可观测性：每一步模型想了什么、调了什么、结果如何）。"""
        return json.dumps(self.trace, ensure_ascii=False, indent=2)


# ============================================================
# 3) LLM 调用 + JSON 提取
# ============================================================
def call_llm(messages, model="deepseek-chat"):
    """主循环的 LLM 调用。Key 优先级：环境变量 DEEPSEEK_API_KEY（Web 部署由 Secrets 注入）→ local_key.py。
    返回 (content, usage)：usage 是每轮的 token 计数，供成本可观测（trace 落盘）。"""
    key = os.environ.get("DEEPSEEK_API_KEY", "") or API_KEY
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    last_err = None
    for attempt in range(3):                       # 指数退避重试：429 / 5xx / 网络抖动
        try:
            r = requests.post(API_URL, headers=headers,
                              json={"model": model, "messages": messages}, timeout=120)
            if r.status_code == 429:
                ra = r.headers.get("Retry-After")
                time.sleep(min(float(ra) if ra else 2 ** attempt, 30))
                continue
            if r.status_code >= 500 or r.status_code in (408, 425):
                time.sleep(2 ** attempt)
                continue
            if r.status_code != 200:
                try:
                    err = r.json().get("error", {}).get("message", r.text[:200])
                except Exception:
                    err = r.text[:200]
                raise RuntimeError(f"API 错误（{r.status_code}）：{err}")
            data = r.json()
            return data["choices"][0]["message"]["content"], data.get("usage", {})
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException) as e:
            last_err = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"API 调用失败（重试 3 次后）：{last_err}")


def extract_json(reply):
    """从回复里提取 JSON 工具调用。
    优先按 "tool" 键做平衡括号提取（回复里出现多个 JSON / 代码示例时最稳）；
    兜底：第一个 { 到最后一个 }。"""
    i = reply.find('"tool"')
    if i != -1:
        start = reply.rfind("{", 0, i)
        if start != -1:
            depth = 0
            for j in range(start, len(reply)):
                c = reply[j]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        return reply[start:j + 1]
    start = reply.find("{")
    end = reply.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return reply[start:end + 1]


# ============================================================
# 4) Agent 循环（ReAct：推理 → 行动 → 观察 → 再推理）
# ============================================================
SYSTEM_TEMPLATE = """你是一个求职 Agent，运行在 OfferAgent 中。你有以下工具：
{tools}

工作方式：
- 把用户的请求拆成步骤，按需依次调用工具
- 需要工具时，只输出一行 JSON：{"tool": "工具名", "args": {"参数名": 值}}
- 标有【执行动作，需用户确认】的工具：你只管发起调用意图，执行前会停下来等用户确认
- 拿到工具结果后，判断是继续调下一个工具还是回答用户
- 所有步骤完成后，给用户一个清晰的中文汇总（做了什么、结论是什么、下一步建议）
{memory}
"""


def build_system(registry: dict, memory: Memory) -> str:
    lines = []
    for t in registry.values():
        confirm = "【执行动作，需用户确认】" if t.human_confirm else ""
        lines.append(f"- {t.name}({json.dumps(t.params, ensure_ascii=False)}): {t.description} {confirm}".rstrip())
    return (SYSTEM_TEMPLATE.replace("{tools}", "\n".join(lines))
                           .replace("{memory}", memory.to_context()))


def run_agent(task: str, registry: dict, state: AgentState = None,
              system_text: str = None, required_tools: list = None) -> tuple:
    """跑 Agent 任务。返回 (最终回复, state)。
    - 首次调用：初始化 system（默认 build_system；多 Agent 场景可传自定义 system_text）+ 用户任务
    - 已有 state.messages（如确认后续跑）：**追加**而非重建，保持上下文连续
    - state.pending 非空 = 有执行动作停在用户确认，处理完可继续。
    - required_tools：任务完成的硬前提（如必须调过 match_job 才给总结），未满足会强制模型继续。"""
    state = state or AgentState()
    state.memory.extract_facts(task)
    if not state.messages:
        sys_txt = system_text or build_system(registry, state.memory)
        state.messages = [
            {"role": "system", "content": sys_txt},
            {"role": "user", "content": task},
        ]
    else:
        state.messages.append({"role": "user", "content": task})
    schemas = _schemas(registry)
    tools_map = _tools_map(registry)
    required_tools = required_tools or []

    def _missing_required() -> list:
        used = {t.get("tool") for t in state.trace}
        return [r for r in required_tools if r not in used]

    try:                                # 外部依赖异常兜底：不崩，返回部分完成状态
        for step in range(state.budget):
            reply, usage = call_llm(state.messages)
            raw = extract_json(reply)
            if not raw and (reply.lstrip().startswith("{") or '"tool"' in reply[:30]):
                # 截断/非法的工具调用（有 { 或 tool 键但解析失败）→ 纠错，不能当最终回答
                state.messages.append({"role": "assistant", "content": reply})
                state.messages.append({"role": "user",
                                       "content": "你输出的 JSON 无法解析，请只输出一行合法 JSON：{\"tool\": \"工具名\", \"args\": {…}}"})
                continue
            if not raw:                 # 模型直接回答
                missing = _missing_required()
                if missing:             # ⑤ 门禁强制闭环：缺必需工具不给总结
                    state.messages.append({"role": "assistant", "content": reply})
                    state.messages.append({"role": "user",
                                           "content": f"任务要求必须调用工具 {missing}，但你直接总结了。请继续调用 {missing}，基于结果再给总结。"})
                    continue
                state.messages.append({"role": "assistant", "content": reply})
                state.memory.add_turn(task, reply)
                return reply, state

            try:
                action = json.loads(raw)
            except json.JSONDecodeError:    # ① 非法 JSON
                state.messages.append({"role": "assistant", "content": reply})
                state.messages.append({"role": "user", "content": "你输出的 JSON 无法解析，请只输出一行合法 JSON：{\"tool\": \"工具名\", \"args\": {…}}"})
                continue

            tool = registry.get(action.get("tool"))
            args = action.get("args")
            if tool is None:                # ② 未知工具
                state.messages.append({"role": "assistant", "content": reply})
                state.messages.append({"role": "user", "content": f"未知工具 {action.get('tool')}，可用工具：{list(registry)}"})
                continue

            if tool.human_confirm:          # ③ 执行类动作 → 停在人确认（安全边界）
                state.pending = {"tool": tool.name, "args": args}
                state.messages.append({"role": "assistant", "content": reply})
                state.messages.append({"role": "user",
                                       "content": f"⚠️ 已生成执行动作 {tool.name}({args})，等待用户确认。请先向用户说明这个动作，确认后再继续。"})
                state.memory.add_turn(task, f"[待确认动作] {tool.name} {args}")
                return "需要用户确认的动作已就绪。", state

            resp = safe_call(tools_map, schemas, tool.name, args)
            state.trace.append({"step": step, "tool": tool.name, "args": args,
                                "ok": resp["ok"],
                                "result": resp.get("result") or resp.get("error"),
                                "tokens": usage})   # ④ 成本可观测：每步 token 落盘
            if not resp["ok"]:              # 坏调用 → 结构化错误回填重试
                state.messages.append({"role": "assistant", "content": reply})
                state.messages.append({"role": "user", "content": f"工具调用失败：{resp['error']}，请修正后重试"})
                continue

            state.messages.append({"role": "assistant", "content": reply})
            state.messages.append({"role": "user",
                                   "content": f"工具 {tool.name} 返回：{json.dumps(resp['result'], ensure_ascii=False)[:600]}，请继续"})

        missing = _missing_required()
        if missing:
            state.memory.add_turn(task, "[达到预算上限且缺必需工具]")
            return f"任务未完成：达到最大循环次数，且未调用必需工具 {missing}。", state
        state.memory.add_turn(task, "[达到预算上限]")
        return "达到最大循环次数，任务未完成。", state
    except Exception as e:
        state.memory.add_turn(task, f"[运行中断] {type(e).__name__}")
        return f"运行中断：{type(e).__name__}: {e}（已完成 {len(state.trace)} 步）", state


def continue_after_confirm(registry: dict, state: AgentState) -> tuple:
    """用户确认执行动作后，真正执行并继续 Agent 循环。"""
    if not state.pending:
        return "没有待确认的动作。", state
    tool = registry.get(state.pending["tool"])
    args = state.pending["args"]
    resp = safe_call({t.name: t.func for t in registry.values()},
                     _schemas(registry), tool.name, args)
    state.trace.append({"step": "human_confirmed", "tool": tool.name, "args": args,
                        "ok": resp["ok"], "result": resp.get("result") or resp.get("error")})
    state.pending = None
    state.messages.append({"role": "user",
                           "content": f"用户已确认。工具 {tool.name} 执行结果：{json.dumps(resp['result'], ensure_ascii=False)[:600]}，请继续完成任务并给最终汇总"})
    return run_agent("请基于以上信息完成原任务，给最终中文汇总（含已执行动作的结果）。", registry, state)


def extract_score(trace: list) -> object:
    """从 trace 里抽匹配分（可空）。只认两种工具，避免误抓 assess_job 的岗位质量分：
    - match_job 工具 result 的 "score"（单 Agent）
    - dispatch 工具 result 的 "match_score"（多 Agent，子 Agent 回填）
    result 可能存为 dict 或 repr 字符串（"{'score': 78, ...}"），两种形态都兼容。
    """
    for t in trace:
        if t.get("tool") not in ("match_job", "dispatch"):
            continue
        r = t.get("result")
        if isinstance(r, dict):
            if t.get("tool") == "dispatch" and r.get("match_score") is not None:
                return r["match_score"]
            if r.get("score") is not None:
                return r["score"]
        if isinstance(r, str):
            try:
                import ast
                obj = ast.literal_eval(r)
                if isinstance(obj, dict):
                    if t.get("tool") == "dispatch" and obj.get("match_score") is not None:
                        return obj["match_score"]
                    if obj.get("score") is not None:
                        return obj["score"]
            except Exception:
                pass
            m = re.search(r"(?:match_)?score['\"]?\s*[:=]\s*(\d+)", r)
            if m:
                return int(m.group(1))
    return None


def save_agent_log(job_name: str, company: str, state: AgentState, final: str,
                   confirmed: bool = False, log_path: str = None) -> str:
    """把一次 Agent 运行（trace + 结果）追加成一行 JSONL —— 投递日志，可复盘可统计。

    默认路径：ai-learning/offeragent/data/agent_logs.jsonl（与投递记录同目录）。
    返回实际写入的路径。
    """
    if log_path is None:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "offeragent", "data", "agent_logs.jsonl")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    entry = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "job": job_name,
        "company": company,
        "match_score": extract_score(state.trace),
        "verdict": gate_verdict(extract_score(state.trace)),
        "steps": len(state.trace),
        "confirmed": confirmed,
        "final": final,
        "tokens": {"prompt": sum(t.get("tokens", {}).get("prompt_tokens", 0) or 0 for t in state.trace),
                   "completion": sum(t.get("tokens", {}).get("completion_tokens", 0) or 0 for t in state.trace)},
        "trace": _slim_trace(state.trace),
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return log_path


def _slim_trace(trace: list) -> list:
    """落盘前截断 trace 里的敏感大字段（JD / 画像 / 话术全文），防隐私泄露 + 控制体积。"""
    BIG = ("jd_text", "profile", "text", "talk")
    out = []
    for t in trace:
        args = t.get("args")
        if isinstance(args, dict):
            slim = dict(args)
            for k in BIG:
                if isinstance(slim.get(k), str) and len(slim[k]) > 400:
                    slim[k] = slim[k][:400] + f"...[截断，原长{len(slim[k])}]"
            out.append(dict(t, args=slim))
        else:
            out.append(t)
    return out
