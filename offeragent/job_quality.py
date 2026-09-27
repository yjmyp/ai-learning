# -*- coding: utf-8 -*-
"""
job_quality · 岗位质量检查（假岗 / 僵尸岗识别）
================================================
设计原则：只用能验证的信号，不做主观猜测。每条结论都要能说清依据。
纯规则实现，不调用大模型：快、免费、可解释、结果稳定。

检查项与依据：
  1. JD 内容过少        JD + 其他信息总长 < 60 字
  2. 没有公司名         公司字段为空或是 company#xxx 占位
  3. 薪资区间过宽       上限 > 下限 x 5（例如 10-1000/天）
  4. 薪资明显偏低       一线/新一线城市上限 < 80/天
  5. JD 像模板复读      同时出现"岗位职责"和"任职要求"但全文 < 200 字
  6. 发布时间过久       平台最后刷新时间超过 60 天（牛客提供）
  7. 缺链接             没有可点开的岗位详情链接
"""
import re


def assess(job: dict) -> dict:
    """评估一个岗位。返回 {score, verdict, flags}"""
    flags = []
    score = 100
    jd = ((job.get("jd") or "") + " " + (job.get("extra") or "")).strip()

    def add(problem, evidence, penalty):
        flags.append({"problem": problem, "evidence": evidence, "penalty": penalty})
        return penalty

    if len(jd) < 60:
        score -= add("JD 内容过少", f"职责与要求一共 {len(jd)} 字", 25)

    comp = (job.get("company") or "").strip()
    if not comp or comp.startswith("company#"):
        score -= add("看不到公司名", "平台没返回公司名称", 20)

    sal = (job.get("salary") or "").replace(" ", "")
    m = re.match(r"(\d+)-(\d+)", sal)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo <= 0:
            score -= add("薪资下限异常", f"原文 {sal}", 12)
        elif hi > lo * 5:
            score -= add("薪资区间过宽",
                         f"原文 {sal}（上限是下限的 {hi // max(lo, 1)} 倍）", 10)
        cities = ("南京", "上海", "北京", "深圳", "杭州", "广州", "苏州")
        if hi < 80 and (job.get("city") or "") in cities:
            score -= add("薪资偏低", f"{job.get('city')} 实习上限 {hi}/天", 10)

    has_duty = ("岗位职责" in jd) or ("职位描述" in jd)
    has_req = ("任职要求" in jd) or ("任职资格" in jd)
    if has_duty and has_req and len(jd) < 200:
        score -= add("JD 像模板复读", f"同时出现职责与要求，全文只有 {len(jd)} 字", 10)

    days = job.get("posted_days")
    if isinstance(days, int) and days >= 60:
        score -= add("岗位可能挂很久了", f"平台最后刷新在 {days} 天前", 20)

    if not (job.get("url") or "").startswith("http"):
        score -= add("没有岗位链接", "无法点开原文核对", 8)

    score = max(0, min(100, score))
    verdict = "正常" if score >= 80 else ("存疑" if score >= 60 else "疑似僵尸岗")
    return {"score": score, "verdict": verdict, "flags": flags}


def summarize(result: dict) -> str:
    """一句话总结，用于列表显示。"""
    if result["verdict"] == "正常":
        return f"质量 {result['score']} 分（没发现明显问题）"
    first = result["flags"][0]["problem"] if result["flags"] else "有问题"
    return f"质量 {result['score']} 分 · {result['verdict']}（{first}）"
