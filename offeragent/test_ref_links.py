# -*- coding: utf-8 -*-
"""检查要推荐的参考链接能不能打开。"""
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

LINKS = [
    ("shadcn 主题", "https://ui.shadcn.com/themes"),
    ("shadcn 后台示例", "https://ui.shadcn.com/examples/dashboard"),
    ("Tailwind 色板", "https://tailwindcss.com/docs/colors"),
    ("Radix 配色系统", "https://www.radix-ui.com/colors"),
    ("Linear", "https://linear.app/"),
    ("Tremor 仪表盘", "https://tremor.so/"),
    ("Streamlit 官方画廊", "https://streamlit.io/gallery"),
    ("streamlit-shadcn-ui demo", "https://streamlit-shadcn-ui.streamlit.app/"),
    ("Reactive Resume", "https://rxresu.me/"),
    ("OpenResume", "https://www.open-resume.com/"),
    ("Material 3 配色", "https://m3.material.io/styles/color/system/overview"),
    ("Coolors 配色器", "https://coolors.co/"),
]

if __name__ == "__main__":
    for name, url in LINKS:
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            print(f"{'OK ' if r.status_code == 200 else str(r.status_code):<4} {name:<26} {url}")
        except Exception as e:
            print(f"ERR  {name:<26} {url}  ({type(e).__name__})")
