# -*- coding: utf-8 -*-
"""
自我蒸馏模块端到端测试：用一组示例答案跑一遍，看 6 份产物长什么样。
不会覆盖你真实的 data/*.md（输出写到 data/distill_test/）。

跑法：python offeragent\test_distill.py
"""
import re
import sys
from pathlib import Path

import requests

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import distill  # noqa: E402

SECRETS = HERE / ".streamlit" / "secrets.toml"
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"

# 示例答案（用来验证产出结构，不是余剑的真实答案）
SAMPLE = {
    "q1": "RAG 知识库问答系统，个人笔记变成能问答的知识库；还有一个 Agent 工具调用 Demo，让模型按 JSON 调计算工具。",
    "q2": "RAG：11 篇资料切 254 块，自建 12 条评估集，top-1/3/5 = 75%/83%/92%。Demo：3 个工具，能拦 5 类坏输出。",
    "q3": "RAG 部署过 Streamlit Cloud，后来因为省 costs 下线了；代码在 GitHub。",
    "q4": "把链路跑通这件事最顺，从读文件到检索到生成，我能一块块拆开调。",
    "q5": "从空白文件写新功能最容易卡，看得懂别人的代码但自己起手难。",
    "q6": "LangChain、Docker、模型微调、多 Agent，都没做过。",
    "q7": "先找一个能跑的最小例子改，改着改着再回头看原理。",
    "q8": "看官方文档加抄改现成代码，然后做一个小 demo 验证。",
    "q9": "下午和晚上效率高，一个人安静时最好；有人催或者任务目标不清楚时容易停住。",
    "q10": "好奇占一半，另一半是想快点有作品去面试。",
    "q11": "先硬扛一会儿，扛不动就换别的任务缓一下，很少主动找人。",
    "q12": "最不能接受目标是天天变、没人带又要我出结果的活。",
    "q13": "喜欢各做一块最后合，但自己一个人做也行，同步太频繁会打断我。",
    "q14": "先列出来对比，实在分不清就问人。",
    "q15": "队友说过我执行快、能自己查资料；也说过我有时候钻牛角尖、不太主动说话。",
}


def load_key() -> str:
    m = re.search(r'DEEPSEEK_API_KEY\s*=\s*"([^"]+)"',
                  SECRETS.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit("没找到 API Key")
    return m.group(1)


def main():
    key = load_key()

    def ask(prompt: str) -> str:
        r = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}]},
            timeout=180,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    state = {"answers": SAMPLE, "followups": {}}
    print(f"模拟进度：{distill.progress(state)}")
    out_dir = HERE / "data" / "distill_test"
    outputs = distill.distill(state, ask, out_dir=out_dir)
    print(f"\n生成 {len(outputs)} 份文件 → {out_dir}")
    for name in ["profile.md", "highlights.md", "interview_answers.md",
                 "gaps.md", "work_style.md", "clone_brief.md"]:
        content = outputs.get(name, "")
        print("\n" + "=" * 70)
        print(f"【{name}】 {len(content)} 字")
        print("=" * 70)
        print(content[:1500])


if __name__ == "__main__":
    main()
