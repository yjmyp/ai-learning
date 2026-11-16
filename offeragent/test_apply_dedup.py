# -*- coding: utf-8 -*-
"""投递全局防重验收：同一岗位换来源/标题变体，也不能再投一次。

跑法：python offeragent\test_apply_dedup.py
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import apply_assist  # noqa: E402
import store          # noqa: E402

RESULTS = []


def check(name, ok, extra=""):
    RESULTS.append((name, bool(ok)))
    print(("  ✅ " if ok else "  ❌ ") + name + (f"  {extra}" if extra else ""))


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="oa_apply_dedup_"))
    old = (
        apply_assist.DATA_DIR, apply_assist.LOG_PATH,
        store.DATA_DIR, store.JDS_DIR, store.MATCH_DIR,
    )
    try:
        apply_assist.DATA_DIR = tmp
        apply_assist.LOG_PATH = tmp / "applications.jsonl"
        store.DATA_DIR = tmp
        store.JDS_DIR = tmp / "jds"
        store.MATCH_DIR = tmp / "match_results"
        store.ensure_dirs()

        old_meta = {
            "company": "某某科技有限公司",
            "title": "AI 应用开发（可转正）",
            "city": "南京",
            "source_url": "https://example.com/job/123?utm_source=boss",
        }
        new_meta = {
            "company": "某某科技",
            "title": "AI应用开发实习生",
            "city": "南京",
            "source_url": "https://example.com/job/123?from=liepin",
        }

        check("URL 追踪参数被归一",
              apply_assist.canonical_url(old_meta["source_url"]) ==
              "https://example.com/job/123")
        check("标题/公司变体命中同一岗位指纹",
              bool(apply_assist.identity_keys("boss_old", old_meta) &
                   apply_assist.identity_keys("liepin_new", new_meta)))

        apply_assist.log_application("boss_old", old_meta)
        rows = apply_assist.load_applications()
        check("历史记录写入 identity", bool(rows and rows[0].get("identity")))
        check("历史 JSONL 可读", json.loads(apply_assist.LOG_PATH.read_text(
            encoding="utf-8").splitlines()[0])["job"] == "boss_old")

        dup = apply_assist.find_duplicate_application("liepin_new", new_meta)
        check("跨来源识别到历史投递", dup is not None and dup.get("job") == "boss_old")

        gate = store.check_apply_allowed("liepin_new", new_meta)
        check("投递前全局拦截", gate["allowed"] is False, gate.get("reason", ""))

        store.save_new_job("liepin_new_file", "南京", "这是一段岗位 JD 文本", extra=new_meta)
        got = {n: m for n, m, _ in store.list_jobs()}
        check("新文件入库后自动标已投",
              got.get("liepin_new_file", {}).get("status") == "已投",
              str(got.get("liepin_new_file", {}).get("status")))
        check("重复岗位记录可追溯",
              got.get("liepin_new_file", {}).get("duplicate_of") == "boss_old")

        other = {
            "company": "另一家公司",
            "title": "后端开发",
            "city": "南京",
            "source_url": "https://example.com/job/999",
        }
        check("不同岗位不误杀", store.check_apply_allowed("other_job", other)["allowed"] is True)
    finally:
        (apply_assist.DATA_DIR, apply_assist.LOG_PATH,
         store.DATA_DIR, store.JDS_DIR, store.MATCH_DIR) = old
        shutil.rmtree(tmp, ignore_errors=True)

    bad = [name for name, ok in RESULTS if not ok]
    print()
    if bad:
        print(f"❌ {len(bad)}/{len(RESULTS)} 项未通过：{bad}")
        return 1
    print(f"✅ 投递防重 {len(RESULTS)}/{len(RESULTS)} 通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
