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
    """对 30 类输入跑守卫：正常调用应通过，坏调用应被拦截。

    覆盖四类坏输出 × 三个工具 + 工具名变体：
      坏调用 = 未知工具 / 缺参 / 类型错 / args 非对象 / None / 大小写与空白变体；
      正常调用 = 各种合法文本形态（含规则会扣分的岗位，调用本身合法）。
    """
    cases = [
        # ---- 正常调用（应通过）----
        ("score_resume", {"text": "Python RAG 上线 top-3 83% 有链接"}, True),
        ("score_resume", {"text": "简历：独立实现端到端 RAG，BM25+向量混合检索，已上线 https://x.com"}, True),
        ("score_resume", {"text": "短" * 1600}, True),                    # 超长文本（>3000 字）
        ("score_resume", {"text": "无数字纯中文项目描述一句话"}, True),      # 无量化词也合法
        ("assess_job", {"text": "负责 AI 应用开发，要求熟悉 RAG"}, True),
        ("assess_job", {"text": "日结刷单高额返利无经验包过"}, True),       # 规则判嫌疑，但调用合法
        ("assess_job", {"text": "短 JD"}, True),                           # 规则扣分，调用合法
        ("extract_keywords", {"text": "负责 AI 应用开发实习，熟悉 RAG、Agent、Python"}, True),
        ("extract_keywords", {"text": "LLM Agent RAG Vector Search Rerank"}, True),
        ("extract_keywords", {"text": "中英混合\n\t带换行与制表符 2026 届"}, True),
        ("score_resume", {"text": "合法调用带额外字段", "extra": "x"}, False),  # 合同外字段 → 执行层拒绝
        ("extract_keywords", {"text": ""}, True),                          # 空串是合法 str，调用成功
        # ---- 坏调用（应拦截）----
        ("score_resume", {"text": 123}, False),                            # 参数类型错
        ("score_resume", {}, False),                                       # 缺参数
        ("score_resume", {"text": None}, False),                           # None 不是 str
        ("score_resume", None, False),                                     # args 非对象
        ("score_resume", "text=xx", False),                                # args 是字符串
        ("score_resume", ["text"], False),                                 # args 是列表
        ("assess_job", {"text": 123}, False),
        ("assess_job", {}, False),
        ("assess_job", {"text": None}, False),
        ("assess_job", 42, False),                                         # args 是数字
        ("extract_keywords", {"text": 123}, False),
        ("extract_keywords", {}, False),
        ("extract_keywords", {"text": None}, False),
        ("extract_keywords", ("text",), False),                            # args 是元组
        ("no_such_tool", {"text": "x"}, False),                            # 未知工具
        ("Score_resume", {"text": "x"}, False),                            # 大小写错 → 未知工具
        (" score_resume", {"text": "x"}, False),                           # 前导空格 → 未知工具
        ("score_resume ", {"text": "x"}, False),                           # 尾随空格 → 未知工具
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
    """对 15 种模型回复格式测 JSON 提取（含嵌套/多块/全角括号/跨行/前后缀）。"""
    cases = [
        ('{"tool": "x", "args": {}}', True),                                  # 纯 JSON
        ('先思考再输出 {"tool": "x", "args": {}} 结束', True),                # 夹在文字里
        ('{"tool": "x", "args": {"nested": {"a": 1}}}', True),                # 嵌套括号
        ('没有 JSON 我直接回答', False),                                      # 无 JSON
        ('{"tool": "x", "args": {', False),                                    # 不完整
        ('tool x args', False),                                                # 非对象
        ('｛"tool": "x"，"args": ｛｝｝', False),                              # 全角括号 → 提取不到
        ('只有开始括号 {', False),                                             # 有 { 无 }
        ('只有结束括号 }', False),                                             # 有 } 无 {
        ('{"tool": "x", "args": {"a": [1,2,{"b":3}]}}', True),                # 多层嵌套数组+对象
        ('{"tool": "x"}', True),                                               # 单层
        ('  {"tool": "x", "args": {}}  ', True),                               # 前后空白
        ('先输出文字\n{"tool": "x", "args": {}}\n再输出文字', True),           # 跨行
        ('{"tool": "x", "args": {}} 和后面的解释', True),                      # JSON 后有文字
        ('我直接回答，不用工具', False),                                       # 纯文本回答
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
