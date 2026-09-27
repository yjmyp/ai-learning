# -*- coding: utf-8 -*-
"""
self_distill.py —— Self-Distill 第一步：读 me.txt → 调大模型 → 生成个人画像

v1 完成定义：跑通「读文件 → 调模型 → 存 profile.md」，输出一份像“我”的画像。

读这份文件时，你要能回答三个问题（守则第 4 条要求的“讲得出”）：
  1. 输入是什么？ → offeragent/me.txt 里的文字
  2. 输出是什么？ → offeragent/profile.md（模型生成的个人画像）
  3. 失败会怎样？ → 文件不存在 / 没 key / 网络断 / 模型报错，分别在哪一行崩
"""
import os
import sys

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(BASE_DIR)
ME_PATH = os.path.join(BASE_DIR, "me.txt")
OUT_PATH = os.path.join(BASE_DIR, "profile.md")

API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-chat"


def load_api_key():
    """取 key：环境变量 → 根目录 local_key.py（不把 key 写死在代码里）"""
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key

    local_key = os.path.join(REPO_ROOT, "local_key.py")
    if os.path.exists(local_key):
        ns = {}
        with open(local_key, encoding="utf-8") as f:
            exec(f.read(), ns)          # 执行这个文件，把里面的变量取出来
        return str(ns.get("API_KEY", "")).strip()
    return ""


def read_me(path=ME_PATH):
    """读素材：和你今天写的 practice_02.py 是同一件事"""
    with open(path, encoding="utf-8") as f:
        return f.read()


PROFILE_SECTIONS = """1. 一句话定位（你是谁，一句话说清）
2. 优势（每条必须带 me.txt 里的具体事实或数字）
3. 短板（诚实，不许安慰）
4. 适配岗位方向（按匹配度排序，给理由）"""

# ===== prompt 模板（改动实验 2 改这里；{me} 和 {sections} 会被自动填进去）=====
PROMPT_TEMPLATE = """你是一位做过大量技术岗招聘的职业顾问，擅长从原始材料里提炼真实的个人画像。

下面是一个学生的个人素材：

<素材>
{me}
</素材>

请严格按以下板块输出画像：
{sections}

硬性要求：
1. 每个结论都要引用素材里的具体事实（项目名、数字、技术栈），不许空泛
2. 素材里没有的信息写“未知”，不要编造
3. 语言直接，不要励志，不要安慰
4. 每个结论前必须标注【事实】或【推断】，判定标准：
   【事实】= 素材里直接写出的客观信息（学校、项目、数字、技术栈、做过/没做过什么）
   【推断】= 涉及未来、他人反应、能力评价、竞争力的判断
   示例：素材写"算法只完成 8 题" → 【事实】算法只完成 8 题
        由此推出"笔试过不了" → 【推断】笔试大概率过不了
   如果一句话里既有事实又有推断，拆成两句分别标注
"""


def call_llm(prompt, api_key):
    """把 prompt 发给 DeepSeek，拿回回答"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
    }
    r = requests.post(API_URL, headers=headers, json=data, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def main():
    api_key = load_api_key()
    if not api_key:
        print("找不到 API key：检查根目录 local_key.py 或环境变量 DEEPSEEK_API_KEY")
        sys.exit(1)

    me = read_me()
    print(f"[1/3] 读完 me.txt：{len(me)} 个字符")

    prompt = PROMPT_TEMPLATE.format(me=me, sections=PROFILE_SECTIONS)
    print(f"[2/3] prompt 拼好：{len(prompt)} 个字符，正在调模型 ...")

    try:
        profile = call_llm(prompt, api_key)
    except Exception as e:
        print(f"[2/3] 调模型失败：{e}")
        sys.exit(1)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(profile)

    print(f"[3/3] 画像已保存：{OUT_PATH}")
    print("-" * 40)
    print(profile)


if __name__ == "__main__":
    main()
