# -*- coding: utf-8 -*-
"""OfferAgent v3 四项验收（全部离线，不花 token）

覆盖：
  1. Plan 节点   —— 能出计划、能识别模型编造的非法工具名
  2. Reflect 节点 —— 能解析自评 JSON、解析失败有保守兜底
  3. memory_vec  —— 记忆写入 + 语义召回（bge/tfidf/词面三档都能跑）
  4. MCP server  —— 真起子进程，走 JSON-RPC：initialize -> tools/list -> tools/call

跑法：python offeragent/test_agent_v3.py
"""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import offer_agent_plan as plan
import memory_vec
from offer_agent_tools import build_registry


def fake_plan_llm(prompt):
    return json.dumps([
        {"step": 1, "tool": "assess_job", "goal": "先看岗位质量"},
        {"step": 2, "tool": "match_job", "goal": "算匹配度"},
        {"step": 3, "tool": "nonexistent_tool", "goal": "编一个不存在的工具"},
        {"step": 4, "tool": "generate_talk", "goal": "生成话术"},
    ], ensure_ascii=False)


def test_plan():
    reg = build_registry()
    out = plan.make_plan("帮我评估这个岗位并准备话术", reg, fake_plan_llm)
    return [("Plan 能出计划（%d 步）" % len(out["steps"]), len(out["steps"]) == 4),
            ("Plan 校验工具名（合法工具识别）",
             "assess_job" in out["valid_tools"] and "match_job" in out["valid_tools"]),
            ("Plan 标出模型编造的非法工具", out["unknown_tools"] == ["nonexistent_tool"])]


def test_reflect():
    def good(p):
        return json.dumps({"goal_met": True, "evidence": "调了 match_job 得到 82 分",
                           "gaps": "没跑链接核验", "next_action": "核验链接后投递"},
                          ensure_ascii=False)

    def bad(p):
        return "我觉得还行吧"          # 非 JSON -> 必须有兜底，不能假装成功

    a = plan.reflect("评估岗位", [{"tool": "match_job"}], "匹配 82 分", good)
    b = plan.reflect("评估岗位", [{"tool": "match_job"}], "匹配 82 分", bad)
    return [("Reflect 解析出 goal_met/evidence/next_action",
             a["goal_met"] is True and "82" in a["evidence"] and bool(a["next_action"])),
            ("Reflect 解析失败时保守兜底（goal_met=None）", b["goal_met"] is None)]


def test_memory():
    memory_vec.STORE = memory_vec.DATA_DIR / "_test_memory.jsonl"
    if memory_vec.STORE.exists():
        memory_vec.STORE.unlink()
    memory_vec.add_memory("用户主投 AI 应用开发实习，坐标南京，可远程。", kind="pref")
    memory_vec.add_memory("上次投的蔚蓝智能给了 86 分，岗位在南京江宁。", kind="job")
    memory_vec.add_memory("用户不喜欢写长篇自我介绍，话术要口语化。", kind="style")
    hit = memory_vec.search("南京那边那个分高的岗位是哪家？", k=1)
    back = hit[0]["backend"] if hit else "none"
    ok_hit = bool(hit) and "蔚蓝" in hit[0]["text"]
    blk = memory_vec.context_block("南京 高匹配 岗位", k=2, min_score=-1)
    memory_vec.STORE.unlink(missing_ok=True)
    return [("记忆写入 + 语义召回命中目标（backend=%s）" % back, ok_hit),
            ("context_block 生成可注入的记忆块", "长期记忆" in blk)]


def mcp_call(proc, req, timeout=20):
    proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.flush()
    t0 = time.time()
    while time.time() - t0 < timeout:
        line = proc.stdout.readline()
        if not line:
            return None
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("id") == req.get("id"):
            return d
    return None


def test_mcp():
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "offer_agent_mcp.py")],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                            bufsize=1)
    try:
        init = mcp_call(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        tools = mcp_call(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        called = mcp_call(proc, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                 "params": {"name": "split_jd",
                                            "arguments": {"jd_text":
                                                          "岗位职责：负责 RAG 应用开发。\n"
                                                          "任职要求：熟悉 Python。"}}})
        items = ((tools or {}).get("result", {}) or {}).get("tools", [])
        names = [t["name"] for t in items]
        human = [t["name"] for t in items
                 if (t.get("annotations") or {}).get("humanConfirm")]
        txt = (((called or {}).get("result") or {}).get("content") or [{}])[0].get("text", "")
        return [("MCP initialize 返回协议版本",
                 bool(((init or {}).get("result") or {}).get("protocolVersion"))),
                ("MCP tools/list 列出工具（%d 个）" % len(names), len(names) >= 8),
                ("MCP 执行类工具被标记需人确认", "open_application" in human),
                ("MCP tools/call 真跑通（split_jd 返回内容）",
                 ("duty" in txt) or ("职责" in txt))]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()


def main():
    checks = test_plan() + test_reflect() + test_memory() + test_mcp()
    ok = 0
    for name, good in checks:
        print(("OK  " if good else "FAIL ") + name)
        ok += 1 if good else 0
    print("\n%d/%d 通过" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
