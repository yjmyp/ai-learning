# agent_calc.py —— 会算数的 Agent（AI 提议 -> 程序执行 -> 结果回填）
import json
import re
import requests

API_KEY = "sk-75255e06772248569871fdb19977fab4"

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

规则：如果需要计算，必须只输出一行 JSON：{"tool": "工具名", "args": [参数列表]}
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


def run_agent(question):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    for _ in range(5):
        reply = call_llm(messages)
        m = re.search(r'\{[^}]*"tool"[^}]*\}', reply)
        if m:
            call = json.loads(m.group(0))
            tool_name = call["tool"]
            args = call["args"]
            result = TOOLS[tool_name](*args)
            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": f"工具返回结果：{result}，请根据结果回答用户"})
        else:
            return reply
    return "达到最大循环次数，任务未完成"


# ===== 第 4 块：触发 =====
if __name__ == "__main__":
   print(run_agent("345 减 67 等于多少？"))
