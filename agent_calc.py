# agent_calc.py —— 会算数的 Agent（AI 提议 -> 程序执行 -> 结果回填）
import json
import requests
from agent_tool_guard import TOOL_SCHEMAS, safe_call

try:
    from local_key import API_KEY
except ImportError:
    API_KEY = ""

url = "https://api.deepseek.com/chat/completions"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


# ===== 第 1 块：工具（普通 Python 函数） =====
def add(a, b):
    return a + b


def multiply(a, b):
    return a * b

def subtract(a, b):
    return a - b

# 工具总表：名字 -> 函数（程序侧注册表）
TOOLS = {
    "add": add,
    "multiply": multiply,
    "subtract": subtract,
}


# ===== 第 2 块：系统提示词（AI 侧说明书） =====
SYSTEM = """你是一个会使用工具的计算助手。你有以下工具：
- add(a, b)：加法
- multiply(a, b)：乘法
- subtract(a, b)：减法

规则：如果需要计算，必须只输出一行 JSON：{"tool": "工具名", "args": {"参数名": 值}}
例如：{"tool": "add", "args": {"a": 1, "b": 2}}
如果不需要工具，直接正常回答。
"""


# ===== 第 3 块：循环（Agent 灵魂） =====
def call_llm(messages):
    data = {
        "model": "deepseek-chat",
        "messages": messages,
    }
    r = requests.post(url, headers=headers, json=data, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def extract_json(reply):
    """把回复里第一个 { 到最后一个 } 之间的内容取出来（支持嵌套括号）。"""
    start = reply.find("{")
    end = reply.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return reply[start:end + 1]


def run_agent(question):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    for _ in range(5):
        reply = call_llm(messages)
        print(f"[debug] 模型输出: {reply}")
        raw = extract_json(reply)
        if raw:
            try:
                call = json.loads(raw)
            except json.JSONDecodeError:
                messages.append({"role": "assistant", "content": reply})
                messages.append({"role": "user", "content": "你输出的 JSON 无法解析，请只输出一行合法 JSON：{\"tool\": \"工具名\", \"args\": {\"参数名\": 值}}"})
                continue
            resp = safe_call(TOOLS, TOOL_SCHEMAS, call.get("tool"), call.get("args"))
            if not resp["ok"]:
                messages.append({"role": "assistant", "content": reply})
                messages.append({"role": "user", "content": f"工具调用失败：{resp['error']}，请修正后重试。args 必须是带参数名的对象，例如 {{\"a\": 1, \"b\": 2}}"})
                continue
            result = resp["result"]
            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": f"工具返回结果：{result}，请根据结果回答用户"})
        else:
            return reply
    return "达到最大循环次数，任务未完成"


# ===== 第 4 块：触发 =====
if __name__ == "__main__":
   print(run_agent("345 减 67 等于多少？"))
