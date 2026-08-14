# -*- coding: utf-8 -*-
"""问答：把检索结果拼进 Prompt，调 DeepSeek 生成带引用的回答"""
import requests

from config import LLM_MODEL, LLM_URL


def build_prompt(question, chunks):
    lines = ["你是学习助手。请严格只根据下面提供的资料回答，", 
             "资料里没有的内容，直接回答“资料里没有相关内容”。",
             "回答中引用资料处，用 [编号] 标注（例如 [1]）。", "", "资料："]
    for i, c in enumerate(chunks):
        src = c.get("source", "未知来源")
        lines.append(f"[{i + 1}] 来源：{src}\n{c['text']}")
    lines.append("")
    lines.append(f"问题：{question}")
    return "\n\n".join(lines)


def ask_deepseek(question, chunks, api_key, temperature=0.3, max_tokens=1024):
    """调 DeepSeek 生成回答；chunks 来自 retriever.retrieve()"""
    messages = [
        {"role": "system", "content": "你是学习助手，回答要简洁、准确、可溯源。"},
        {"role": "user", "content": build_prompt(question, chunks)},
    ]
    resp = requests.post(
        LLM_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]
