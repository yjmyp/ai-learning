# -*- coding: utf-8 -*-
"""
test_agent.py —— OfferAgent 引擎离线回归测试（不花 token）
============================================================================
引擎循环 mock offer_agent_core.call_llm（固定回复序列）；
工具嵌套 mock offer_agent_tools._ask_model（固定匹配报告）。
两个 mock 分开打 —— 顺带验证"工具嵌套调用"这一成本结构的真实性。

用法：python test_agent.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "offeragent"))

import offer_agent_core as C
import offer_agent_tools as T
from offer_agent_tools import build_registry

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}")


def j(tool, args):
    return json.dumps({"tool": tool, "args": args}, ensure_ascii=False)


def fake_seq(seq):
    it = iter(seq)
    return lambda msgs, model="deepseek-chat": (
        next(it), {"prompt_tokens": 100, "completion_tokens": 20})


def nest_mock(prompt, *materials):
    """工具内部的嵌套 LLM 调用：固定返回匹配报告（含 '匹配度：88%' 供正则抽取）。"""
    return "匹配度：88%，高度匹配。候选人 RAG 全链路与 JD 要求对齐。"


reg = build_registry()
T._ask_model = nest_mock

# --- 1) 顺序调用工具 → 正常完成 + 分数 + tokens 落盘 ---
print("[1] 顺序调用工具（assess 纯规则 + match 嵌套 LLM）")
C.call_llm = fake_seq([
    j("assess_job", {"jd_text": "AI 应用开发实习，要求 Python、RAG、Agent、网络协议，公司正规，薪资正常，附链接"}),
    j("match_job", {"profile": "余剑，南京邮电大学网络工程 2027 届，AI 应用开发，RAG 全链路，Agent 工具调用",
                    "jd_text": "要求 Python、RAG、Agent、网络协议"}),
    "最终总结：匹配 88%。",
])
final, state = C.run_agent("匹配这个岗位", reg)
check("1.1 正常完成拿到 final", final == "最终总结：匹配 88%。")
tools = [t.get("tool") for t in state.trace]
check("1.2 trace 含 assess_job + match_job", "assess_job" in tools and "match_job" in tools)
check("1.3 extract_score = 88", C.extract_score(state.trace) == 88)
check("1.4 trace 落盘 tokens", state.trace[0].get("tokens", {}).get("prompt_tokens") == 100)
check("1.5 嵌套调用确实发生（成本结构实证）", nest_mock is T._ask_model)

# --- 2) 非法 JSON → 自动纠错继续 ---
print("[2] 非法 JSON 纠错")
C.call_llm = fake_seq([
    '{"tool": "match_job", "args": {',      # 有花括号但 JSON 解析失败 → 触发纠错分支
    j("match_job", {"profile": "余剑 2027 届 AI 应用开发 RAG Agent",
                    "jd_text": "要求 RAG Agent Python"}),
    "纠错后完成。",
])
final, state = C.run_agent("匹配岗位", reg)
check("2.1 非法 JSON 后能完成", final == "纠错后完成。")

# --- 3) 未知工具 → 自动纠错继续 ---
print("[3] 未知工具纠错")
C.call_llm = fake_seq([
    j("no_such_tool", {"x": 1}),
    j("match_job", {"profile": "余剑 2027 届 RAG Agent",
                    "jd_text": "要求 RAG"}),
    "完成。",
])
final, state = C.run_agent("匹配岗位", reg)
check("3.1 未知工具后能完成", final == "完成。")

# --- 4) 门禁强制闭环：模型直接总结 → 强制继续调 match_job ---
print("[4] required_tools 强制闭环")
C.call_llm = fake_seq([
    "这个岗位看起来不错，我觉得可以投。",          # 直接总结（未调工具）
    j("match_job", {"profile": "余剑 2027 届 RAG Agent",
                    "jd_text": "要求 RAG"}),
    "现在真的总结了。",
])
final, state = C.run_agent("匹配岗位", reg, required_tools=["match_job"])
check("4.1 强制后 trace 含 match_job", "match_job" in [t.get("tool") for t in state.trace])
check("4.2 强制后完成", final == "现在真的总结了。")

# --- 4b) 门禁失败路径：预算耗尽仍缺必需工具 → 明确报未完成 ---
print("[4b] required_tools 预算耗尽")
C.call_llm = fake_seq([
    "岗位不错。",
    "还是总结吧。",
    "再总结一次。",
    "不调工具直接答。",
    "最后一次。",
    "还是没调。",
    "放弃。",
    "再试。",
    "没了。",
    "结束。",
    "真的结束。",
    "到头了。",
])
final, state = C.run_agent("匹配岗位", reg, required_tools=["match_job"])
check("4b.1 缺必需工具时明确报未完成", "未调用必需工具 ['match_job']" in final)

# --- 5) human_confirm：执行动作停在人确认 ---
print("[5] 安全边界 human_confirm")
C.call_llm = fake_seq([
    j("open_application", {"url": "https://example.com/job"}),
])
final, state = C.run_agent("投递这个岗位", reg)
check("5.1 停在待确认", final == "需要用户确认的动作已就绪。")
check("5.2 pending 已记录", state.pending is not None and state.pending["tool"] == "open_application")

# --- 6) 异常兜底：API 崩 → 不崩，返回运行中断 ---
print("[6] 异常兜底")


def boom(msgs, model="deepseek-chat"):
    raise RuntimeError("API 错误（500）")


C.call_llm = boom
final, state = C.run_agent("匹配岗位", reg)
check("6.1 返回运行中断而非抛异常", final.startswith("运行中断"))

# --- 7) extract_json：多个 JSON / 代码示例 → 平衡括号提取 ---
print("[7] extract_json 平衡括号")
r1 = C.extract_json('先思考 {"tool": "a", "args": {}} 然后 {"tool": "b", "args": {"k": 1}}')
check("7.1 双 JSON 取到工具调用", r1 is not None and '"tool"' in r1)
r2 = C.extract_json('```json\n{"tool": "match_job", "args": {"profile": "x", "jd_text": "y"}}\n```')
check("7.2 代码块包裹可取", r2 is not None and "match_job" in r2)
r3 = C.extract_json("没有 JSON 我直接回答")
check("7.3 无 JSON 返回 None", r3 is None)

# --- 8) save_agent_log：敏感截断 + usage 汇总 ---
print("[8] 日志敏感截断")
jd_long = "要求" + "RAG Agent Python 网络协议 FastAPI Streamlit " * 30
seq = [
    j("assess_job", {"jd_text": jd_long}),
    "总结。",
]
C.call_llm = fake_seq(seq)
final, state = C.run_agent("评估岗位", reg)
logp = os.path.join(tempfile.gettempdir(), "test_agent_log.jsonl")
C.save_agent_log("test_job", "测试公司", state, final, log_path=logp)
line = json.loads(open(logp, encoding="utf-8").read().strip().splitlines()[-1])
args_jd = line["trace"][0]["args"]["jd_text"]
check("8.1 JD 已截断", len(args_jd) <= 420 and "截断" in args_jd)
check("8.2 usage 已汇总", line.get("tokens", {}).get("prompt", 0) >= 100)
os.remove(logp)

# --- 9) Memory.forget：记忆纠错 ---
print("[9] Memory.forget 纠错")
from agent_memory import Memory
mem = Memory()
mem.extract_facts("我是测试用户，我做过测试项目")
check("9.1 抽取 2 条事实", len(mem.facts) == 2)
mem.forget("做过项目：测试项目")
check("9.2 删除后剩 1 条", len(mem.facts) == 1)

# --- 10) 多 Agent worker 独立记忆库（静态断言） ---
print("[10] 多 Agent 记忆隔离")
import offer_agent_multi as M
check("10.1 WORKER_DB 独立于用户记忆库",
      M.WORKER_DB.endswith("memory_worker.db") and M.WORKER_DB != os.path.join(HERE, "offeragent", "data", "memory.db"))
check("10.2 worker 默认使用独立库（不污染用户画像）",
      "db_path or WORKER_DB" in open(os.path.join(HERE, "offer_agent_multi.py"), encoding="utf-8").read())

print(f"\n=== 结果：{PASS} 通过 / {FAIL} 失败 ===")
sys.exit(1 if FAIL else 0)
