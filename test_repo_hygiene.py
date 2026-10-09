# -*- coding: utf-8 -*-
"""仓库卫生检查：防止密钥随代码进 GitHub 这类不可逆事故。

背景（真踩过）：早期 API key 硬编码进代码，随 push 泄露，只能作废重建。
把这个教训固化成门禁：仓库里出现疑似真 key、或隐私数据被纳入版本控制，直接失败。

检查项：
  1. 已跟踪文件里没有真实 key 形态
  2. 敏感文件没被 git 跟踪（secrets.toml / local_key.py / .env）
  3. 求职隐私数据 offeragent/data/ 未入库（占位符 .gitkeep 除外——用于保证 Docker
     volume 源目录在 CI checkout 后存在）
  4. .gitignore 覆盖上述敏感路径

跑法：python test_repo_hygiene.py
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

KEY_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"(?i)api[_-]?key\s*[=:]\s*[\"'][A-Za-z0-9_\-]{20,}[\"']"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{25,}"),
]
ALLOW_HINTS = ("xxx", "your", "test", "1234", "example", "placeholder",
               "your_key", "YOUR_KEY", "demo", "sample")
SKIP_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".bin",
            ".sqlite3", ".webp", ".ico", ".woff", ".woff2"}
MUST_IGNORE = [".streamlit/secrets.toml", "local_key.py", ".env", "offeragent/data/"]
MUST_NOT_TRACK = [".streamlit/secrets.toml", "local_key.py", ".env"]


def tracked_files():
    r = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return [f for f in (r.stdout or "").splitlines() if f.strip()]


def scan_keys(files):
    suspects = []
    for rel in files:
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path) or os.path.getsize(path) > 400000:
            continue
        if os.path.splitext(rel)[1].lower() in SKIP_EXT:
            continue
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            low = line.lower()
            for pat in KEY_PATTERNS:
                m = pat.search(line)
                if not m:
                    continue
                if any(h.lower() in low for h in ALLOW_HINTS):
                    continue
                suspects.append("%s:%d  %s..." % (rel, line_no, m.group(0)[:24]))
    return suspects


def main():
    checks = []
    files = tracked_files()
    checks.append(("git 仓库可读（能列出跟踪文件）", len(files) > 0))

    suspects = scan_keys(files)
    checks.append(("已跟踪文件里没有真实 API key（可疑 %d 处）" % len(suspects),
                   len(suspects) == 0))
    for s in suspects[:10]:
        print("   可疑：%s" % s)

    bad = [f for f in MUST_NOT_TRACK if any(t == f or t.endswith("/" + f) for t in files)]
    checks.append(("敏感文件未被跟踪（%s）" % (", ".join(bad) if bad else "无"),
                   len(bad) == 0))

    data_tracked = [t for t in files if t.startswith("offeragent/data/")
                    and t != "offeragent/data/.gitkeep"]
    checks.append(("求职隐私数据未入库（%d 个文件）" % len(data_tracked),
                   len(data_tracked) == 0))

    # 构建产物：java-api/target 里那个 jar 有 24MB，入库会把仓库撑大、且每次构建都产生 diff。
    # 这条是被真实事故加上的（一次 git add java-api 把 target 一起提交了）。
    junk = [t for t in files if "/target/" in t or "node_modules/" in t
            or "__pycache__/" in t or t.endswith(".class")]
    checks.append(("构建产物未入库（%d 个%s）"
                   % (len(junk), "：" + ", ".join(junk[:3]) if junk else ""),
                   len(junk) == 0))

    gi_path = os.path.join(ROOT, ".gitignore")
    gi = open(gi_path, encoding="utf-8", errors="ignore").read() if os.path.exists(gi_path) else ""
    missing = [p for p in MUST_IGNORE if p not in gi and p.rstrip("/") not in gi]
    checks.append((".gitignore 覆盖敏感路径（缺：%s）" % (", ".join(missing) if missing else "无"),
                   len(missing) == 0))

    ok = sum(1 for _, v in checks if v)
    for name, good in checks:
        print(("OK  " if good else "FAIL ") + name)
    print("\n%d/%d 通过" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
