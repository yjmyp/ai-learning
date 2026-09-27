# -*- coding: utf-8 -*-
r"""
make_resume_pdf · 简历 HTML → PDF（支持多模板 + 自动嵌照片）
========================================================
用法：
    python offeragent\make_resume_pdf.py                      # 默认 classic 模板
    python offeragent\make_resume_pdf.py --template sidebar
    python offeragent\make_resume_pdf.py --template compact --out 简历\试试.pdf
    python offeragent\make_resume_pdf.py --template sidebar --no-default   # 只看，不换默认

说明：
  · 三种模板：classic（单栏）/ sidebar（左侧栏）/ compact（极简黑白）
  · 有 简历/照片.jpg（或 offeragent/assets/avatar.png）就自动嵌进照片位
  · 生成的同名 PDF 会同时写一份「默认版」到 简历/余剑-简历-AI应用开发实习-v3.pdf，
    名片页的下载按钮就是取这份；--no-default 可以跳过
"""
import argparse
import base64
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent
RESUME_DIR = REPO / "简历"
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import browser_fetch as bf          # noqa: E402
import resume_templates as rt       # noqa: E402

DEFAULT_OUT = RESUME_DIR / "余剑-简历-AI应用开发实习-v3.pdf"


def html_to_pdf(html: str, out: Path) -> int:
    """用无头 Edge 把 HTML 打成 A4 PDF，返回 KB 数。"""
    tmp = RESUME_DIR / "_render_tmp.html"
    tmp.write_text(html, encoding="utf-8")
    if not bf.launch(headless=True):
        raise SystemExit("❌ Edge 启动失败")
    ws = bf._new_tab(tmp.as_uri())
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    time.sleep(4)
    res = cdp.call("Page.printToPDF", {
        "printBackground": True,
        "paperWidth": 8.27, "paperHeight": 11.69,          # A4
        "marginTop": 0.35, "marginBottom": 0.35,
        "marginLeft": 0.30, "marginRight": 0.30,
        "preferCSSPageSize": False,
    }, timeout=60)
    cdp.close()
    tmp.unlink(missing_ok=True)
    data = base64.b64decode(res.get("data", ""))
    if not data:
        raise SystemExit("❌ 没拿到 PDF 数据")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return max(1, round(len(data) / 1024))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default="classic", choices=list(rt.TEMPLATES.keys()))
    ap.add_argument("--out", default="")
    ap.add_argument("--no-default", action="store_true",
                    help="只生成模板版，不覆盖名片页用的默认 PDF")
    args = ap.parse_args()

    photo = rt.find_photo()
    print("模板：", args.template, "|", rt.TEMPLATES[args.template])
    print("照片：", photo if photo else "未找到（PDF 右上角会没有照片）")

    html = rt.render_with_photo(args.template)
    out = Path(args.out) if args.out else RESUME_DIR / (
        "余剑-简历-AI应用开发实习-v3.pdf" if args.template == "classic"
        else f"余剑-简历-AI应用开发实习-v3-{args.template}.pdf")
    kb = html_to_pdf(html, out)
    print(f"✅ 已生成：{out}（{kb} KB）")

    try:
        from pypdf import PdfReader
        pages = len(PdfReader(str(out)).pages)
        print("页数：", pages, "（1 页最佳）")
    except Exception:
        pages = None

    if not args.no_default and out != DEFAULT_OUT:
        shutil.copyfile(out, DEFAULT_OUT)
        print(f"↪ 已同步为默认版：{DEFAULT_OUT.name}（名片页下载的就是这份）")


if __name__ == "__main__":
    main()
