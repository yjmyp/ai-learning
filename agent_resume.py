# agent_resume.py —— 求职助手 Agent（真实工具 + 记忆 + 多轮）
# 对应客观差距清单：
#   ① 工具从"数学玩具（add/multiply/subtract）"换成"求职场景真实工具"
#      简历评分 / 岗位质量评估 / JD 关键词抽取 —— 解决真实问题、可解释、纯规则实现
#   ② 加短期记忆（多轮）+ 长期记忆（事实表）→ 上下文管理
#   ③ 配套评估脚本 eval_agent.py → 有评估和优化过程
import json
import re
import requests
from agent_tool_guard import safe_call
from agent_memory import Memory

try:
    from local_key import API_KEY
except ImportError:
    API_KEY = ""

url = "https://api.deepseek.com/chat/completions"
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


# ===== 第 1 块：真实工具（求职场景，纯规则、可解释、不依赖 LLM） =====
def score_resume(text):
    """简历文本五维评分：量化 / 项目深度 / 技能明确 / 可验证 / 简洁度。返回结构化 JSON。"""
    dims = {
        "量化指标": len(re.findall(r"\d+(?:\.\d+)?\s*[%％]|top[-－]\d|\d+\s*(?:条|个|篇|家|天)", text)),
        "项目深度": len(re.findall(r"RAG|Agent|向量|检索|重排|记忆|多轮|混合|评估|部署|上线|混合检索", text)),
        "技能明确": len(re.findall(r"Python|FastAPI|Streamlit|Chroma|DeepSeek|Function Calling|Git|Docker|SQL", text)),
        "可验证性": len(re.findall(r"https?://|上线|开源|GitHub", text)),
    }
    concise = 10 if len(text) < 1200 else (6 if len(text) < 3000 else 0)
    total = min(100, sum(min(22, v * 6) for v in dims.values()) + concise)
    advice = []
    if dims["量化指标"] < 2:
        advice.append("缺量化数字：给每个项目补'多少条/多少家/命中率 X%'")
    if dims["可验证性"] == 0:
        advice.append("缺可验证链接：加 GitHub / 上线地址")
    if not advice:
        advice.append("结构 OK：检查每个项目是否按 STAR（场景-动作-结果）叙述")
    return {"total": total, "dimensions": dims, "advice": "；".join(advice)}


def assess_job(text):
    """岗位质量评估：规则扣分（与 OfferAgent job_quality 同思路）。"""
    score = 100
    flags = []
    if len(text) < 100:
        flags.append("JD 内容过少"); score -= 25
    if not re.search(r"职责|工作内容|要求|岗位职责|负责", text):
        flags.append("缺少职责/要求描述"); score -= 15
    if re.search(r"日结|刷单|无经验包过|高额返利", text):
        flags.append("疑似异常岗位"); score -= 40
    if re.search(r"实习|应届|202[5-9]届|远程|远程办公", text):
        flags.append("面向实习/应届/远程，可投")  # 不扣分，仅提示
    score = max(0, min(100, score))
    verdict = "正常" if score >= 80 else ("存疑" if score >= 60 else "疑似僵尸岗")
    return {"score": score, "verdict": verdict, "flags": flags}


def extract_keywords(text):
    """JD 关键词抽取：词频 Top 8（过滤停用词）。"""
    STOP = {"的", "了", "和", "是", "在", "有", "与", "及", "或", "等", "我们", "你",
            "负责", "要求", "岗位", "工作", "相关", "具备", "熟悉", "优先", "能够", "进行", "以及"}
    words = re.findall(r"[\u4e00-\u9fa5]{2,6}|[A-Za-z][A-Za-z0-9+/]{1,20}", text)
    freq = {}
    for w in words:
        if w in STOP:
            continue
        freq[w] = freq.get(w, 0) + 1
    return {"top_keywords": [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:8]]}


# 工具注册表 + 参数合同（复用 agent_tool_guard 的 safe_call）
TOOLS = {
    "score_resume": score_resume,
    "assess_job": assess_job,
    "extract_keywords": extract_keywords,
}
TOOL_SCHEMAS = {
    "score_resume": {"required": ["text"], "types": {"text": str}},
    "assess_job": {"required": ["text"], "types": {"text": str}},
    "extract_keywords": {"required": ["text"], "types": {"text": str}},
}

# 系统提示词：{memory} 运行时注入
SYSTEM = """你是一个求职助手 Agent，能调用真实工具帮用户求职。可用工具：
- score_resume(text)：给简历文本打分，返回 JSON（含总分布和修改建议）
- assess_job(text)：评估一个岗位的质量，返回 JSON（分数/结论/风险标记）
- extract_keywords(text)：抽取一段 JD 的关键词 Top8

规则：
- 需要工具时，只输出一行 JSON：{"tool": "工具名", "args": {"参数名": 值}}
- 拿到工具结果后，用自然语言向用户解释结果并给出建议
- 不需要工具时直接回答
{memory}
"""


# ===== 第 2 块：LLM 调用 + JSON 提取（沿用已验证的逻辑） =====
def call_llm(messages):
    data = {"model": "deepseek-chat", "messages": messages}
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


# ===== 第 3 块：Agent 循环（含记忆注入 + 多轮） =====
def run_agent(question, memory=None):
    """跑一轮 Agent 任务；结果写入记忆。memory 复用 = 多轮记忆。"""
    memory = memory or Memory()
    memory.extract_facts(question)  # 从新问题里抽长期事实
    messages = [
        {"role": "system", "content": SYSTEM.replace("{memory}", memory.to_context())},
        {"role": "user", "content": question},
    ]
    final = "达到最大循环次数，任务未完成"
    for _ in range(5):
        reply = call_llm(messages)
        raw = extract_json(reply)
        if not raw:                    # 模型选择直接回答 → 结束本轮
            final = reply
            break
        try:
            call = json.loads(raw)
        except json.JSONDecodeError:   # ① 非法 JSON → 反馈重试
            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": "你输出的 JSON 无法解析，请只输出一行合法 JSON：{\"tool\": \"工具名\", \"args\": {…}}"})
            continue
        resp = safe_call(TOOLS, TOOL_SCHEMAS, call.get("tool"), call.get("args"))
        if not resp["ok"]:             # ② 坏调用 → 结构化错误回填重试
            messages.append({"role": "assistant", "content": reply})
            messages.append({"role": "user", "content": f"工具调用失败：{resp['error']}，请修正后重试"})
            continue
        messages.append({"role": "assistant", "content": reply})
        messages.append({"role": "user", "content": f"工具返回结果：{resp['result']}，请根据结果回答用户"})
        # ③ 工具成功 → 让模型基于结果作答（下一轮循环会拿到结果）
    memory.add_turn(question, final)   # 写入短期记忆（多轮可用）
    return final


def chat(question, memory=None):
    """多轮对话入口：同一个 memory 传进来，Agent 记住前面的对话和事实。"""
    memory = memory or Memory()
    ans = run_agent(question, memory)
    print(f"助手：{ans}")
    return ans


# ===== 第 4 块：触发 =====
if __name__ == "__main__":
    mem = Memory()
    print("—— 第 1 轮：评分我的简历 ——")
    chat("我是余剑，2027届，我做过RAG知识库问答系统，请用score_resume帮我看看这段简历文本：独立实现端到端RAG链路，BM25+向量混合检索，top-3命中率83%，已上线可访问", mem)
    print("\n—— 第 2 轮：多轮追问（验证记忆）——")
    chat("我忘了刚才简历评分多少分，告诉我总分和还缺什么", mem)
    print("\n—— 第 3 轮：换个工具（岗位评估）——")
    chat("帮我用assess_job评估这个岗位：负责AI应用开发实习，要求熟悉RAG和Agent，面向2027届，可远程", mem)
    print("\n—— 第 4 轮：长期记忆验证 ——")
    chat("我叫什么？什么学校？我想做什么方向？", mem)
