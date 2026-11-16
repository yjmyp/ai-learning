# -*- coding: utf-8 -*-
"""自我蒸馏 v2 测试（离线，用临时目录，不碰真实 data/）。

覆盖：老 state 升级 / 自适应追问 / 每题最多追问一次 / 充分度口径 /
      追问内容会喂给生成。

跑法：python offeragent\test_distill_v2.py
"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import distill        # noqa: E402
import distill_chat   # noqa: E402

RESULTS = []


def check(name, ok, extra=""):
    RESULTS.append((name, bool(ok)))
    print(("  OK  " if ok else "  FAIL ") + name + (f"  {extra}" if extra else ""))


def fake_model(raw):
    return lambda prompt: raw


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="oa_distill_"))
    old_path = distill_chat.STATE_PATH
    distill_chat.STATE_PATH = tmp / "distill_chat.json"
    try:
        # ---- 1) 老 state 就地升级，答案不丢 ----
        old_state = {"history": [{"role": "assistant", "content": "hi"}],
                     "answers": {"q1": "做了个 RAG 项目", "q2": "740 块语料"},
                     "idx": 2}
        distill_chat.STATE_PATH.write_text(
            json.dumps(old_state, ensure_ascii=False), encoding="utf-8")
        st = distill_chat.load()
        check("老 state 升级：答案保留", st["answers"].get("q1") == "做了个 RAG 项目")
        check("老 state 升级：补齐 followups", st["followups"] == {})
        check("老 state 升级：补齐 pending", st["pending"] is None)
        check("老 state 升级：版本号 = 2", st.get("v") == 2)

        # ---- 2) assess 解析 ----
        good = ("<ACK>记下了，740 块这个数字有用</ACK>\n"
                "<ENOUGH>no</ENOUGH>\n"
                "<FOLLOWUP>这 740 块怎么切分的？</FOLLOWUP>")
        v = distill_chat.assess("问", "答", fake_model(good))
        check("assess 解析 ACK", v["ack"].startswith("记下了"))
        check("assess 解析 ENOUGH=no", v["enough"] is False)
        check("assess 解析 FOLLOWUP", "740" in v["followup"])

        okv = ("<ACK>好</ACK>\n<ENOUGH>yes</ENOUGH>\n<FOLLOWUP>多问一句</FOLLOWUP>")
        v2 = distill_chat.assess("问", "答", fake_model(okv))
        check("够了就丢掉追问", v2["enough"] is True and v2["followup"] == "")

        check("模型输出乱码时按『够』处理",
              distill_chat.assess("问", "答", fake_model("随便写点啥"))["enough"] is True)

        def boom(_p):
            raise RuntimeError("网络挂了")
        check("模型报错时按『够』处理",
              distill_chat.assess("问", "答", boom)["enough"] is True)

        # ---- 3) 自适应追问：内容太稀 -> 追问一层 ----
        distill_chat.reset()
        st = distill_chat.load()
        first_q = distill.ALL_QUESTIONS[0][1]
        st["history"] = [{"role": "assistant", "content": "第 1 题"}]
        distill_chat.reply_and_ask(st, "还行吧，做了个项目", fake_model(good))
        check("太空的回答会触发追问", st["pending"] == "q1", str(st["pending"]))
        check("追问时 idx 不前进", st["idx"] == 0, str(st["idx"]))
        check("追问出现在聊天里", "追问" in st["history"][-1]["content"])
        check("q1 被记为『已追问』", "q1" in st["asked_followup"])

        # ---- 4) 回答追问 -> 写进 followups 并进下一题 ----
        distill_chat.reply_and_ask(st, "按标题切，740 块里有 33 篇", fake_model(good))
        check("追问答案进 followups", st["followups"].get("q1") == ["按标题切，740 块里有 33 篇"])
        check("追问后 pending 清空", st["pending"] is None)
        check("追问后 idx 前进到 1", st["idx"] == 1, str(st["idx"]))
        check("追问后问到第 2 题", "第 2 题" in st["history"][-1]["content"])

        # ---- 5) 同一题不会被追问第二次 ----
        st["idx"] = 0
        st["pending"] = None
        distill_chat.reply_and_ask(st, "还是随便", fake_model(good))
        check("同一题只追问一次",
              st["pending"] is None and st["idx"] == 1 and
              st["asked_followup"].count("q1") == 1,
              "pending=" + str(st["pending"]) + " idx=" + str(st["idx"]))

        # ---- 6) 充分度口径 ----
        empty = distill_chat.coverage({"answers": {}, "followups": {}})
        check("全空 = 0 分", empty["score"] == 0, str(empty["score"]))
        check("全空时缺口 = 全部题目", len(empty["missing"]) == len(distill.ALL_QUESTIONS),
              str(len(empty["missing"])))

        full = {k: f"做了 X，覆盖 740 条数据，用了 python" for k, _ in distill.ALL_QUESTIONS}
        best = distill_chat.coverage({"answers": full, "followups": {}})
        check("全答且有细节 = 90 分", best["score"] == 90, str(best["score"]))
        withfu = distill_chat.coverage(
            {"answers": full, "followups": {"q1": ["a", "b", "c", "d"]}})
        check("追问补充最多加 10 分 -> 100", withfu["score"] == 100, str(withfu["score"]))

        n_half = len(distill.ALL_QUESTIONS) // 2
        half = {k: "嗯" for k, _ in distill.ALL_QUESTIONS[:n_half]}
        mid = distill_chat.coverage({"answers": half, "followups": {}})
        expect = int(round(60.0 * n_half / len(distill.ALL_QUESTIONS)))
        check(f"半答无细节 = {expect} 分", mid["score"] == expect, str(mid["score"]))

        # ---- 7) 追问内容确实喂给生成 ----
        mats = distill.build_materials(
            {"answers": {"q1": "做了个 RAG 项目"},
             "followups": {"q1": ["740 块，33 篇"]}})
        check("build_materials 带追问", "740 块，33 篇" in mats)
        check("build_materials 带原始答案", "做了个 RAG 项目" in mats)
    finally:
        distill_chat.STATE_PATH = old_path

    n_ok = sum(1 for _, ok in RESULTS if ok)
    print(f"\n== 汇总 == 通过 {n_ok}/{len(RESULTS)}")
    return 0 if n_ok == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
