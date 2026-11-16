# -*- coding: utf-8 -*-
"""确定性多 Agent 流水线的离线测试：不调用模型，不花钱。"""
import unittest
from unittest.mock import patch

from agent_memory import Memory
import offer_agent_core as C
from offer_agent_core import AgentState
import offer_agent_multi as M


class MultiAgentPipelineTest(unittest.TestCase):
    def test_pipeline_order_contracts_and_artifacts(self):
        calls = []

        def fake_worker(role, task, base_registry, db_path=None, required_tools=None):
            calls.append((role, list(required_tools or [])))
            state = AgentState(memory=Memory(), budget=1)
            if role == "岗位分析师":
                state.trace = [
                    {"tool": "assess_job", "ok": True,
                     "result": {"score": 88, "verdict": "岗位质量良好", "flags": []}},
                    {"tool": "split_jd", "ok": True,
                     "result": {"职责": ["做 RAG 和 Agent"], "要求": ["Python"]}},
                    {"tool": "match_job", "ok": True,
                     "result": {"score": 82, "report": "画像匹配良好",
                                "verdict": "建议投（匹配分 82）"}},
                ]
                return "岗位分析完成", state
            if role == "话术专家":
                state.trace = [
                    {"tool": "generate_talk", "ok": True,
                     "result": {"talk": "你好，我想投这个岗位。", "banned_hits": []}},
                    {"tool": "check_talk", "ok": True, "result": {"ok": True, "hits": []}},
                ]
                return "话术生成完成", state
            if role == "评审员":
                state.trace = [
                    {"tool": "check_talk", "ok": True, "result": {"ok": True, "hits": []}},
                ]
                return "判定：通过；问题：无", state
            raise AssertionError(f"未知角色：{role}")

        state = AgentState(memory=Memory(), budget=3)
        with patch.object(M, "run_worker", side_effect=fake_worker):
            final, state = M.run_job_pipeline(
                profile="余剑，AI 应用开发", jd_text="要求 Python/RAG/Agent",
                base_registry={}, state=state, job_label="测试公司 · AI 实习",
                url="https://example.com/job")

        self.assertEqual([c[0] for c in calls], ["岗位分析师", "话术专家", "评审员"])
        self.assertEqual(calls[0][1], ["assess_job", "split_jd", "match_job"])
        self.assertEqual(calls[1][1], ["generate_talk", "check_talk"])
        self.assertEqual(calls[2][1], ["check_talk"])
        self.assertEqual(state.artifacts["score"], 82)
        self.assertTrue(state.artifacts["review"]["passed"])
        self.assertIn("建议投", final)
        self.assertIn("你好，我想投这个岗位。", final)
        self.assertTrue(all(t.get("tool") != "open_application" for t in state.trace))
        self.assertEqual([t["tool"] for t in state.trace], ["dispatch", "dispatch", "dispatch"])

    def test_review_gate_rejects_low_score_empty_talk_and_banned_words(self):
        review = M.review_job_package(55, "", ["最强"], "判定：不通过；问题：缺匹配分")
        self.assertFalse(review["passed"])
        self.assertGreaterEqual(len(review["issues"]), 3)
        self.assertIn("低于投递门禁", " ".join(review["issues"]))

    def test_unfinished_reviewer_cannot_pass(self):
        review = M.review_job_package(82, "你好，我想投这个岗位。", [],
                                      "达到最大循环次数，任务未完成。")
        self.assertFalse(review["passed"])
        self.assertIn("评审员没有完成验收", " ".join(review["issues"]))

    def test_optional_tool_parameters_are_not_required(self):
        from offer_agent_tools import build_registry
        reg = build_registry()
        self.assertEqual(reg["check_talk"].required_params, ["text"])
        self.assertEqual(reg["generate_talk"].required_params, ["profile", "jd_text"])

    def test_worker_tool_subset_is_enforced(self):
        registry = {
            "assess_job": object(), "match_job": object(), "generate_talk": object(),
            "check_talk": object(), "funnel": object(),
        }
        reviewer_reg = M.worker_registry("评审员", registry)
        self.assertEqual(set(reviewer_reg), {"check_talk"})
        self.assertNotIn("generate_talk", reviewer_reg)

    def test_json_quoted_in_prose_is_a_final_answer(self):
        reply = '判定：通过\n\n依据：check_talk 返回 {"ok": true, "hits": []}，未命中禁用词。'
        with patch.object(C, "call_llm", return_value=(reply, {"total_tokens": 1})):
            final, state = C.run_agent("验收话术", {}, AgentState(memory=Memory(), budget=3))
        self.assertEqual(final, reply)
        self.assertNotIn("未知工具", str(state.messages))


if __name__ == "__main__":
    unittest.main()
