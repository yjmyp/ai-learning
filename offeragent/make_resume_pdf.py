# -*- coding: utf-8 -*-
r"""
make_resume_pdf · 把简历 HTML 打成 PDF（带照片）
==============================================
为什么不用截图/手动打印：照片和排版要能一键重生成。

用法：
    python offeragent\make_resume_pdf.py                 # 默认用 v3 模板
    python offeragent\make_resume_pdf.py --html 简历\xx.html --out 简历\xx.pdf

照片：如果有 简历/照片.jpg（或 offeragent/assets/avatar.png），会自动嵌进右上角照片位；
      html 里预留的占位是 <div id="photo"></div>。
"""
import argparse
import base64
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import browser_fetch as bf  # noqa: E402

PHOTO_CANDIDATES = [
    REPO / "简历" / "照片.jpg",
    REPO / "简历" / "照片.png",
    REPO / "offeragent" / "assets" / "avatar.png",
    REPO / "offeragent" / "assets" / "avatar.jpg",
]


def find_photo():
    for p in PHOTO_CANDIDATES:
        if p.exists() and p.is_file():
            return p
    return None


def inject_photo(html: str, photo: Path | None) -> str:
    """把 <div id="photo"></div> 换成内嵌 base64 的图片（没有照片就留空）。"""
    if not photo:
        return html.replace('<div id="photo"></div>', "")
    mime = "image/png" if photo.suffix.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(photo.read_bytes()).decode()
    img = f'<img src="data:{mime};base64,{b64}" alt="照片">'
    return html.replace('<div id="photo"></div>', f'<div id="photo">{img}</div>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", default=str(REPO / "简历" / "余剑-简历-AI应用开发实习-v3.html"))
    ap.add_argument("--out", default=str(REPO / "简历" / "余剑-简历-AI应用开发实习-v3.pdf"))
    args = ap.parse_args()

    src = Path(args.html).resolve()
    out = Path(args.out).resolve()
    if not src.exists():
        raise SystemExit(f"❌ 找不到模板：{src}")

    photo = find_photo()
    print("照片：", photo if photo else "未找到（PDF 会没有照片位）")
    html = inject_photo(src.read_text(encoding="utf-8"), photo)
    tmp = src.with_name(src.stem + "__render.html")
    tmp.write_text(html, encoding="utf-8")

    if not bf.launch(headless=True):
        raise SystemExit("❌ Edge 启动失败")
    ws = bf._new_tab(tmp.as_uri())
    cdp = bf._CDP(ws)
    cdp.call("Page.enable")
    time.sleep(4)
    res = cdp.call("Page.printToPDF", {
        "printBackground": True,
        "paperWidth": 8.27, "paperHeight": 11.69,     # A4
        "marginTop": 0.35, "marginBottom": 0.35,
        "marginLeft": 0.30, "marginRight": 0.30,
        "preferCSSPageSize": False,
    }, timeout=60)
    cdp.close()
    tmp.unlink(missing_ok=True)

    data = base64.b64decode(res.get("data", ""))
    if not data:
        raise SystemExit("❌ 没拿到 PDF 数据")
    out.write_bytes(data)
    print(f"✅ 已生成：{out}（{len(data) / 1024:.0f} KB）")
    try:
        from pypdf import PdfReader
        print("页数：", len(PdfReader(str(out)).pages))
    except Exception:
        pass


if __name__ == "__main__":
    main()
