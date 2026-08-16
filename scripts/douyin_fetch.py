# -*- coding: utf-8 -*-
"""抖音分享链接抓取：Edge 无头 dump DOM -> 提取 <title> 与页面可见文本。

用法（单条）:
  python scripts/douyin_fetch.py --id v01 --url https://v.douyin.com/xxxx/ --out tmp/douyin
  （--label 可选，用于标注视频标题/作者）

说明:
  - 需要本机安装 Edge（脚本里写死了常见路径，可改 EDGE 常量）。
  - 输出：<out>/<id>.txt 为纯文本视图，<out>/<id>.html 为原始 DOM。
  - 数据通过 --virtual-time-budget 等 JS 跑完再 dump，规避抖音反爬。
"""
import argparse
import html as html_mod
import os
import re
import subprocess
import sys
import tempfile
import uuid

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(EDGE):
    EDGE = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"


def visible_text(html_text):
    text = re.sub(r"<script.*?</script>", " ", html_text, flags=re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "\n", text)
    lines = [html_mod.unescape(l.strip()) for l in text.splitlines() if l.strip()]
    return lines


def fetch(url, out_html):
    profile = os.path.join(tempfile.gettempdir(), "edge-headless-" + uuid.uuid4().hex)
    cmd = [
        EDGE,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--user-data-dir=" + profile,
        "--virtual-time-budget=18000",
        "--dump-dom",
        url,
    ]
    with open(out_html, "w", encoding="utf-8") as f:
        subprocess.run(cmd, stdout=f, stderr=subprocess.DEVNULL, timeout=150)
    s = open(out_html, encoding="utf-8", errors="ignore").read()
    m = re.search(r"<title>(.*?)</title>", s, re.S)
    title = html_mod.unescape(m.group(1).strip()) if m else ""
    return s, title


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    out_html = os.path.join(args.out, args.id + ".html")
    out_txt = os.path.join(args.out, args.id + ".txt")
    s, title = fetch(args.url, out_html)
    lines = visible_text(s)
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("LABEL: %s\n" % args.label)
        f.write("URL: %s\n" % args.url)
        f.write("TITLE: %s\n" % title)
        f.write("---- VISIBLE TEXT ----\n")
        f.write("\n".join(lines))
    print("OK %s | %s | %d lines" % (args.id, title[:60], len(lines)), flush=True)


if __name__ == "__main__":
    main()
