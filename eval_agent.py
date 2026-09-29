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
