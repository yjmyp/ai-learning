# -*- coding: utf-8 -*-
"""面试拷问 v2：四维打分解析 + 趋势统计（纯离线，不需要模型）。"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import interview_drill as idr  # noqa: E402

OK, BAD = 0, 0


def check(name, cond):
    global OK, BAD
    print(("✅ " if cond else "❌ ") + name)
    if cond:
        OK += 1
    else:
        BAD += 1


def main():
    # 1) 正常打分
    t, s = idr.parse_scores("✅ 好的：xxx\n[[SCORES]] 结构=7;深度=6;真实=9;表达=6")
    check("抠出四维分数", s == {"结构": 7, "深度": 6, "真实": 9, "表达": 6})
    check("正文里的打分行被删掉", "SCORES" not in t and "好的" in t)

    # 2) 中文分号 / 逗号 / 小数点
    t, s = idr.parse_scores("[[SCORES]] 结构=7.4，深度=6.5；真实=9,表达=5")
    check("小数点四舍五入", s.get("结构") == 7 and s.get("真实") == 9)
    check("中文分隔符也能切", len(s) == 4)

    # 3) 越界收口
    t, s = idr.parse_scores("[[SCORES]] 结构=15;深度=-3")
    check("超过 10 收口到 10", s.get("结构") == 10)
    check("负数收口到 0", s.get("深度") == 0)

    # 4) 模型没按格式输出 → 不要瞎猜分
    t, s = idr.parse_scores("这个回答还行，我给它 8 分吧。")
    check("没有打分标记就不给分", s == {})
    check("原文保留", "8 分" in t)

    # 5) 均分 / 场次均分
    items = [{"s": {"结构": 8, "深度": 6, "真实": 9, "表达": 7}},
             {"s": {"结构": 6, "深度": 6, "真实": 8, "表达": 5}}]
    avg = idr.dim_avg(items)
    check("四维均分=7", avg.get("结构") == 7)
    check("真实均分=8.5", avg.get("真实") == 8.5)
    check("整场均分能算出来", idr.session_avg(items) is not None)
    check("没打分的题不算进场次均分", idr.session_avg([{"s": {}}, {}]) is None)

    # 6) 历史读写 + 上限
    p = idr.HISTORY_PATH
    old = p.read_text(encoding="utf-8") if p.exists() else None
    try:
        p.unlink(missing_ok=True)
        idr.add_history({"job": "T", "avg": 6.5})
        idr.add_history({"job": "T", "avg": 7.5})
        rows = idr.load_history()
        check("历史能追加", len(rows) == 2 and rows[-1]["avg"] == 7.5)
        check("按岗位筛得出来", len([h for h in rows if h["job"] == "T"]) == 2)
    finally:
        if old is None:
            p.unlink(missing_ok=True)
        else:
            p.write_text(old, encoding="utf-8")

    # 7) v2.5 题库沉淀
    bp = idr.BANK_PATH
    old_bank = bp.read_text(encoding="utf-8") if bp.exists() else None
    try:
        bp.unlink(missing_ok=True)
        n1 = idr.save_questions(["你的 RAG 项目怎么实现的？",
                                 "为什么选 Chroma 而不是 FAISS？",
                                 "你最大的短板是什么？"], "T")
        check("新题全部入库", n1 == 3)
        n2 = idr.save_questions(["你的 RAG 项目怎么实现的？"], "T2")
        check("同题不重复入库", n2 == 0)
        rows = idr.load_bank()
        check("题库条数不变", len(rows) == 3)
        hit = [r for r in rows if "实现" in r["q"]][0]
        check("重复出现只累加次数", hit["used"] == 2)
        check("分类：技术原理",
              idr.classify("为什么选 Chroma 而不是 FAISS？") == "技术原理")
        check("分类：动机规划",
              idr.classify("你最大的短板是什么？") == "动机规划")
        st = idr.bank_stats()
        check("统计对得上", sum(st.values()) == 3)
    finally:
        if old_bank is None:
            bp.unlink(missing_ok=True)
        else:
            bp.write_text(old_bank, encoding="utf-8")

    # 8) 预置题库：幂等并入、不与已有记录重复、来源标签正确
    old_bank2 = bp.read_text(encoding="utf-8") if bp.exists() else None
    try:
        bp.unlink(missing_ok=True)
        seeds = idr.load_seed()
        check("预置题库文件存在且有题", len(seeds) >= 30)
        n1 = idr.ensure_seed()
        check("首次并入 = 预置题数", n1 == len(seeds))
        check("二次调用不重复并入", idr.ensure_seed() == 0)
        rows = idr.load_bank()
        check("题库条数 = 预置题数", len(rows) == len(seeds))
        check("预置题标「预置」", idr.row_tag(rows[0]) == "预置")
        check("练过的题标「用过 N 次」",
              idr.row_tag({"q": "x", "used": 3}) == "用过 3 次")
        # 预置题被再次生成时应只累加 used，不再新增
        idr.save_questions([seeds[0]["q"]], "某岗位")
        check("同题只累加不新增", len(idr.load_bank()) == len(seeds))
        check("累加后 used=1",
              idr.load_bank()[0].get("used", 0) == 1)
    finally:
        if old_bank2 is None:
            bp.unlink(missing_ok=True)
        else:
            bp.write_text(old_bank2, encoding="utf-8")

    # 9) 追问：模型输出多余引号/换行也能洗干净
    class _Fake:
        def __call__(self, prompt):
            return '  "\u4f60\u8bf4\u7684 20 QPS \u662f\u600e\u4e48\u6d4b\u51fa\u6765\u7684\uff1f"\n'
    q = idr.make_followup("x", "y", _Fake())
    check("追问去掉引号与换行", q.startswith("你说") and '"' not in q)

    # 10) STAR 结构诊断（本地规则，不能乱给分）
    good = "当时在 RAG 项目里，我负责检索模块，做了 BM25 和向量融合，召回率从 72% 提升到 95%。"
    g = idr.star_check(good)
    check("STAR 四块齐全", g["score"] == 4 and g["missing"] == [])
    check("STAR 识别到数字", g["has_number"] is True)

    no_r = "当时在项目里，我负责检索模块，做了 BM25 和向量融合，效果不错。"
    n = idr.star_check(no_r)
    check("没有量化结果 → R 判缺失", "R" in n["missing"])
    check("缺 R 时给出补数字的提示", "数字" in idr.star_hint(n))

    check("空答案 STAR=0", idr.star_check("")["score"] == 0)
    check("空答案提示不为空", bool(idr.star_hint(idr.star_check(""))))

    # 11) 复盘报告
    db = idr.debrief([
        {"q": "a", "a": good, "s": {"结构": 9, "深度": 8, "真实": 9, "表达": 7}},
        {"q": "b", "a": "我们做了个 RAG。", "s": {"结构": 4, "深度": 4, "真实": 5, "表达": 6}},
    ])
    check("复盘统计已答数", db["answered"] == 2 and db["total"] == 2)
    check("复盘找出最弱维度", db["weakest"] in idr.SCORE_DIMS)
    check("复盘给出可执行结论", len(db["fixes"]) >= 1)
    check("复盘 STAR 完整度在 0-1", 0.0 <= db["star_rate"] <= 1.0)
    check("空复盘不报错", idr.debrief([])["answered"] == 0)

    print(f"\n{OK} 通过 / {BAD} 失败")
    return 0 if BAD == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
