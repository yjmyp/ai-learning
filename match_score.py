# -*- coding: utf-8 -*-
"""结构化匹配打分（本地可复算，不调大模型）

为什么换掉"让模型说一个数"：
  1. 不可解释 —— 面试官问"82 分怎么来的"，答不出
  2. 不可复现 —— 同一个 JD 跑两次可能 78 和 86，无法做回归
  3. 会漂移 —— 换了提示词/模型，历史分数就废了

改成五个维度、本地规则计算、每维都给命中/缺失证据：
  硬技能(0.30) / 项目证据(0.25) / 地点(0.15) / 时间(0.15) / 门槛(0.15)

  · 硬技能 = JD 里出现的技能词，有多少在你的技能清单里
  · 项目证据 = JD 里的技能词，有多少出现在你的项目描述里（证明"做过"）
  · 地点 = JD 城市 vs 你的意向（南京 / 远程）
  · 时间 = JD 的到岗/每周天数/实习时长要求 vs 你的可实习条件
  · 门槛 = JD 的学历/届别/经验要求 vs 你的实际情况（会把"硕士"这类硬门槛直接扣掉）

输出里同时给 hard_blocks（硬门槛冲突）——这类岗位分数再高也不该投。

用法：
    python match_score.py --all                # 给全部岗位打结构化分并回填 meta
    python match_score.py --all --dry-run      # 只看分数和维度，不写文件
    python match_score.py --job <岗位名>        # 单个岗位，打印完整维度明细
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "offeragent"))

JDS_DIR = os.path.join(HERE, "offeragent", "data", "jds")
PROFILE_PATH = os.path.join(HERE, "offeragent", "data", "profile.md")
ME_PATH = os.path.join(HERE, "offeragent", "me.txt")
META_SUFFIX = ".meta.json"
GATE_SCORE = 60

# 技能词表：分组只是为了讲得清楚，匹配时统一处理（同一组内任一写法命中即算）
SKILL_LEXICON = {
    "语言/基础": ["python", "sql", "java", "go", "c++", "http", "linux", "数据结构", "算法"],
    "大模型/应用": ["llm", "大模型", "rag", "检索增强", "prompt", "提示词", "agent", "智能体",
                    "function calling", "工具调用", "mcp", "多轮", "记忆", "微调", "lora",
                    "sft", "评测", "eval", "embedding", "向量", "重排", "rerank", "幻觉",
                    "上下文", "token", "多模态", "transformer", "attention"],
    "框架/工具": ["langchain", "langgraph", "llamaindex", "dify", "coze", "crewai",
                  "autogen", "openai", "deepseek", "qwen", "通义", "claude", "huggingface",
                  "transformers", "sentence-transformers", "bge", "chroma", "milvus",
                  "faiss", "qdrant", "pgvector", "elasticsearch", "bm25"],
    "工程/部署": ["fastapi", "flask", "streamlit", "docker", "k8s", "kubernetes", "git",
                  "redis", "mysql", "postgres", "mongodb", "并发", "异步", "微服务",
                  "部署", "ci", "接口", "rest", "api"],
}
SKILL_TERMS = [w for group in SKILL_LEXICON.values() for w in group]

# 门槛词：命中就说明"这条要求可能卡住我"
DEGREE_PAT = re.compile(r"(硕士|研究生|博士|本科及以上|统招本科|985|211|双一流)")
EXPERIENCE_PAT = re.compile(r"(\d+\s*年[以上]*经验|经验不限|有实习经验|实习经历)")
GRADE_PAT = re.compile(r"(20\d{2}\s*届|2[0-9]\s*届)")
# 方向词：算法/训练类岗位和"AI 应用开发"是两条路，方向不符要扣分（不是硬门槛，但别白投）
ALGO_PAT = re.compile(r"(算法|推荐|搜索|排序|模型训练|预训练|微调|SFT|RLHF|推理优化|蒸馏|"
                      r"论文|顶会|PyTorch|TensorFlow|深度学习|NLP|CV)")
APP_PAT = re.compile(r"(应用|工程|开发|Agent|智能体|RAG|知识库|LLM 应用|落地|平台|业务)")
ONSITE_PAT = re.compile(r"(线下|坐班|onsite|到岗|每周\s*\d\s*天|[3-5]\s*天/周)")


def _lower(s):
    return (s or "").lower()


def load_text(path, default=""):
    try:
        return open(path, encoding="utf-8").read()
    except Exception:
        return default


def profile_text():
    return load_text(PROFILE_PATH) or load_text(ME_PATH)


def hit_terms(text, terms):
    t = _lower(text)
    return [w for w in terms if w.lower() in t]


def split_profile(p):
    """把画像拆成"技能区"和"项目区"，用于分别算硬技能与项目证据。"""
    if not p:
        return "", ""
    # 注意：画像开头常有「| 项目 | 内容 |」这种表格表头，直接找"项目"会把技能区切没。
    # 只在明确的分节标题上切，且切点必须在文件后半段，否则整篇都给两边用。
    for marker in ("## 三、项目", "## 项目经历", "## 项目画像", "代表项目", "项目经历"):
        i = p.find(marker)
        if i > len(p) * 0.3:
            return p[:i], p[i:]
    return p, p


def score_job(profile, jd_text, meta=None, name=""):
    """返回结构化评分 dict（纯本地计算，同样的输入永远同样的输出）。"""
    meta = meta or {}
    jd = jd_text or ""
    skill_part, proj_part = split_profile(profile)
    jd_terms = hit_terms(jd, SKILL_TERMS)

    # ① 硬技能
    my_skills = set(hit_terms(skill_part, SKILL_TERMS))
    if jd_terms:
        matched = [w for w in jd_terms if w in my_skills]
        missing = [w for w in jd_terms if w not in my_skills]
        # 饱和度处理：JD 常列一堆技能词（java/go/c++ 这种），按"命中 4~8 个核心词即满分"算，
        # 否则纯覆盖率会让所有岗位都低分（实测：不饱和时最高分只有 55，门禁全卡）。
        denom = max(4, min(len(jd_terms), 8))
        skills_raw = min(1.0, len(matched) / denom)
    else:
        matched, missing, skills_raw = [], [], 0.5      # JD 没写技能词 → 给中性分
    # ② 项目证据
    proj_terms = set(hit_terms(proj_part, SKILL_TERMS))
    if jd_terms:
        proven = [w for w in jd_terms if w in proj_terms]
        denom = max(3, min(len(jd_terms), 6))          # 项目证据比技能更难命中，分母放小一点
        proj_raw = min(1.0, len(proven) / denom)
    else:
        proven, proj_raw = [], 0.5
    # ③ 地点
    city = (meta.get("city") or "").strip()
    jd_city_hit = re.findall(r"(南京|苏州|上海|杭州|北京|深圳|广州|成都|武汉|西安|远程|全国)", jd)
    if not city and jd_city_hit:
        city = jd_city_hit[0]
    if not city:
        city_raw, city_note = 0.7, "城市未标注"
    elif "南京" in city or "远程" in jd or "全国" in jd:
        city_raw, city_note = 1.0, "南京/可远程，符合意向"
    elif city in ("苏州", "上海", "杭州"):
        city_raw, city_note = 0.6, f"{city}：需通勤/异地，可谈"
    else:
        city_raw, city_note = 0.35, f"{city}：异地且非意向城市"
    # ④ 时间
    days = re.findall(r"([3-6])\s*天\s*/?\s*周", jd)
    months = re.findall(r"(\d+)\s*个月", jd)
    if days and int(days[0]) > 5:
        time_raw, time_note = 0.4, f"要求每周 {days[0]} 天（超 5 天）"
    elif months and int(months[0]) > 12:
        time_raw, time_note = 0.5, f"要求实习 {months[0]} 个月（偏长）"
    else:
        time_raw, time_note = 1.0, "到岗与时长可满足（4-5 天/周，6 个月+）"
    # ⑤ 门槛
    hard_blocks, gate_raw = [], 1.0
    degree = DEGREE_PAT.findall(jd)
    if degree and any(d in ("硕士", "研究生", "博士") for d in degree):
        hard_blocks.append("学历要求硕士/研究生")
        gate_raw -= 0.5
    if "985" in jd or "211" in jd or "双一流" in jd:
        hard_blocks.append("院校要求 985/211/双一流")
        gate_raw -= 0.2
    exp = EXPERIENCE_PAT.findall(jd)
    if any(re.search(r"\d+\s*年", e) for e in exp):
        hard_blocks.append("要求工作经验年限")
        gate_raw -= 0.3
    grade = GRADE_PAT.findall(jd)
    if grade and not any(("2027" in g) or re.match(r"^2?27\s*届", g) for g in grade):
        hard_blocks.append(f"届别要求 {grade[0]}（我是 2027 届）")
        gate_raw -= 0.3
    # 方向匹配：以岗位**标题**为准（JD 正文里"工程/开发"这类词太泛，容易失效）。
    # 标题里是算法/推荐/搜索/NLP/CV 且不含应用/Agent → 方向不符，扣分。
    # 标题信号取三处：meta.title（搜岗入库时写的）、meta.name、文件名（手工入库时只有文件名）
    title = " ".join([str(meta.get("title") or ""), str(meta.get("name") or ""), name or ""])
    if ALGO_PAT.search(title) and not APP_PAT.search(title):
        gate_raw -= 0.35
        hard_blocks.append("方向偏算法/训练（你主投 AI 应用开发）")
    gate_raw = max(0.0, gate_raw)

    dims = [
        ("skills", "硬技能匹配", 0.30, skills_raw,
         "命中 " + (("、".join(matched[:8])) or "无") +
         (("；缺 " + "、".join(missing[:8])) if missing else "")),
        ("project", "项目证据", 0.25, proj_raw,
         "项目里能证明的：" + (("、".join(proven[:8])) or "无")),
        ("city", "地点匹配", 0.15, city_raw, city_note),
        ("time", "时间匹配", 0.15, time_raw, time_note),
        ("gate", "门槛匹配", 0.15, gate_raw,
         ("硬门槛：" + "；".join(hard_blocks)) if hard_blocks else "未发现硬门槛冲突"),
    ]
    total = sum(w * raw for _k, _l, w, raw, _e in dims) * 100
    score = int(round(total))
    return {
        "score": score,
        "verdict": ("建议投" if score >= GATE_SCORE and not hard_blocks
                    else ("不建议投（硬门槛：" + "；".join(hard_blocks) + "）"
                          if hard_blocks else f"不建议投（匹配分 {score} < {GATE_SCORE}）")),
        "dims": [{"key": k, "label": l, "weight": w, "score": round(raw * 100),
                  "evidence": e} for k, l, w, raw, e in dims],
        "jd_terms": jd_terms[:20],
        "matched": matched[:20],
        "missing": missing[:20],
        "hard_blocks": hard_blocks,
        "method": "structured-v1（本地五维加权，无模型参与）",
    }


def load_jobs():
    """读岗位库：返回 [(name, meta, jd_text)]。"""
    out = []
    if not os.path.isdir(JDS_DIR):
        return out
    for fn in sorted(os.listdir(JDS_DIR)):
        if not fn.endswith(META_SUFFIX):
            continue
        name = fn[:-len(META_SUFFIX)]
        meta = {}
        try:
            meta = json.load(open(os.path.join(JDS_DIR, fn), encoding="utf-8"))
        except Exception:
            pass
        jd = load_text(os.path.join(JDS_DIR, name + ".txt"))
        out.append((name, meta, jd))
    return out


def save_score(name, meta, result):
    """把结构化分写回 meta（保持 meta.json 是分数的唯一权威源）。"""
    meta["match_score"] = result["score"]
    meta["match_method"] = result["method"]
    meta["match_dims"] = result["dims"]
    meta["match_missing"] = result["missing"]
    meta["match_hard_blocks"] = result["hard_blocks"]
    meta["match_verdict"] = result["verdict"]
    with open(os.path.join(JDS_DIR, name + META_SUFFIX), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="给所有岗位打分")
    ap.add_argument("--job", default="", help="只打一个岗位（打印明细）")
    ap.add_argument("--dry-run", action="store_true", help="不写 meta")
    args = ap.parse_args()

    profile = profile_text()
    if not profile.strip():
        raise SystemExit("读不到画像（offeragent/data/profile.md 或 me.txt）")
    jobs = load_jobs()
    if args.job:
        jobs = [j for j in jobs if args.job in j[0]]
    if not jobs:
        raise SystemExit("没有匹配到岗位")

    rows = []
    for name, meta, jd in jobs:
        res = score_job(profile, jd, meta, name=name)
        rows.append((name, meta, res))
        if args.job:
            print("=" * 70)
            print(f"{name}  总分 {res['score']}  |  {res['verdict']}")
            for d in res["dims"]:
                print(f"  {d['label']}(权重{d['weight']:.2f}) = {d['score']:>3}  {d['evidence']}")
            if res["missing"]:
                print("  缺失技能：", "、".join(res["missing"]))
    if not args.dry_run:
        for name, meta, res in rows:
            save_score(name, meta, res)

    rows.sort(key=lambda x: -x[2]["score"])
    print()
    print("按结构化匹配分排序（%d 个岗位）：" % len(rows))
    print("  %-42s %5s  %s" % ("岗位", "分数", "结论"))
    for name, _meta, res in rows[:20]:
        print("  %-42s %5d  %s" % (name[:40], res["score"], res["verdict"][:40]))
    if args.dry_run:
        print("\n（--dry-run：没有写回 meta）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
