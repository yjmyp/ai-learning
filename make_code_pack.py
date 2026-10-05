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

# 硬排除：密钥、浏览器配置、二进制库、图片与临时验证物（永不打包）
EXCLUDE = {"local_key.py", ".streamlit", "secrets.toml", "edge_profile",
           "memory.db", "memory_worker.db", "shots", "ocr_test.png",
           "_pv_verify.html", "_pv_issue_summary.md", "config.json"}

# 按扩展名选代码块语言
LANG = {".py": "python", ".json": "json", ".jsonl": "json", ".md": "markdown",
        ".txt": "text", ".toml": "toml", ".yaml": "yaml", ".yml": "yaml"}

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
    "jobs": {
        "title": "求职链路核心（搜岗 → 打分 → 门禁 → 投递）",
        "desc": ("内容包括：搜岗多源入库、找工作/投递页面、话术生成（禁用词防 AI 腔）、"
                 "岗位质量分、岗位详情、公司查询、ATS 关键词覆盖、面试拷问、流程条。"
                 "目标是让 AI 讲透「搜岗→匹配→投递」数据链路。"),
        "files": [
            "offeragent/job_sources.py",
            "offeragent/pages_work.py",
            "offeragent/pages_apply.py",
            "offeragent/apply_assist.py",
            "offeragent/interview_drill.py",
            "offeragent/job_quality.py",
            "offeragent/job_detail.py",
            "offeragent/company_lookup.py",
            "offeragent/pipeline.py",
            "offeragent/resume_tailor.py",
            "offeragent/browser_fetch.py",
            "offeragent/jd_fetcher.py",
        ],
    },
    "content": {
        "title": "内容生成与数字分身（蒸馏 / 简历生成 / 持久化）",
        "desc": ("内容包括：自我蒸馏（画像生成/聊天）、数字分身（HR 问答）、简历问答生成与清洗、"
                 "PDF 生成、OCR/文件读取、邮件解析、GitHub 数据同步。"
                 "目标是让 AI 讲透「把用户变成结构化画像 → 复用到投递/分身」这条线。"),
        "files": [
            "offeragent/distill.py",
            "offeragent/distill_chat.py",
            "offeragent/self_distill.py",
            "offeragent/digital_twin.py",
            "offeragent/resume_builder.py",
            "offeragent/resume_clean.py",
            "offeragent/make_resume_pdf.py",
            "offeragent/doc_io.py",
            "offeragent/inbox_parse.py",
            "offeragent/sync_data.py",
        ],
    },
    "pages": {
        "title": "页面域（首页 / 更多 / 分身 / Agent / 对比）",
        "desc": ("内容包括：今日台/蒸馏聊天首页、更多页（建议/设置/对比/公司/拷问/投递记录）、"
                 "数字分身页、Agent 控制台、对比页。"
                 "目标是让 AI 看懂 11 页面的 UI 编排方式。"),
        "files": [
            "offeragent/pages_home.py",
            "offeragent/pages_more.py",
            "offeragent/pages_twin.py",
            "offeragent/pages_agent.py",
            "offeragent/pages_match.py",
        ],
    },
    "theme": {
        "title": "主题与 UI 工具（视觉层）",
        "desc": ("内容包括：主题 CSS（theme.py，纯样式）、UI 公共组件（ui_kit.py）、"
                 "v41 模块。目标是让 AI 在需要改视觉时能看懂主题结构。"),
        "files": [
            "offeragent/theme.py",
            "offeragent/ui_kit.py",
            "offeragent/v41.py",
        ],
    },
    "tests": {
        "title": "测试与项目说明（26 个测试 + run_tests + README）",
        "desc": ("内容包括：26 个测试脚本、统一测试入口 run_tests.py、README。"
                 "目标是让 AI 看懂「测试怎么组织、怎么跑、断言什么」。"),
        "files": [
            "offeragent/test_*.py",
            "run_tests.py",
            "offeragent/README.md",
        ],
    },
    "data_jobs": {
        "title": "真实岗位数据（岗位库 + 匹配报告 + 话术 + 投递清单）",
        "desc": ("内容包括：data/jds/ 真实 JD 与 meta 打分、data/match_results/ 匹配分析报告、"
                 "话术队列、投递清单。目标是让 AI 看到「批量打分的输入输出长什么样」。"
                 "注意：含你的求职信息，喂给 DeepSeek 前请知悉。"),
        "files": [
            "offeragent/data/jds/*.txt",
            "offeragent/data/jds/*.meta.json",
            "offeragent/data/match_results/*.md",
            "offeragent/data/talk_queue.json",
            "offeragent/data/投递清单-2026-10-04.md",
        ],
    },
    "data_logs": {
        "title": "Agent 运行日志与蒸馏产物",
        "desc": ("内容包括：Agent trace 日志（agent_logs.jsonl）、蒸馏测试产物、"
                 "个人画像、蒸馏聊天记录。目标是让 AI 看懂「引擎 trace 与自我蒸馏的产物」。"
                 "注意：含个人信息，喂给 DeepSeek 前请知悉。"),
        "files": [
            "offeragent/data/agent_logs.jsonl",
            "offeragent/data/distill_test/*",
            "offeragent/data/profile.md",
            "offeragent/data/distill_chat.json",
        ],
    },
}


def resolve_files(patterns):
    """展开文件清单：支持 glob 通配（如 offeragent/test_*.py）。"""
    out = []
    for pat in patterns:
        # 无通配 → 单文件
        if "*" not in pat and "?" not in pat:
            if (ROOT / pat).is_file():
                out.append(pat)
            continue
        for p in sorted(ROOT.glob(pat)):
            if p.is_file():
                out.append(str(p.relative_to(ROOT)).replace("\\", "/"))
    return out


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
    files = resolve_files(cfg["files"])
    total = 0
    for rel in files:
        txt = read_safe(rel)
        if txt is None:
            continue
        n = txt.count("\n") + 1
        total += n
        lines.append(f"| `{rel}` | {n} | 见下方代码 |")
    lines += ["", f"**合计 {total} 行**（约 {total * 4 // 1024}KB），在 DeepSeek 上下文内。", ""]
    lines += ["---", ""]

    for rel in files:
        txt = read_safe(rel)
        if txt is None:
            lines += [f"## ⚠️ 未找到: {rel}", ""]
            continue
        n = txt.count("\n") + 1
        lang = LANG.get(Path(rel).suffix, "text")
        lines += [f"## ===== {rel}（{n} 行）=====", "",
                  f"```{lang}", txt.rstrip("\n"), "```", ""]
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
