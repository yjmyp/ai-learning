# -*- coding: utf-8 -*-
"""数字人核心测试（离线，用临时目录，不碰真实 data/）。

跑法：python offeragent\test_twin_core.py
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

import twin_core  # noqa: E402

RESULTS = []


def check(name, ok, extra=""):
    RESULTS.append((name, bool(ok)))
    print(("  OK  " if ok else "  FAIL ") + name + (f"  {extra}" if extra else ""))


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="oa_twin_"))
    chat = tmp / "twin_chat.json"
    try:
        # ---- 1) 空档案目录 ----
        check("空目录：persona 为空", twin_core.load_persona(tmp) == {})
        r0 = twin_core.readiness(tmp)
        check("空目录：就绪度 0/6", r0["score"] == 0 and r0["total"] == 6, str(r0["score"]))
        check("空目录：缺 6 份", len(r0["missing"]) == 6)

        # ---- 2) 写入部分档案 ----
        (tmp / "profile.md").write_text("# 余剑\n南邮大四，做过 RAG", encoding="utf-8")
        (tmp / "style_guide.md").write_text("## 说话风格\n短句，不用「赋能」", encoding="utf-8")
        (tmp / "clone_brief.md").write_text("## 一句话定位\nAI 应用开发", encoding="utf-8")
        (tmp / "gaps.md").write_text("（不在底座清单里）", encoding="utf-8")
        (tmp / "highlights.md").write_text("   \n\n ", encoding="utf-8")  # 空白文件应被忽略

        persona = twin_core.load_persona(tmp)
        check("只收底座清单里的档案", set(persona) == {"profile.md", "style_guide.md", "clone_brief.md"},
              str(sorted(persona)))
        check("空白档案被忽略", "highlights.md" not in persona)
        check("gaps.md 不进底座", "gaps.md" not in persona)

        r1 = twin_core.readiness(tmp)
        check("就绪度 = 3/6", r1["score"] == 3, str(r1["score"]))
        check("缺的写成中文标签", "亮点库" in r1["missing"])
        check("有的写成中文标签", "表达风格与边界手册" in r1["have_labels"])

        # ---- 3) build_system 真的把档案拼进去了 ----
        sysp = twin_core.build_system(persona, "余剑", ["以后别说「赋能」"])
        check("system 含画像事实", "南邮大四" in sysp)
        check("system 含风格手册", "不用「赋能」" in sysp)
        check("system 含纠正", "以后别说「赋能」" in sysp)
        check("缺的档案标出来", "（还没有这份档案）" in sysp)
        check("system 带硬规则", "禁止编造" in sysp)
        sysp2 = twin_core.build_system(persona)
        check("没纠正时显示暂无", "（暂无）" in sysp2)

        # ---- 4) 对话状态 ----
        check("坏文件 -> 空对话", twin_core.load_chat(tmp / "nope.json")["messages"] == [])
        chat.write_text("{ not json", encoding="utf-8")
        check("JSON 坏了也不崩", twin_core.load_chat(chat)["messages"] == [])

        st = twin_core.load_chat(chat)
        captured = {}

        def fake_ask(prompt):
            captured["p"] = prompt
            return "我用 python 做了 740 块的检索，命中率 95%"

        ans = twin_core.reply(st, "你的 RAG 命中率多少", fake_ask,
                              persona=persona, who="余剑", path=chat)
        check("reply 返回模型答案", ans.startswith("我用 python"))
        check("reply 落了 2 条消息", len(st["messages"]) == 2, str(len(st["messages"])))
        check("落库角色正确",
              [m["role"] for m in st["messages"]] == ["user", "assistant"])
        on_disk = json.loads(chat.read_text(encoding="utf-8"))
        check("真的写到磁盘", len(on_disk["messages"]) == 2)
        check("prompt 里带上了画像", "南邮大四" in captured["p"])
        check("prompt 里带上了本次问题", "命中率多少" in captured["p"])

        # 第二轮：历史要进 prompt
        twin_core.reply(st, "那召回率呢", fake_ask, persona=persona, path=chat)
        check("第二轮 prompt 带上历史", "命中率多少" in captured["p"])
        check("两轮共 4 条消息", len(st["messages"]) == 4, str(len(st["messages"])))

        # ---- 5) 边界情况 ----
        before = len(st["messages"])
        check("空问题不产生消息", twin_core.reply(st, "   ", fake_ask, path=chat) == ""
              and len(st["messages"]) == before)

        def boom(_p):
            raise RuntimeError("API 挂了")
        a2 = twin_core.reply(st, "再问一句", boom, path=chat)
        check("模型报错给兜底话术", "没答上来" in a2, a2[:20])
        check("报错也落库", len(st["messages"]) == before + 2)
        check("报错记进 last_error", "API 挂了" in str(st.get("last_error")))

        # ---- 6) 纠偏 ----
        check("空纠正不收", twin_core.add_correction(st, "   ", path=chat) is False)
        check("正常纠正收下", twin_core.add_correction(st, "别用「赋能」", path=chat) is True)
        check("重复纠正不叠加", twin_core.add_correction(st, "别用「赋能」", path=chat) is False)
        check("纠正 = 1 条", len(st["corrections"]) == 1)
        for i in range(twin_core.MAX_CORRECTIONS + 5):
            twin_core.add_correction(st, "纠正 %d" % i, path=chat)
        check("纠正有上限", len(st["corrections"]) == twin_core.MAX_CORRECTIONS,
              str(len(st["corrections"])))
        check("纠正落了磁盘",
              len(json.loads(chat.read_text(encoding="utf-8"))["corrections"])
              == twin_core.MAX_CORRECTIONS)

        # ---- 7) 历史截断 ----
        many = [{"role": "user", "content": "u%d" % i} for i in range(50)]
        many += [{"role": "assistant", "content": "a%d" % i} for i in range(50)]
        ht = twin_core._history_text(many, turns=3)
        check("历史只带最近 3 轮", ht.count("\n") == 5, str(ht.count("\n")))
        check("历史保留最新一条", "a49" in ht and "u0" not in ht)
    finally:
        pass

    n_ok = sum(1 for _, ok in RESULTS if ok)
    print(f"\n== 汇总 == 通过 {n_ok}/{len(RESULTS)}")
    return 0 if n_ok == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
