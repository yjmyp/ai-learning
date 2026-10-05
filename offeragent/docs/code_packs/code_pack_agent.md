# 代码包：Agent 引擎核心（自研 ReAct 循环 + 工具守卫 + 并发打分）

> 内容包括：引擎（状态对象 + ReAct 循环 + 预算上限）、工具注册表（schema 合同 + 守卫拦截 + 错误回填）、批量打分（线程池并发）、评估脚本、提示词。目标是让 AI 带我从头手敲引擎循环和 _score_one。

## 怎么喂
把本文件全文复制给 DeepSeek，开头加一句：
> 「先读完全文代码，再按我的水平逐块讲解，一次一小步，先框架后填空，不直接给完整答案。」

## 包含的文件

| 文件 | 行数 | 说明 |
|---|---|---|
| `offer_agent_core.py` | 364 | 见下方代码 |
| `offer_agent_tools.py` | 208 | 见下方代码 |
| `batch_score.py` | 114 | 见下方代码 |
| `eval_agent.py` | 97 | 见下方代码 |
| `offeragent/prompts.py` | 233 | 见下方代码 |
| `offeragent/llm.py` | 193 | 见下方代码 |

**合计 1209 行**（约 4KB），在 DeepSeek 上下文内。

---

## ===== offer_agent_core.py（364 行）=====

```python
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
```

## ===== offer_agent_tools.py（208 行）=====

```python
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
try:
    from local_key import API_KEY
except ImportError:
    API_KEY = os.environ.get("DEEPSEEK_API_KEY", "") or ""
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
```

## ===== batch_score.py（114 行）=====

```python
# -*- coding: utf-8 -*-
"""
batch_score.py —— 岗位分析师批量打分排序（商业化：按匹配分排投递优先级）
============================================================================
对全部「待投且未匹配」岗位，分派「岗位分析师」子 Agent 逐个评估质量 + 算匹配度，
把 match_score 回填到 jds/*.meta.json，最后输出按匹配分从高到低的投递优先级表。

用法：
  python batch_score.py                 # 跑全部待投且未匹配的岗位
  python batch_score.py --limit 3       # 只跑前 3 个（省钱）
  python batch_score.py --force         # 重跑全部待投岗位（含已打分的，覆盖回填）
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "offeragent"))

from offer_agent_tools import build_registry
from offer_agent_multi import run_worker
from offer_agent_core import extract_score, gate_verdict

JDS_DIR = os.path.join(HERE, "offeragent", "data", "jds")
PROFILE_PATH = os.path.join(HERE, "offeragent", "data", "profile.md")
MEMORY_DB = os.path.join(HERE, "offeragent", "data", "memory.db")


def load_profile() -> str:
    try:
        return open(PROFILE_PATH, encoding="utf-8").read()
    except FileNotFoundError:
        return "余剑，南京邮电大学网络工程2027届，AI应用开发实习生（RAG/Agent）"


def pending_unmatched(force: bool = False) -> list:
    """[(name, company, jd)] 待投 且（未匹配 或 force 强制重跑）。"""
    out = []
    for p in sorted(os.listdir(JDS_DIR)):
        if not p.endswith(".txt"):
            continue
        name = p[: -len(".txt")]
        meta_path = os.path.join(JDS_DIR, name + ".meta.json")
        try:
            meta = json.load(open(meta_path, encoding="utf-8"))
        except Exception:
            meta = {}
        if meta.get("status") not in ("待投", None):
            continue
        if not force and meta.get("match_score") is not None:
            continue
        jd = open(os.path.join(JDS_DIR, p), encoding="utf-8").read()
        out.append((name, meta.get("company", ""), jd))
    return out


def _score_one(item: tuple, profile: str, reg: dict) -> dict:
    """单个岗位：拼任务 → 调模型 → 抠分数（只算不写文件，文件由主线程统一写，避免并发写冲突）。"""
    name, company, jd = item
    task = (f"请评估岗位质量并计算匹配度，只调用 assess_job 和 match_job 两个工具，"
            f"不要生成话术。\n【岗位】{company or ''} · {name}\n【JD】\n{jd[:800]}\n【画像】\n{profile[:600]}")
    final, state = run_worker("岗位分析师", task, reg)     # 独立记忆库，不污染用户画像
    score = extract_score(state.trace)
    return {"name": name, "company": company, "score": score}


def run_batch(limit: int | None = None, force: bool = False) -> list:
    """批量打分核心逻辑（CLI 与 Web 共用）。返回按匹配分降序的 results。
    并发版：每个岗位一次 LLM 调用，互相独立 → 线程池 3 个同时打，串行 13 岗 ≈ 并发后约 1/3 时间。"""
    items = pending_unmatched(force)[:limit] if limit else pending_unmatched(force)
    if not items:
        return []
    profile = load_profile()
    reg = build_registry()
    results = []
    with ThreadPoolExecutor(max_workers=3) as pool:   # 3 个工人同时跑，map 保持输入顺序
        for i, res in enumerate(pool.map(lambda it: _score_one(it, profile, reg), items), 1):
            print(f"[{i}/{len(items)}] {res['company'] or res['name']} …", flush=True)
            if res["score"] is None:
                print(f"    ⚠️ {res['name']} 未调 match_job（门禁未闭环），分数缺失，建议人工复核")
            meta_path = os.path.join(JDS_DIR, res["name"] + ".meta.json")
            try:
                meta = json.load(open(meta_path, encoding="utf-8"))
            except Exception:
                meta = {}
            meta["match_score"] = res["score"]
            meta["match_verdict"] = gate_verdict(res["score"])
            json.dump(meta, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            results.append({"岗位": res["name"], "公司": res["company"],
                            "匹配分": res["score"], "裁决": gate_verdict(res["score"])})
            print(f"    → {res['name']} 匹配分 {res['score']} {gate_verdict(res['score'])}")
    results.sort(key=lambda r: -(r["匹配分"] or 0))
    return results


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    force = "--force" in sys.argv
    results = run_batch(limit=limit, force=force)
    if not results:
        print("没有「待投」岗位可跑（全部已打分？加 --force 强制重跑）。")
        return
    print(f"\n=== 投递优先级（按匹配分从高到低）===")
    for r in results:
        print(f"  {r['匹配分'] or '—':>4}  {r['岗位']:<16} {r['公司']}  [{r['裁决']}]")


if __name__ == "__main__":
    main()
```

## ===== eval_agent.py（97 行）=====

```python
# eval_agent.py —— Agent 评估：坏输入拦截率 + JSON 提取成功率 + 端到端用例
# 对应差距清单③：Agent 必须有"评估和优化过程"，面试能说"成功率从 X% 到 Y%"
#
# 用法：
#   python eval_agent.py            # 离线评估（不调 LLM，秒出结果）
#   python eval_agent.py --live     # 追加 3 条真实端到端用例（需要本地 API key）
import json
import sys
from agent_tool_guard import safe_call
from agent_resume import TOOLS, TOOL_SCHEMAS, extract_json, run_agent, Memory


def eval_guard():
    """对 6 类输入跑守卫：正常调用应通过，坏调用应被拦截。"""
    cases = [
        # (工具名, args, 期望 ok)
        ("score_resume", {"text": "Python RAG 上线 top-3 83% 有链接"}, True),   # 正常
        ("assess_job", {"text": "负责 AI 应用开发，要求熟悉 RAG"}, True),        # 正常
        ("score_resume", {"text": 123}, False),    # 参数类型错 → 拦截
        ("score_resume", {}, False),               # 缺参数 → 拦截
        ("no_such_tool", {"text": "x"}, False),    # 未知工具 → 拦截
        ("extract_keywords", None, False),         # args 非对象 → 拦截
    ]
    n_pass = 0
    rows = []
    for name, args, expect_ok in cases:
        r = safe_call(TOOLS, TOOL_SCHEMAS, name, args)
        correct = (r["ok"] == expect_ok)
        n_pass += correct
        rows.append((name, args, "期望通过" if expect_ok else "期望拦截",
                     "通过" if r["ok"] else f"拦截:{r['error'][:30]}", "✓" if correct else "✗"))
    return n_pass, len(cases), rows


def eval_extract():
    """对 6 种模型回复格式测 JSON 提取。"""
    cases = [
        ('{"tool": "x", "args": {}}', True),                                  # 纯 JSON
        ('先思考再输出 {"tool": "x", "args": {}} 结束', True),                # 夹在文字里
        ('{"tool": "x", "args": {"nested": {"a": 1}}}', True),                # 嵌套括号
        ('没有 JSON 我直接回答', False),                                      # 无 JSON
        ('{"tool": "x", "args": {', False),                                    # 不完整
        ('tool x args', False),                                                # 非对象
    ]
    n_pass = 0
    rows = []
    for text, expect in cases:
        got = extract_json(text) is not None
        correct = (got == expect)
        n_pass += correct
        rows.append((text[:24], "应提取" if expect else "应无", "提取到" if got else "无", "✓" if correct else "✗"))
    return n_pass, len(cases), rows


def eval_live():
    """端到端 3 条真实用例（需要 API key）。"""
    results = []
    mem = Memory()
    q1 = "用 score_resume 评：独立实现端到端RAG，BM25+向量混合检索，top-3命中率83%，已上线"
    q2 = "刚才我项目里的混合检索是什么？你记得吗（验证记忆）"
    q3 = "用 extract_keywords 抽取这段话的关键词：负责AI应用开发实习，要求熟悉RAG、Agent、Python"
    for q in (q1, q2, q3):
        try:
            ans = run_agent(q, mem)
            results.append((q[:20], ans[:80], True))
        except Exception as e:
            results.append((q[:20], str(e)[:60], False))
    return results


def main():
    print("=" * 46)
    print("Agent 评估报告（agent_resume.py）")
    print("=" * 46)

    g_pass, g_total, g_rows = eval_guard()
    print(f"\n[1] 工具守卫（safe_call）：{g_pass}/{g_total} 判定正确")
    for name, args, exp, got, mark in g_rows:
        print(f"    {mark} {name}{args} → {got}")

    e_pass, e_total, e_rows = eval_extract()
    print(f"\n[2] JSON 提取（extract_json）：{e_pass}/{e_total} 判定正确")
    for text, exp, got, mark in e_rows:
        print(f"    {mark} {text!r} → {got}")

    print(f"\n[3] 汇总：守卫 {g_pass}/{g_total}，提取 {e_pass}/{e_total}，"
          f"综合正确率 {(g_pass + e_pass) / (g_total + e_total) * 100:.0f}%")

    if "--live" in sys.argv:
        print("\n[4] 端到端（真实 LLM，需 API key）：")
        for q, ans, ok in eval_live():
            print(f"    {'✓' if ok else '✗'} Q:{q}… → {ans}")


if __name__ == "__main__":
    main()
```

## ===== offeragent/prompts.py（233 行）=====

```python
# -*- coding: utf-8 -*-
"""
prompts · OfferAgent 全部提示词（集中管理，方便增删）
====================================================
命名约定：
  PROMPT_*  = 通用任务提示词
  TALK_*    = 投递话术（按场景分版本）
  BANNED_*  = 生成后校验用的禁用词表

改动话术时只动这个文件，App 里不再写提示词。
"""

# ============================================================
# 一、画像与匹配
# ============================================================

PROMPT_PROFILE = (
    "生成个人画像，包含：基本信息、技能、项目经历、求职目标、优势、不足"
)

PROMPT_MATCH = """你是资深 AI 招聘顾问。对比「求职者画像」与「岗位 JD」，输出结构化匹配报告。
必须严格按以下模板输出，第一行就是匹配度，维度评分用单独小节：

# 匹配度：XX%
## 匹配点
- （逐条，说明与 JD 的对齐之处）
## 差距
- （逐条）
## 短板与风险
- （逐条）
## 同类岗位对比建议
- （投递优先级 / 谈判要点）
## 维度评分
技术栈:xx 项目匹配:xx 背景:xx 地点:xx 时长:xx
## 结论
（一句话：是否建议投递 + 理由）
"""

PROMPT_ADVICE = """你是资深简历顾问。结合「匹配报告」与「简历全文」，输出 3 条简历修改建议。
每条包含：改哪里 / 怎么改 / 解决什么问题。用 Markdown 有序列表，简洁、可执行。"""

PROMPT_HIGHLIGHT = """从「画像」中提取 3~5 条最值得对 HR 讲的个人亮点。
每条一句话，含具体数字（如有），口语化、不夸张。直接输出编号列表，不要其他内容。"""


# ============================================================
# 二、投递话术（v5 · 像真人打字，不像求职信）
# ============================================================
#
# v2 的问题：三段式结构（开场+量化经历+意愿）逼模型写简历摘要 → 生硬
# v3 的问题：改得过分口语（"想问问""聊聊"）→ 不像正常求职沟通
# v4 的问题：三段式结构 + 禁用词表仍逼出"工整求职信"，像 AI 写的。
# v5 的标准：像真人在手机上第一次联系 HR 打的字——短、直接、有具体细节、收尾给自然的下一步。
# 参考来源：Liyaxuxu/icebreaker-hr（"只挑不编"原则 + 十余轮 JD 实测经验）

TALK_STYLE_RULES = """
【核心要求】这段话要像真人第一次在 BOSS 直聘 / 微信上联系 HR 时打出来的字，
不是一封工整的求职信。想象你自己在手机上打字：短、直接、不端着、不怕不工整。

【像人的四个特征】
1. 开头自然：你好/您好 + 我是谁（学校 + 专业完整）。
   不加"尊敬的""冒昧""您好！我是"（感叹号加在自我介绍上显得像模板）
2. 中间只说一件最相关的事：和这个岗位最相关的一条经历或能力，一两句带完。
   素材里有具体数字或项目名就自然带出来（"top5 命中 92%""上线过"）。
   相关性强就直说，相关性弱就从能力迁移角度说，别硬扯。
3. 结尾给一个轻松的下一步：请对方看简历/作品、或表示想进一步了解。
   用"方便的话可以看下我的简历吗""想了解一下"这类，不用"期待您的回复""不知是否方便"。
4. 一句话说完的事别拆两句。宁可信息少一点，也别堆成简历摘要。

【反面清单（这些词一说就露馅）】
- 书面八股：贵司、冒昧、诚挚、深感荣幸、万分感谢、期待您的回复、希望有机会、敬请
- 工整排比：不说"不仅…而且…""既…又…""相信…一定…"
- 万能热情：非常/十分/充满热情/兴趣浓厚/高度匹配
- 性格软素质：学习能力强、抗压、有责任心、性格开朗
- 自我贬低：经验不足、还有很多要学、多多指教
- 罗列技能：熟悉 A、掌握 B、了解 C

【事实边界】
- 不编造素材里没有的经历、数字、奖项
- 进行中的项目只能按素材写的状态说。素材写"进行中"，就不要说它"已实现 XX 能力"；
  宁可少说一句，也不要替它升级
- 不提年级（"大三""大四"）。用毕业时间或可实习时长传递阶段信息
"""

TALK_FEWSHOT = """
【同一个人的两版对比，学它的差别】

工整版（AI 味，别学）：
"您好，我是南京邮电大学网络工程专业学生，具备 RAG 全链路开发经验，
曾独立实现文档解析、向量检索、重排生成等环节，对贵司 AI 应用开发实习岗位高度匹配，
期待与您进一步沟通。"
→ 问题：像简历摘要的朗读版；"高度匹配""期待与您"是模板词，真人不会这么打字。

真人版（学这个）：
"你好，我是南邮网络工程的学生，自己做过一个 RAG 问答系统，上线了，
top5 命中率 92%。看到你们在招 AI 应用开发实习生，正好是我在做的方向，
方便的话可以看下我的简历吗？"
→ 好在：口语、只提一件最相关的事、带具体数字、收尾是自然的请求。

【关于项目】项目不是必须提的。如果这个岗位和你做过的项目相关性弱，
就不提项目，改用"你具备什么可迁移的能力 + 你为此做过什么"来表达。
硬塞一个不相关的项目，比不提更糟。
"""

TALK_BOSS = """你要写一条 BOSS 直聘 / 微信上发给 HR 的第一条消息。对方会据此决定要不要点开简历。
{style}
{fewshot}

【本场景最重要的一条：极简直接】
上面的通用规则里"中间带一条相关经历"对你**不适用**——这个场景不要任何项目细节、
技术名词、数字和客套话，一句话把事说清楚：
"你好，我是 XX 大学的 XX（专业）学生，2027 届，想投贵公司 XX 岗位，以下是我的简历。"

【示例对比】
❌ 绕弯（不要）：你好，我是南邮网络工程的学生，自己做过 RAG 问答系统，上线了，
   top5 命中率 92%，看到你们在招 AI 开发实习生，方便的话可以看下我的简历吗？
✅ 直接（要这样）：你好，我是南京邮电大学网络工程专业的学生，2027 届，
   想投贵公司 AI 开发实习生岗位，以下是我的简历。

【禁止】
- 不写项目经历、技术名词、数字（RAG、top5、评估集都不要出现）
- 不写"方便的话""不知是否""期待""贵司"——用"贵公司"
- 不编造素材里没有的内容；岗位名以素材/JD 里实际写的为准
- 不提"大三""大四"，但可以说"2027 届"（毕业时间）

【长度】40 到 60 字，不要分行。
只输出消息正文：不要标题、不要落款、不要 emoji。
"""

TALK_EMAIL = """你要写一段用于网申表单「自我评价 / 个人简介」栏的文字（也可能直接用作邮件正文）。
{style}
{fewshot}

【结构】3 到 4 段，段与段之间空一行：
1. 身份背景（学校、专业、方向），一到两句
2. 与这个岗位最相关的 1 到 2 段经历：做了什么 + 怎么做的 + 关注了什么。技术细节在这里展开
3. 次相关的支撑经历（其他项目或课程）简要带过。素材里没有的就不要硬凑
4. 一句话能力概括 + 求职意愿收尾

【长度】250 到 300 字
【禁止】性格与软素质描述、平铺全部履历、只堆名词、编造素材里没有的内容
只输出正文，不要标题、不要称呼、不要落款。
"""

TALK_REFERRAL = """你要写一条发给内推人（学长、朋友、同事）的微信消息。
{style}
{fewshot}

【这一版可以稍微随意，但仍然保持正常的成年人沟通语气】
【长度】40 到 70 字。说清两件事：你想要哪个岗位；需要对方帮什么忙。
只输出消息正文：不要称呼、不要落款、不要 emoji。
"""

# 三个场景的注册表（App 用这个渲染选项）
TALK_VARIANTS = {
    "boss": ("BOSS/微信 打招呼（60-90 字）", TALK_BOSS),
    "email": ("邮件正文（150-250 字）", TALK_EMAIL),
    "referral": ("内推消息（40-70 字）", TALK_REFERRAL),
}

# 拼装成最终提示词（把共用规则和示例填进去）
def build_talk_prompt(variant: str) -> str:
    tpl = TALK_VARIANTS.get(variant, TALK_VARIANTS["boss"])[1]
    base = tpl.format(style=TALK_STYLE_RULES, fewshot=TALK_FEWSHOT)
    return base + ("\n\n特异性要求：话术必须自然提及 JD 里 1-2 个与你真实相关的具体技术/职责关键词"
                   "（如 RAG、Agent、向量检索、网络协议、工具调用等），"
                   "禁止只做自我介绍——HR 每天看几十条，只有提到 JD 关键词的才会被记住。")


# ============================================================
# 三、生成后校验（命中即重写一次）
# ============================================================

BANNED_OPENERS = [
    # 注意：不要禁"您好，我是"——正常的求职打招呼语就该这么开头。
    # 真正该禁的是书面八股、报年级、罗列技能。
    "尊敬的领导", "尊敬的HR", "您好！我叫", "本人", "敬启者",
]

BANNED_PHRASES = [
    "期待您的回复", "期待您的答复", "期待与您",
    "期待", "高度匹配", "非常匹配", "与岗位要求高度", "共同成长", "诚挚",
    "祝好", "盼复", "冒昧", "深感荣幸", "万分感谢", "希望有机会",
    "不知是否方便", "进一步沟通", "深度交流", "多多指教", "敬请",
    "携手", "共进", "赋能", "助力", "共创",
    "想问问", "聊聊匹配", "看看是否合适", "大三", "大四",
    "性格开朗", "学习能力强", "抗压能力", "有责任心",
    "经验不足", "提升空间", "还有很多要学", "兴趣浓厚",
    "不仅", "而且", "相信您", "一定不会让您失望",
]

# 场景专属禁用词：
#   打招呼语要隐去年级/届别（信息留给对话），用毕业时间或可实习时长传递阶段信息
#   网申自我介绍里写"2027 届本科"是正常的，不拦
VARIANT_BANNED = {
    "boss": ["本科在读", "大三", "大四"],
    "referral": ["届", "本科在读"],
    "email": [],
}


def check_talk(talk: str, variant: str = "boss") -> list:
    """检查话术里有没有禁用词。返回命中的词列表（空列表 = 通过）。

    variant 决定是否检查场景专属词（例如打招呼语不提届别）。
    """
    hits = []
    words = BANNED_OPENERS + BANNED_PHRASES + VARIANT_BANNED.get(variant, [])
    for w in words:
        if w in talk:
            hits.append(w)
    return hits


def generate_talk(ask, variant: str, profile: str, jd: str, max_retry: int = 2):
    """生成话术，命中禁用词就带着具体反馈重写。

    ask 是一个函数：ask(提示词, *材料) -> 模型输出文本
    返回 (最终文本, 仍命中的禁用词列表)
    """
    prompt = build_talk_prompt(variant)
    talk = ask(prompt, profile, jd)
    hits = check_talk(talk, variant)
    for _ in range(max_retry):
        if not hits:
            break
        fix = (prompt
               + f"\n\n你上一版里有这些词或说法：{hits}。"
                 "重写一遍，去掉它们，其余保持。只输出正文。")
        talk = ask(fix, profile, jd)
        hits = check_talk(talk, variant)
    return talk, hits
```

## ===== offeragent/llm.py（193 行）=====

```python
# -*- coding: utf-8 -*-
"""
llm.py —— OfferAgent AI 调用层（2026-09-29 从 offer_agent_app.py 抽出）
============================================================================
API Key 解析、每日额度保护、模型调用、匹配报告解析。不依赖页面。
"""
import json
import os
import re
import time

import requests
import streamlit as st

from store import CONFIG_PATH, USAGE_PATH, read_text, write_text

API_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-chat"
MODEL_OPTIONS = ["deepseek-chat", "deepseek-v4-flash"]


def get_api_key() -> str:
    try:
        k = st.secrets.get("DEEPSEEK_API_KEY", "")
        if k:
            return k
    except Exception:
        pass
    k = os.environ.get("DEEPSEEK_API_KEY", "")
    if k:
        return k
    cfg = read_text(CONFIG_PATH, "{}")
    try:
        k = json.loads(cfg).get("api_key", "")
        if k:
            return k
    except Exception:
        pass
    # 本地 CLI 回退：local_key.py（与 offer_agent_core / batch_score 同一来源）
    try:
        from local_key import API_KEY
        if API_KEY:
            return API_KEY
    except Exception:
        pass
    return ""


def get_model() -> str:
    cfg = read_text(CONFIG_PATH, "{}")
    try:
        return json.loads(cfg).get("model", DEFAULT_MODEL)
    except Exception:
        return DEFAULT_MODEL


def daily_limit() -> int:
    """每天允许的模型调用次数上限（防公开链接被人刷费用）。
    优先级：Secrets 的 DAILY_CALL_LIMIT > 环境变量 > 本地 config.json > 默认 200。"""
    raw = ""
    try:
        raw = st.secrets.get("DAILY_CALL_LIMIT", "")
    except Exception:
        raw = ""
    if not raw:
        raw = os.environ.get("DAILY_CALL_LIMIT", "")
    if not raw:
        try:
            raw = json.loads(read_text(CONFIG_PATH, "{}")).get("daily_call_limit", "")
        except Exception:
            raw = ""
    try:
        n = int(raw)
        return n if n > 0 else 0        # 0 = 不限（明确设 0 才关闭保护）
    except Exception:
        return 200


def _usage_today() -> dict:
    """今天的调用计数，按日期自动归零。"""
    today = time.strftime("%Y-%m-%d")
    try:
        u = json.loads(read_text(USAGE_PATH, "{}"))
    except Exception:
        u = {}
    if not isinstance(u, dict) or u.get("date") != today:
        u = {"date": today, "calls": 0}
    return u


def _bump_usage() -> int:
    u = _usage_today()
    u["calls"] = int(u.get("calls", 0)) + 1
    try:
        USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        write_text(USAGE_PATH, json.dumps(u, ensure_ascii=False))
    except Exception:
        pass
    return u["calls"]


def usage_left() -> tuple:
    """返回 (今天剩余次数, 上限)。上限为 0 表示不限。"""
    lim = daily_limit()
    used = int(_usage_today().get("calls", 0))
    if lim <= 0:
        return (-1, 0)
    return (max(lim - used, 0), lim)


def ask_model(messages: list, model: str = None) -> str:
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("未配置 API Key：请到「设置」页填入 DeepSeek API Key")
    lim = daily_limit()
    used = int(_usage_today().get("calls", 0))
    if used >= lim:
        raise RuntimeError(
            f"今天的模型调用额度已用完（上限 {lim} 次）。这是防止公开链接被人刷费用的保护。"
            f"要放宽就把 Secrets / 设置里的 DAILY_CALL_LIMIT 调大，或者明天再用。")
    _bump_usage()
    model = model or get_model()
    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages},
        timeout=120,
    )
    if resp.status_code != 200:
        try:
            err = resp.json().get("error", {}).get("message", resp.text[:200])
        except Exception:
            err = resp.text[:200]
        raise RuntimeError(f"API 错误（{resp.status_code}）：{err}")
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise RuntimeError(f"响应解析失败：{str(data)[:200]}")


def ask_chat(prompt: str, *materials: str, model: str = None) -> str:
    messages = [{"role": "user", "content": prompt}]
    for m in materials:
        if m and m.strip():
            messages.append({"role": "user", "content": m})
    return ask_model(messages, model)


def extract_score(report: str) -> int:
    m = re.search(r"匹配度[:：]?\s*(\d{1,3})\s*%", report)
    if m:
        return min(100, max(0, int(m.group(1))))
    return None


def parse_report(report: str) -> dict:
    """把匹配报告解析成结构化小节：{'匹配点': [...], '差距': [...], ...}"""
    sections = {}
    current = None
    for line in report.splitlines():
        m = re.match(r"^#+\s*(匹配点|差距|短板与风险|短板|结论|同类岗位对比建议|维度评分)",
                     line.strip())
        if m:
            current = m.group(1)
            sections[current] = []
            continue
        if current and line.strip():
            items = sections[current]
            if line.strip().startswith(("-", "•", "*")):
                items.append(line.strip().lstrip("-•* ").strip())
            else:
                if items:
                    items[-1] = items[-1] + " " + line.strip()
                else:
                    items.append(line.strip())
    return sections


def extract_dim_scores(report: str) -> dict:
    """从「维度评分」小节提取五维分数 {维度: 分数}"""
    m = re.search(r"##\s*维度评分\s*\n(.*)", report)
    if not m:
        return {}
    line = m.group(1).strip().splitlines()[0] if m.group(1).strip() else ""
    dims = {}
    for part in line.replace("，", " ").replace(",", " ").split():
        part = part.strip()
        mm = re.match(r"([\u4e00-\u9fa5A-Za-z]+)\s*[:：]\s*(\d{1,3})", part)
        if mm:
            dims[mm.group(1)] = min(100, max(0, int(mm.group(2))))
    return dims
```
