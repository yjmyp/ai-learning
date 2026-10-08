# -*- coding: utf-8 -*-
"""隐私工具验收：导出 zip / 清空数据 / 路径护栏（不许删到别处）。

跑法：python offeragent/test_privacy_tools.py
"""
import io
import os
import shutil
import sys
import tempfile
import zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import privacy_tools as pt  # noqa: E402


def main():
    tmp = tempfile.mkdtemp(prefix="oa_privacy_")
    checks = []
    try:
        # 造一份"假数据目录"
        os.makedirs(os.path.join(tmp, "jds"), exist_ok=True)
        with open(os.path.join(tmp, "profile.md"), "w", encoding="utf-8") as f:
            f.write("画像内容")
        with open(os.path.join(tmp, "jds", "a.json"), "w", encoding="utf-8") as f:
            f.write('{"job": 1}')
        s = pt.data_summary(tmp, allow_any=True)
        checks.append(("data_summary 能数出文件数与体积", s["files"] == 2 and s["bytes"] > 0))
        blob = pt.export_bytes(tmp, allow_any=True)
        names = zipfile.ZipFile(io.BytesIO(blob)).namelist()
        checks.append(("导出的 zip 含全部文件（%d 个）" % len(names), len(names) == 2))
        checks.append(("导出文件名带时间戳",
                       pt.export_filename().startswith("offeragent-data-")
                       and pt.export_filename().endswith(".zip")))
        # 路径护栏：普通路径（不含 offeragent/data 后缀）必须拒绝
        blocked = False
        try:
            pt.purge(tmp)                      # 没给 allow_any，应拒绝
        except ValueError:
            blocked = True
        checks.append(("路径护栏：拒绝清空非 data 目录", blocked))
        checks.append(("护栏拦住后文件还在（没被误删）",
                       os.path.exists(os.path.join(tmp, "profile.md"))))
        n_files, n_dirs = pt.purge(tmp, allow_any=True)
        left = os.listdir(tmp)
        checks.append(("清空后目录为空（删 %d 文件 / %d 目录）" % (n_files, n_dirs),
                       n_files == 2 and n_dirs == 1 and left == []))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ok = sum(1 for _, v in checks if v)
    for name, good in checks:
        print(("PASS " if good else "FAIL ") + name)
    print("\n%d/%d 通过" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
