# -*- coding: utf-8 -*-
"""
make_code_pack.py · OfferAgent 代码打包器
==========================================
把指定的核心代码文件合并成一个 Markdown 代码包，喂给 DeepSeek / 其他 AI，
让它能看到完整代码并逐行讲解。

用法：
    python make_code_pack.py            # 生成全部代码包
    python make_code_pack.py resume     # 只生成 resume 包
    python make_code_pack.py agent      # 只生成 agent 引擎包

新增打包内容：往 PACKS 里加一组 files 即可，不用改其他逻辑。
安全：local_key.py / secrets.toml 永不打包（硬排除）。
"""
import io
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\29947\Documents\Codex\ai-learning")
OUT_DIR = ROOT / "offeragent" / "docs" / "code_packs"

# 硬排除：密钥、临时文件、数据
EXCLUDE = {"local_key.py", ".streamlit", "secrets.toml", "data", "jds", "assets"}

PACKS = {
    "resume": {
        "title": "简历系统 + 应用入口（当前教学主线）",
        "desc": ("内容包括：简历三层（content/styles/templates）+ 简历页 + 数据层/AI层/入口。"
                 "目标是让 AI 能讲透「数据与表现分离 + 注册表」模式，并带我加第 8 套模板。"),
        "files": [
            "offeragent/resume_content.py",
            "offeragent/resume_styles.py",
            "offeragent/resume_templates.py",
            "offeragent/pages_resume.py",
            "offeragent/store.py",
            "offeragent/llm.py",
            "offeragent/offer_agent_app.py",
        ],
    },
    "agent": {
        "title": "Agent 引擎核心（自研 ReAct 循环 + 工具守卫 + 并发打分）",
        "desc": ("内容包括：引擎（状态对象 + ReAct 循环 + 预算上限）、工具注册表（schema 合同 + "
                 "守卫拦截 + 错误回填）、批量打分（线程池并发）、评估脚本、提示词。"
                 "目标是让 AI 带我从头手敲引擎循环和 _score_one。"),
        "files": [
            "offer_agent_core.py",
            "offer_agent_tools.py",
            "batch_score.py",
            "eval_agent.py",
            "offeragent/prompts.py",
            "offeragent/llm.py",
        ],
    },
}


def read_safe(rel: str):
    """读文件；被硬排除的路径返回 None。"""
    if any(seg in EXCLUDE for seg in Path(rel).parts):
        return None
    p = ROOT / rel
    if not p.exists():
        return None
    try:
        return io.open(p, encoding="utf-8").read()
    except Exception:
        return None


def build_pack(name: str, cfg: dict) -> str:
    lines = [
        f"# 代码包：{cfg['title']}",
        "",
        f"> {cfg['desc']}",
        "",
        "## 怎么喂",
        "把本文件全文复制给 DeepSeek，开头加一句：",
        "> 「先读完全文代码，再按我的水平逐块讲解，一次一小步，先框架后填空，不直接给完整答案。」",
        "",
        "## 包含的文件",
        "",
        "| 文件 | 行数 | 说明 |",
        "|---|---|---|",
    ]
    total = 0
    for rel in cfg["files"]:
        txt = read_safe(rel)
        if txt is None:
            continue
        n = txt.count("\n") + 1
        total += n
        lines.append(f"| `{rel}` | {n} | 见下方代码 |")
    lines += ["", f"**合计 {total} 行**（约 {total * 4 // 1024}KB），在 DeepSeek 上下文内。", ""]
    lines += ["---", ""]

    for rel in cfg["files"]:
        txt = read_safe(rel)
        if txt is None:
            lines += [f"## ⚠️ 未找到: {rel}", ""]
            continue
        n = txt.count("\n") + 1
        lines += [f"## ===== {rel}（{n} 行）=====", "",
                  "```python", txt.rstrip("\n"), "```", ""]
    return "\n".join(lines)


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    made = []
    for name, cfg in PACKS.items():
        if only and name != only:
            continue
        out = OUT_DIR / f"code_pack_{name}.md"
        io.open(out, "w", encoding="utf-8", newline="").write(build_pack(name, cfg))
        made.append((out.name, out.stat().st_size // 1024))
    if made:
        for name, kb in made:
            print(f"OK  {name}  ({kb} KB)")
    else:
        print(f"未知包名: {only}，可选: {list(PACKS)}")


if __name__ == "__main__":
    main()
