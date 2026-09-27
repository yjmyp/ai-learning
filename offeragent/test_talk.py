# -*- coding: utf-8 -*-
"""
话术对比测试：同一个岗位，用旧提示词 vs 新提示词各生成一条，直接看差别。

跑法：python offeragent\test_talk.py [岗位名]
默认岗位：weilan_ai
"""
import re
import sys
from pathlib import Path

import requests

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
JDS_DIR = DATA_DIR / "jds"
SECRETS = HERE / ".streamlit" / "secrets.toml"

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

sys.path.insert(0, str(HERE))
from prompts import build_talk_prompt, check_talk, generate_talk  # noqa: E402


def load_api_key() -> str:
    text = SECRETS.read_text(encoding="utf-8")
    m = re.search(r'DEEPSEEK_API_KEY\s*=\s*"([^"]+)"', text)
    if not m:
        raise SystemExit("没在 .streamlit/secrets.toml 里找到 DEEPSEEK_API_KEY")
    return m.group(1)


def ask(prompt: str, *materials: str, key: str, temperature: float = 0.8) -> str:
    content = prompt + "\n\n" + "\n\n".join(
        f"【材料 {i + 1}】\n{m}" for i, m in enumerate(materials)
    )
    r = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": [{"role": "user", "content": content}],
              "temperature": temperature},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


# v2 的旧提示词（原样搬过来，用于对比）
OLD_PROMPT_TALK = """你是资深求职顾问兼文案。根据「画像」与「岗位 JD」，写一条发给 HR 的中文打招呼语。
铁律：
1. 像真人微信聊天，自然口语、有温度，绝不像简历复读机、绝不堆列表
2. 不写"您好！我是XX大学XX专业XX届学生"这种模板开头；改为自然切入（如"看到贵司在招XX方向的实习…"）
3. 结构：一句自然开场 → 一句最有说服力的相关经历（带 1 个量化数字，自然融入）→ 一句表达兴趣/意愿
4. 长度 60~100 字
5. 直接输出正文，不要标题、称呼、落款、emoji"""


def main():
    job = sys.argv[1] if len(sys.argv) > 1 else "weilan_ai"
    jd_path = JDS_DIR / f"{job}.txt"
    if not jd_path.exists():
        raise SystemExit(f"找不到 JD：{jd_path}")

    key = load_api_key()
    profile = (DATA_DIR / "profile.md").read_text(encoding="utf-8")
    jd = jd_path.read_text(encoding="utf-8")

    print(f"岗位：{job}")
    print("=" * 70)

    print("\n【旧版提示词生成】\n")
    old = ask(OLD_PROMPT_TALK, profile, jd, key=key)
    print(old)
    old_hits = check_talk(old)
    print(f"\n禁用词命中：{old_hits if old_hits else '无'}")

    print("\n" + "=" * 70)
    print("\n【新版 · BOSS 打招呼（含自动校验重写）】\n")
    new, new_hits = generate_talk(
        lambda p, *m: ask(p, *m, key=key), "boss", profile, jd
    )
    print(new)
    print(f"\n禁用词命中：{new_hits if new_hits else '无（校验通过）'}")

    print("\n" + "=" * 70)
    print("\n【新版 · 邮件/网申自我介绍】\n")
    mail, mail_hits = generate_talk(
        lambda p, *m: ask(p, *m, key=key), "email", profile, jd
    )
    print(mail)
    print(f"\n禁用词命中：{mail_hits if mail_hits else '无（校验通过）'}")


if __name__ == "__main__":
    main()
