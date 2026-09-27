# -*- coding: utf-8 -*-
"""联网搜岗实测：牛客（结构化解析）+ 实习僧（大模型抽取）。BOSS 需要先登录，跳过。"""
import re
import sys
from pathlib import Path

import requests

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import job_sources  # noqa: E402

SECRETS = HERE / ".streamlit" / "secrets.toml"
API_URL = "https://api.deepseek.com/chat/completions"


def load_key() -> str:
    m = re.search(r'DEEPSEEK_API_KEY\s*=\s*"([^"]+)"',
                  SECRETS.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("没找到 API Key")
    return m.group(1)


def make_ask(key):
    def ask(prompt: str) -> str:
        r = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json={"model": "deepseek-chat",
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=180,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    return ask


def show(name, jobs):
    print(f"\n【{name}】拿到 {len(jobs)} 条")
    for j in jobs[:5]:
        print(f"  - {j['title']} | {j['company']} | {j['city']} | {j['salary']}")
        if j.get("extra"):
            print(f"      {j['extra']}")
        if j.get("url"):
            print(f"      {j['url']}")


if __name__ == "__main__":
    key = load_key()
    ask = make_ask(key)
    try:
        show("牛客 · 关键词 AI", job_sources.search_nowcoder("AI", ""))
    except Exception as e:
        print("牛客失败:", type(e).__name__, str(e)[:120])
    try:
        show("实习僧 · AI / 南京", job_sources.search_shixiseng("AI", "南京", ask))
    except Exception as e:
        print("实习僧失败:", type(e).__name__, str(e)[:120])
    print("\n" + "=" * 70)
    print("多平台合并（牛客 + 实习僧 + BOSS）")
    res = job_sources.search_all("AI", "南京", ask_model=ask)
    print("各平台结果：", res["by_source"])
    for k, v in res["errors"].items():
        print(f"  失败 {k}：{v[:100]}")
    show("合并去重后", res["jobs"])
