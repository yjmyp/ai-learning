# -*- coding: utf-8 -*-
"""自我蒸馏版本库测试：版本落盘、证据（原始回答）、对比、生成时自动存档。"""
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import distill


def main():
    tmp = Path(tempfile.mkdtemp(prefix="oa_ver_"))
    orig = distill.VERSIONS_DIR
    distill.VERSIONS_DIR = tmp / "versions"
    checks = []
    try:
        state = {"answers": {"q1": "做了 RAG", "q2": "", "q3": "有代码"},
                 "followups": {"q1": "740 块"}}
        out1 = {"profile.md": "画像 v1\n", "highlights.md": "亮点 v1\n"}
        v1 = distill.save_version(state, out1)
        checks.append(("落盘版本目录", (distill.VERSIONS_DIR / v1).is_dir()))
        m = distill.load_version(v1)["manifest"]
        checks.append(("记录已回答数量与键", m["answered"] == 2
                       and set(m["answer_keys"]) == {"q1", "q3"}))
        checks.append(("证据回答可回查",
                       distill.load_version(v1)["answers"]["answers"]["q1"] == "做了 RAG"))
        out2 = {"profile.md": "画像 v2\n", "highlights.md": "亮点 v1\n"}
        v2 = distill.save_version(state, out2)
        d = distill.diff_versions(v1, v2)
        checks.append(("版本对比能看出差异", "+画像 v2" in d and "-画像 v1" in d))
        checks.append(("列表新版本在前", [x["version"] for x in distill.list_versions()][0] == v2))

        def fake_ask(prompt):
            return ("=== profile.md ===\n自动存档画像\n"
                    "=== highlights.md ===\n自动存档亮点\n")

        before = len(distill.list_versions())
        distill.distill({"answers": state, "followups": {}}, fake_ask,
                        out_dir=tmp / "out")
        checks.append(("distill() 自动存档", len(distill.list_versions()) == before + 1))
    finally:
        distill.VERSIONS_DIR = orig
    for name, ok in checks:
        print(("✅ " if ok else "❌ ") + name)
    print("\n%d/%d 通过" % (sum(1 for _, ok in checks if ok), len(checks)))
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
