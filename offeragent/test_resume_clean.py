# -*- coding: utf-8 -*-
"""简历文本清洗 + 问答式生成（含照片题）的验收。

跑法：python offeragent\test_resume_clean.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from resume_clean import clean, has_junk          # noqa: E402
import resume_builder                              # noqa: E402

JUNK = (
    "# 余剑\n\n"
    "项目：file:///C:/Users/29947/Documents/Codex/ai-learning/%E7%AE%80%E5%8E%86/"
    "%E4%BD%99%E5%89%91-%E7%AE%80%E5%8E%86-AI%E5%B\n\n"
    "本机 C:\\Users\\29947\\Documents\\Codex\\ai-learning\\简历\\我的简历.md\n\n"
    "正常内容：top-5 命中率 92%，占比 30%\n"
)


def main():
    checks = []
    out, rep = clean(JUNK)
    checks.append(("识别出乱码", has_junk(JUNK)))
    checks.append(("清洗后无 file://", "file://" not in out))
    checks.append(("清洗后无百分号编码", "%E7%AE%80" not in out))
    checks.append(("清洗后无本机路径", "C:\\Users" not in out))
    checks.append(("正常百分比没被误删", "92%" in out and "30%" in out))
    checks.append(("清洗报告有条目", len(rep) >= 2))

    # 问答式生成：照片题必须在题目列表里，且位置合理
    keys = [k for k, _, _ in resume_builder.QUESTIONS]
    checks.append(("有照片这一题", "photo" in keys))
    checks.append(("照片题在联系方式之后", keys.index("photo") > keys.index("contact")))
    checks.append(("题目总数 ≥ 13", len(keys) >= 13))

    # 答案里粘贴路径会被自动清洗
    st = {"answers": {}, "idx": 0}
    resume_builder.answer(st, "file:///C:/x/%E7%AE%80%E5%8E%86/ abc")
    checks.append(("答案里的路径被清洗", "file://" not in st["answers"]["name"]))

    ok = 0
    for name, good in checks:
        print(("✅ " if good else "❌ ") + name)
        ok += 1 if good else 0
    print(f"\n{ok}/{len(checks)} 通过")

    # 恢复问答状态，别把测试答案留在正式文件里
    resume_builder.save({"answers": {}, "idx": 0})


if __name__ == "__main__":
    main()
