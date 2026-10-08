# -*- coding: utf-8 -*-
"""生成 v3 评估集：从语料里挑真实块 → 让模型写出"用户会怎么问" → 存成 jsonl

为什么要自动生成而不是手写：
  手写 50 条会挑"我知道答案在哪"的问题，天然偏简单；这里从**库里真实存在的块**
  反向生成问题，覆盖面更广，也更接近真实用户提问（每条都带 ground truth 块 id，
  评估时直接算 Recall@k / MRR，不靠"关键词猜命中"）。

产出：rag2/eval/eval_v3.jsonl
   {"id","q","chunk_id","source","head","kw","kind":"answerable"|"no_answer"}

用法：
    python build_eval_set.py --rebuild        # 先按当前语料重建索引（28 篇）
    python build_eval_set.py                  # 只生成评估集
    python build_eval_set.py --n 42           # 生成 42 条可回答题（默认 42）
"""
import argparse
import json
import os
import random
import re
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from engine import get_engine
from qa import ask_deepseek

EVAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval")
EVAL_PATH = os.path.join(EVAL_DIR, "eval_v3.jsonl")

GEN_PROMPT = """下面给你 {n} 段中文资料片段。请为**每一段**写一个用户可能会问的问题。

要求：
1. 问题要像真人提问，可以用资料里的术语，但不要照抄整句
2. 问题必须只靠那一段资料就能回答（不要问需要跨段综合的问题）
3. 同时给出一个"答案里几乎必然出现的关键词"（从该段资料里挑一个专有名词或术语）
4. 只输出 JSON 数组，元素形如 {{"i": 1, "q": "问题", "kw": "关键词"}}，不要解释

资料片段：
{chunks}
"""

# 明确问"库里肯定没有"的内容，用来测拒答
NO_ANSWER = [
    "特斯拉 Model 3 的电池包容量是多少度？",
    "2026 年诺贝尔物理学奖颁给了谁？",
    "请帮我写一首关于秋天的七言绝句。",
    "Python 的 asyncio 事件循环底层是用什么语言实现的？",
    "南京到北京的高铁二等座票价多少钱？",
    "用一句话解释量子纠缠，并给出贝尔不等式的推导。",
    "这道菜（番茄炒蛋）的正宗做法是什么？",
    "2027 年春节是几月几号？",
]


def _is_useful(text):
    """过滤掉纯链接、纯表格、太短的块——它们不适合做问答素材。"""
    t = (text or "").strip()
    if not (150 <= len(t) <= 700):
        return False
    cn = len(re.findall(r"[\u4e00-\u9fff]", t))
    if cn < 60:                      # 中文太少（多为链接/数字）
        return False
    if t.count("http") >= 3:         # 链接堆
        return False
    return True


def pick_chunks(store, per_source=3, rng=None):
    rng = rng or random.Random(42)
    data = store.get_all()
    by_src = defaultdict(list)
    for cid, text, meta in zip(data["ids"], data["documents"], data["metadatas"]):
        if _is_useful(text):
            by_src[(meta or {}).get("source", "")].append((cid, text))
    picked = []
    for src in sorted(by_src):
        items = by_src[src]
        rng.shuffle(items)
        picked.extend((src, cid, text) for cid, text in items[:per_source])
    rng.shuffle(picked)
    return picked


def gen_batch(batch, api_key, retries=2):
    """一批 6 个块 → 模型写出对应问题。失败返回空列表。"""
    lines = []
    for i, (_src, _cid, text) in enumerate(batch, start=1):
        lines.append("[%d] %s" % (i, text.replace("\n", " ")[:420]))
    prompt = GEN_PROMPT.format(n=len(batch), chunks="\n\n".join(lines))
    for attempt in range(retries + 1):
        try:
            raw = ask_deepseek("请按格式输出 JSON 数组。", [
                {"source": "（占位）", "text": prompt}], api_key, temperature=0.4,
                max_tokens=1500)
            m = re.search(r"\[.*\]", raw, re.S)
            if m:
                rows = json.loads(m.group(0))
                out = []
                for r in rows:
                    i = int(r.get("i", 0))
                    if 1 <= i <= len(batch):
                        out.append((batch[i - 1], r.get("q", "").strip(),
                                    r.get("kw", "").strip()))
                return out
        except Exception:
            time.sleep(2)
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="先按当前语料重建索引")
    ap.add_argument("--n", type=int, default=42, help="可回答题条数（默认 42）")
    ap.add_argument("--per-source", type=int, default=3, help="每篇最多取几个块做素材")
    args = ap.parse_args()

    engine = get_engine()
    if args.rebuild:
        print("[1/4] 重建索引（当前语料 %d 个目录）..." % len(config.DOCS_DIRS))
        engine.ensure_index(force=True)
    print("[1/4] 索引块数 =", engine.store.count())

    api_key = config.get_api_key()
    if not api_key:
        raise SystemExit("没有 API key，无法生成评估集")

    print("[2/4] 挑选候选块 ...")
    cands = pick_chunks(engine.store, per_source=args.per_source)
    print("     可用候选块 =", len(cands))

    os.makedirs(EVAL_DIR, exist_ok=True)
    rows, seen_q = [], set()
    print("[3/4] 分批让模型出题 ...")
    B = 6
    for start in range(0, len(cands), B):
        if len(rows) >= args.n:
            break
        batch = cands[start:start + B]
        got = gen_batch(batch, api_key)
        for (src, cid, text), q, kw in got:
            if not q or not kw or q in seen_q:
                continue
            if kw not in text:              # 关键词必须真出自该块，否则丢弃
                continue
            seen_q.add(q)
            rows.append({
                "id": "a%02d" % (len(rows) + 1),
                "q": q,
                "chunk_id": cid,
                "source": src,
                "head": text[:40].replace("\n", " "),
                "kw": kw,
                "kind": "answerable",
            })
        print("     已生成 %d / %d" % (len(rows), args.n))
        time.sleep(0.5)

    rows = rows[:args.n]
    for i, q in enumerate(NO_ANSWER, start=1):
        rows.append({
            "id": "n%02d" % i, "q": q, "chunk_id": "", "source": "",
            "head": "", "kw": "", "kind": "no_answer",
        })

    with open(EVAL_PATH, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n_ans = sum(1 for r in rows if r["kind"] == "answerable")
    print("[4/4] 写出 %s：%d 条（可回答 %d + 拒答 %d）"
          % (EVAL_PATH, len(rows), n_ans, len(rows) - n_ans))
    srcs = defaultdict(int)
    for r in rows:
        if r["kind"] == "answerable":
            srcs[r["source"]] += 1
    print("     覆盖资料 %d 篇：" % len(srcs))
    for s, c in sorted(srcs.items(), key=lambda x: -x[1]):
        print("       %2d  %s" % (c, s))


if __name__ == "__main__":
    main()
