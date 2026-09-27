# -*- coding: utf-8 -*-
"""测 OCR：生成一张带中文的图片，再用 RapidOCR 识别回来。"""
import sys
from pathlib import Path

HERE = Path(__file__).parent


def make_image(path: Path) -> str:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (900, 260), "white")
    d = ImageDraw.Draw(img)
    font = None
    for cand in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
                 r"C:\Windows\Fonts\simsun.ttc"]:
        if Path(cand).exists():
            try:
                font = ImageFont.truetype(cand, 34)
                break
            except Exception:
                continue
    lines = ["余剑 南京邮电大学 网络工程 2027届",
             "项目：RAG 知识库问答系统（已上线）",
             "top-1/3/5 = 75% / 83% / 92%",
             "技能：Python Chroma FastAPI"]
    for i, t in enumerate(lines):
        d.text((30, 25 + i * 58), t, fill="black", font=font)
    img.save(path)
    return "\n".join(lines)


def main():
    tmp = HERE / "data" / "ocr_test.png"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    truth = make_image(tmp)
    print("原图文字：")
    print(truth)
    try:
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        result, _ = engine(str(tmp))
        text = "\n".join(x[1] for x in (result or []))
        print("\nOCR 识别结果：")
        print(text)
        hits = sum(1 for kw in ["南京邮电大学", "网络工程", "RAG", "Python", "83"]
                   if kw in text)
        print(f"\n关键信息命中 {hits}/5")
    except Exception as e:
        print("\nOCR 失败：", type(e).__name__, str(e)[:200])


if __name__ == "__main__":
    main()
