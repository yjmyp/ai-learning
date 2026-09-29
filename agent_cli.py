# -*- coding: utf-8 -*-
"""
agent_cli.py —— OfferAgent Agent 化演示（命令行）
====================================================
演示什么：一个真实任务，Agent **自主规划工具链**并依次执行——
  assess_job → split_jd → match_job → generate_talk → check_talk → (open_application 停在确认)

这验证了"OfferAgent 真的变成 Agent"：
  模型自己决定调哪些工具、按什么顺序、根据每个工具结果决定下一步，
  遇到执行类动作（打开投递链接）停在用户确认——安全边界。

用法：
  python agent_cli.py              # 单 Agent 完整分析链 + 停在投递确认
  python agent_cli.py --confirm    # 模拟用户确认后继续（真正打开浏览器）
  python agent_cli.py --job ant_agent   # 换一个岗位（默认 calix）
  python agent_cli.py --multi      # 多 Agent 协作模式（主管分派岗位分析师 + 话术专家）
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from offer_agent_tools import build_registry
from offer_agent_core import AgentState, run_agent, continue_after_confirm, save_agent_log
from offer_agent_multi import run_supervisor
from agent_memory import Memory

PROFILE_PATH = os.path.join(HERE, "offeragent", "data", "profile.md")
JDS_DIR = os.path.join(HERE, "offeragent", "data", "jds")
MEMORY_DB = os.path.join(HERE, "offeragent", "data", "memory.db")


def read_job(name: str) -> tuple:
    jd = open(os.path.join(JDS_DIR, name + ".txt"), encoding="utf-8").read()
    meta = json.load(open(os.path.join(JDS_DIR, name + ".meta.json"), encoding="utf-8"))
    return jd, meta


def main():
    job_name = sys.argv[sys.argv.index("--job") + 1] if "--job" in sys.argv else "calix"
    confirm = "--confirm" in sys.argv
    multi = "--multi" in sys.argv

    jd, meta = read_job(job_name)
    profile = open(PROFILE_PATH, encoding="utf-8").read()

    # 记忆种子：画像关键事实（长期记忆，SQLite 跨会话落盘）
    mem = Memory(db_path=MEMORY_DB)
    mem.extract_facts("我是余剑，南京邮电大学网络工程2027届，做过RAG知识库问答系统和Agent求职助手，想投AI应用开发实习岗")

    state = AgentState(memory=mem, budget=14)
    task = f"""帮我把这个岗位的完整求职处理流程跑一遍。

【岗位】{meta.get('company') or '未知公司'} · {meta.get('name')}（{meta.get('city') or '未知城市'}）
【JD】
{jd[:800]}

【我的画像】
{profile}

请依次执行：
1. assess_job —— 评估这个岗位的质量
2. split_jd —— 拆解 JD，看岗位到底要什么
3. match_job —— 对比我的画像和 JD，算匹配度
4. generate_talk —— 生成 BOSS/微信版投递话术
5. check_talk —— 校验话术有没有禁用词
6. open_application —— 打开投递链接（这个动作会等我确认）

全部完成后给我一个中文汇总：岗位质量结论、匹配度、最终话术、下一步建议。"""

    print("=" * 56)
    print(f"OfferAgent Agent 演示 · 岗位：{job_name}" + (" · 多 Agent 协作模式" if multi else " · 单 Agent 模式"))
    print("=" * 56)
    print("任务：", task[:80].replace("\n", " "), "...")
    print("-" * 56)

    if multi:
        final, state = run_supervisor(task, build_registry(), state, db_path=MEMORY_DB)
    else:
        final, state = run_agent(task, build_registry(), state)

    print("\n[Agent 执行轨迹 trace]")
    print(state.dump_trace())

    if state.pending:
        print("\n" + "=" * 56)
        print(f"🔒 执行动作停在确认：{state.pending['tool']}({state.pending['args']})")
        print("按 OfferAgent 原则：发送前那一眼和那一下，永远由人来做。")
        if confirm:
            print("\n[模拟用户确认 → 继续执行]")
            final, state = continue_after_confirm(build_registry(), state)
            confirmed = True
            print("\n[Agent 收尾回复]")
            print(final)
        else:
            confirmed = False
            print("加 --confirm 参数可模拟确认后继续（会真的打开浏览器）。")
    else:
        confirmed = False
        print("\n[Agent 最终回复]")
        print(final)

    # trace 落盘：投递日志（每行一条 Agent 运行）
    log_path = save_agent_log(job_name, meta.get("company", ""), state, final,
                              confirmed=confirmed)
    print(f"\n[投递日志已写入] {log_path}")

    print("\n[记忆状态] 记住的事实：")
    for f in state.memory.facts:
        print("  -", f)


if __name__ == "__main__":
    main()
