# debug_agent.py —— 临时调试：打印模型原始回复，定位端到端失败原因
import json
import sys
sys.path.insert(0, ".")
from agent_resume import call_llm, extract_json, safe_call, TOOLS, TOOL_SCHEMAS, SYSTEM, Memory

mem = Memory()
mem.extract_facts("我是余剑，2027届，我做过RAG知识库问答系统")
messages = [
    {"role": "system", "content": SYSTEM.replace("{memory}", mem.to_context())},
    {"role": "user", "content": "用 score_resume 评：独立实现端到端RAG，BM25+向量混合检索，top-3命中率83%，已上线"},
]
reply = call_llm(messages)
print("=== 模型原始回复 ===")
print(repr(reply))
print("=== 提取 raw ===")
raw = extract_json(reply)
print(repr(raw))
if raw:
    try:
        call = json.loads(raw)
        print("=== parsed ===", call)
        resp = safe_call(TOOLS, TOOL_SCHEMAS, call.get("tool"), call.get("args"))
        print("=== safe_call ===", resp)
    except Exception as e:
        print("=== JSONDecodeError ===", repr(e))
