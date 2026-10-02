# -*- coding: utf-8 -*-
"""建议/设置/对比/公司/简历/拷问/投递记录 —— OfferAgent 页面域模块（2026-09-29 从 offer_agent_app.py 拆出）"""
import json
import os
import re
import time
from pathlib import Path

import streamlit as st

# 分层公共层 + 业务子模块（宽 import 兜底，页面函数保持原名调用）
from store import *
from prompts import PROMPT_ADVICE
from pages_twin import find_avatar
from llm import *
from ui_kit import *
import apply_assist
import digital_twin
import distill
import job_sources
import theme
import job_quality
import resume_tailor
import interview_drill
import pipeline
import inbox_parse
import v41
import company_lookup
import job_detail
import doc_io
import resume_builder
import resume_clean
import resume_templates

def page_advice():
    hero("简历建议", "匹配报告 + 简历 → 3 条可执行修改建议")
    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    if not jobs:
        st.info("先到「岗位库」添加岗位")
        return
    name = st.selectbox("选择岗位", [j[0] for j in jobs], key="advice_pick")
    report = read_text(MATCH_DIR / f"match_{name}.md")
    if not report:
        st.warning("该岗位还没跑匹配，先到「匹配分析」页运行")
        return
    default_resume = read_text(BASE_DIR / ".." / "简历" / "余剑-简历-AI应用开发实习-v2.md") \
        if (BASE_DIR / ".." / "简历" / "余剑-简历-AI应用开发实习-v2.md").exists() else ""
    default_resume = resume_clean.clean(default_resume)[0]
    resume = st.text_area("简历全文（默认读取 v2，可粘贴覆盖）", default_resume,
                          height=300, key="resume_area")
    if st.button("📝 生成简历建议", type="primary"):
        resume = resume_clean.clean(resume)[0]
        with st.spinner("生成中…"):
            try:
                st.session_state["advice_result"] = ask_chat(PROMPT_ADVICE, report, resume)
            except Exception as e:
                st.error(str(e))
    advice = st.session_state.get("advice_result", "")
    if advice:
        st.markdown(advice)
        st.code(advice, language="markdown")


# ============================================================
# 页面：设置
# ============================================================
def page_settings():
    hero("设置", "API Key 与模型配置")
    ensure_dirs()
    api_key = get_api_key()
    if api_key:
        st.success("API Key 已配置（来自 Secrets/环境变量/本地配置）")
    else:
        st.warning("未配置 API Key")
    cfg = json.loads(read_text(CONFIG_PATH, "{}"))
    new_key = st.text_input("DeepSeek API Key（只保存在本机 data/config.json，不上传）",
                            value=cfg.get("api_key", ""), type="password")
    model = st.selectbox("模型", MODEL_OPTIONS,
                         index=MODEL_OPTIONS.index(cfg.get("model", DEFAULT_MODEL))
                         if cfg.get("model") in MODEL_OPTIONS else 0)
    if st.button("💾 保存设置", type="primary"):
        cfg["api_key"] = new_key.strip()
        cfg["model"] = model
        write_text(CONFIG_PATH, json.dumps(cfg, ensure_ascii=False, indent=2))
        st.success("设置已保存")
    st.markdown("---")
    st.markdown("##### 🎯 每日投递目标")
    st.caption("定一个每天要投几家的数，首屏会显示今天的完成进度。"
               "别定太高——连续投递比一次投很多更重要。")
    _tgt_now = int(cfg.get("daily_target", 3) or 3)
    tgt_new = st.number_input("每天投几家", min_value=1, max_value=20,
                              value=_tgt_now, key="set_target_in")
    if st.button("保存投递目标", key="set_target_save"):
        cfg["daily_target"] = int(tgt_new)
        write_text(CONFIG_PATH, json.dumps(cfg, ensure_ascii=False, indent=2))
        st.success(f"已保存：每天 {int(tgt_new)} 家")
    st.markdown("---")
    st.markdown("##### 💰 花费保护：每天最多调用几次模型")
    st.caption("公开链接被人乱点、或你自己狂跑批量匹配，都是按调用次数烧钱的。"
               "这里设一个每日上限，超过就拒绝调用并提示。填 0 = 不限制。")
    _lim_now = daily_limit()
    _left, _ = usage_left()
    new_lim = st.number_input("每日调用上限（次）", min_value=0, max_value=100000,
                              value=int(cfg.get("daily_call_limit", 200) or 200),
                              step=50, key="lim_in")
    st.caption(f"当前生效：{'不限' if _lim_now <= 0 else str(_lim_now) + ' 次'}　·　"
               f"今天已用 {0 if _lim_now <= 0 else _lim_now - _left} 次")
    if st.button("保存上限", key="lim_save"):
        cfg["daily_call_limit"] = int(new_lim)
        write_text(CONFIG_PATH, json.dumps(cfg, ensure_ascii=False, indent=2))
        st.success("已保存。部署版也可以在 Secrets 里加 `DAILY_CALL_LIMIT = \"100\"` 覆盖。")
    st.markdown("---")
    st.markdown("##### 连接测试")
    if st.button("🔌 测试 API 连接"):
        with st.spinner("测试中…"):
            try:
                st.success(f"连接正常：{ask_chat('只回复两个字：正常')[:50]}")
            except Exception as e:
                st.error(str(e))
    st.markdown("---")
    st.caption("部署到 Streamlit Cloud：Settings → Secrets 填入 "
               "`DEEPSEEK_API_KEY = \"sk-...\"` 即可。")
    st.markdown("---")
    st.caption("分享链接、名片页、简历导出都在「📇 展示」页；"
               "照片、简历正文和模板在「🎯 找工作 → 简历」页。")
    st.markdown("---")
    st.markdown("##### 🔒 访问密码（上线公网前设置）")
    st.caption("设置后访问应用需要先输密码。密码以 SHA-256 哈希保存在本机 config.json，"
               "不存明文；部署时也可用 Secrets 的 `APP_PASSWORD`。")
    cur_pw = st.text_input("设置/修改访问密码（留空 = 清除密码）", type="password",
                           key="set_pw")
    if st.button("保存密码", key="set_pw_save"):
        if cur_pw.strip():
            cfg["app_password_hash"] = v41.hash_password(cur_pw.strip())
            write_text(CONFIG_PATH, json.dumps(cfg, ensure_ascii=False, indent=2))
            st.success("访问密码已设置（哈希保存）。")
        else:
            cfg.pop("app_password_hash", None)
            write_text(CONFIG_PATH, json.dumps(cfg, ensure_ascii=False, indent=2))
            st.success("已清除访问密码。")


# ============================================================
# 入口
# ============================================================
def page_compare():
    """多个岗位并排对比。"""
    hero("岗位对比", "选 2-4 个岗位并排比：匹配度、五维评分、岗位质量、城市薪资")
    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    if len(jobs) < 2:
        st.info("至少要有 2 个岗位才能对比。先去「岗位库 / 关键词搜岗」加几个。")
        return
    names_all = [j[0] for j in jobs]
    picks = st.multiselect("选择岗位（2 到 4 个）", names_all,
                           default=names_all[:min(2, len(names_all))], key="cmp_pick")
    if len(picks) < 2:
        st.info("至少选 2 个岗位。")
        return
    meta_map = dict((j[0], j[1]) for j in jobs)
    rows = []
    for name in picks[:4]:
        meta = meta_map[name]
        report = read_text(MATCH_DIR / f"match_{name}.md")
        dims = extract_dim_scores(report) or {}
        jd = read_text(JDS_DIR / f"{name}.txt")
        q = job_quality.assess({"jd": jd, "company": meta.get("company", ""),
                                "city": meta.get("city", ""),
                                "url": meta.get("source_url", "")})
        rows.append({
            "岗位": name,
            "公司": meta.get("company") or "-",
            "城市": meta.get("city") or "-",
            "匹配度": meta.get("match_score") or "-",
            "岗位质量": q["score"],
            "质量结论": q["verdict"],
            "技术栈": dims.get("技术栈", "-"),
            "项目匹配": dims.get("项目匹配", "-"),
            "背景": dims.get("背景", "-"),
            "地点": dims.get("地点", "-"),
            "时长": dims.get("时长", "-"),
        })
    st.dataframe(rows, use_container_width=True)
    st.caption("匹配度来自「匹配分析」的报告；岗位质量来自规则检查（0-100，越高越可信）。"
               "没跑过匹配的岗位匹配度会显示 -。")
    for name in picks[:4]:
        report = read_text(MATCH_DIR / f"match_{name}.md")
        if report:
            with st.expander(f"{name} 的结论"):
                m = re.search(r"## 结论\s*\n+(.+)", report)
                st.markdown(m.group(1).strip() if m else "（报告里没找到结论段）")


def page_company():
    """公司速查（结论可信度较低，界面上显著提示）。"""
    hero("公司速查", "投之前先看一眼这家公司的公开线索（结论是线索，不是事实）")
    st.warning("这个功能的输出**可信度明显低于其它功能**：数据来自公开网页抓取 + 模型总结，"
               "可能过时或不完整。工商/融资/口碑没有权威免费接口，拿不到准数。"
               "**结论只能当线索，不要据此判断公司好坏。**")
    company = st.text_input("公司名", key="co_input", placeholder="例如：蔚蓝智能")
    if st.button("🔎 查一下（抓公开页面，约 20 秒）", type="primary"):
        if not company.strip():
            st.warning("先填公司名")
            return
        with st.spinner("抓公开页面 + 提取线索…"):
            try:
                st.session_state["co_out"] = company_lookup.lookup(
                    company.strip(), lambda p: ask_chat(p))
            except Exception as e:
                st.error(str(e))
    out = st.session_state.get("co_out")
    if not out:
        return
    if not out["report"]:
        st.error("没抓到可用的公开页面。可以换个公司全称再试，或者跳过这项直接投。")
        return
    st.markdown(out["report"])
    with st.expander("看抓到的原始来源（可自己核对）"):
        for url, text in out["sources"]:
            st.markdown(f"**{url}**")
            st.text(text[:1200])


def resume_source_panel(prefix: str) -> str:
    """简历来源统一面板（导入文件 / 问答生成 / 手动编辑）。返回当前简历全文。

    prefix 用来隔离不同页面的控件 key，避免重复元素 ID。
    """
    key = f"{prefix}_text"
    if key not in st.session_state:
        st.session_state[key] = load_my_resume()

    src = st.radio("简历从哪来",
                   ["📎 导入文件（PDF / Word / 图片 / 文本）",
                    "💬 问答式生成一份", "✍️ 手动编辑"],
                   horizontal=True, key=f"{prefix}_src")

    if "导入" in src:
        st.caption("支持 PDF、Word(.docx)、txt/md，以及简历截图（离线 OCR 识别，约 5-15 秒）。")
        up = st.file_uploader("选择简历文件",
                              type=["pdf", "docx", "txt", "md", "png", "jpg",
                                    "jpeg", "webp", "bmp"],
                              key=f"{prefix}_up")
        if up is not None and st.button("读取这个文件", key=f"{prefix}_read"):
            with st.spinner("读取中…"):
                try:
                    out = doc_io.read_any(up.getvalue(), up.name)
                except Exception as e:
                    out = {"text": "", "method": "失败", "warning": str(e)}
            if out["text"]:
                st.session_state[key] = out["text"]
                st.success(f"读取成功：{out['method']}，{len(out['text'])} 字")
            if out.get("warning"):
                st.warning(out["warning"])
            if not out["text"]:
                st.error("没读到文字。可以改用截图上传，或手动粘贴。")
            st.rerun()
    elif "问答" in src:
        rb = resume_builder.load()
        done, total = resume_builder.progress(rb)
        st.progress(done / total,
                    text=(f"第 {done + 1} / {total} 题" if done < total else "全部答完"))
        q = resume_builder.current(rb)
        if q:
            st.markdown(f"**{q['q']}**")
            st.caption("为什么问这个 / 怎么答有用：" + q["why"])
            if q["k"] == "photo":
                # 照片这一题直接给上传按钮，比让人打字有用
                up_photo = st.file_uploader("上传照片（jpg / png / webp）",
                                            type=["jpg", "jpeg", "png", "webp"],
                                            key=f"{prefix}_rb_photo")
                if up_photo is not None:
                    st.image(up_photo.getvalue(), width=140, caption="预览")
                    if st.button("✅ 用这张照片", type="primary",
                                 key=f"{prefix}_rb_photo_save"):
                        dst = resume_builder.save_photo(up_photo.getvalue())
                        resume_builder.answer(rb, f"已上传：{dst.name}")
                        st.rerun()
                c1, c2 = st.columns(2)
                if c1.button("没有照片，跳过这题", key=f"{prefix}_rb_skip"):
                    resume_builder.answer(rb, "无")
                    st.rerun()
                if c2.button("重新开始", key=f"{prefix}_rb_reset"):
                    resume_builder.reset()
                    st.rerun()
            else:
                val = st.text_area("你的回答", rb["answers"].get(q["k"], ""),
                                   key=f"{prefix}_rb_{q['k']}", height=100)
                c1, c2, c3 = st.columns(3)
                if c1.button("提交，下一题", type="primary", key=f"{prefix}_rb_next"):
                    resume_builder.answer(rb, val)
                    st.rerun()
                if c2.button("跳过这题", key=f"{prefix}_rb_skip"):
                    resume_builder.answer(rb, "")
                    st.rerun()
                if c3.button("重新开始", key=f"{prefix}_rb_reset"):
                    resume_builder.reset()
                    st.rerun()
        else:
            st.caption("答完了。生成草稿后，空着的字段会明确列出来，不会替你编。")
            if st.button("📝 生成简历草稿（调用 DeepSeek）", type="primary",
                         key=f"{prefix}_rb_build"):
                with st.spinner("整理中…"):
                    try:
                        draft = resume_builder.build(rb, lambda p: ask_chat(p))
                        (DATA_DIR / "resume_draft.md").write_text(draft, encoding="utf-8")
                        st.session_state[key] = draft
                        st.session_state[f"{prefix}_draft"] = draft
                    except Exception as e:
                        st.error(str(e))
            if st.session_state.get(f"{prefix}_draft"):
                with st.expander("看生成的草稿", expanded=True):
                    st.markdown(st.session_state[f"{prefix}_draft"])

    return st.text_area("简历全文（可编辑）", height=280, key=key)


def page_my_resume():
    """我的简历：管理简历内容本身（不针对具体岗位）。"""
    hero("我的简历", "导入 / 问答生成 / 手动编辑。保存后用于 ATS 覆盖检查和面试准备")
    saved = MY_RESUME_PATH.exists()
    if saved:
        st.success(f"已保存到 {MY_RESUME_PATH.name}（{len(read_text(MY_RESUME_PATH))} 字）")
    else:
        st.info("还没保存过。下面是仓库里已有的简历，改完点保存就会变成「我的简历」。")
    text = resume_source_panel("my")
    c1, c2 = st.columns([1, 3])
    if c1.button("💾 保存为我的简历", type="primary", key="my_save"):
        cleaned, rep = save_my_resume(text)
        st.success(f"已保存（{len(cleaned)} 字）")
        if rep:
            st.warning("顺手清掉了这些不该出现在简历里的东西："
                       + "、".join(f"{name}×{n}" for name, n, _ in rep))
            with st.expander("看被删掉的原文片段"):
                for name, n, sample in rep:
                    st.caption(f"{name} ×{n}　例：{sample}")
        else:
            st.caption("文本检查通过：没有本地路径 / 编码乱码。")
        next_step("resume_saved")
    c2.caption("保存位置：简历/我的简历.md　·　投递里的「简历定制」默认读这份")

    st.markdown("---")
    st.markdown("#### 📷 简历照片")
    st.caption("照片会出现在：打印版简历的右上角、以及公开名片页的头像。"
               "传一次就够，后面所有模板共用这一张。")
    ph1, ph2 = st.columns([1, 3], vertical_alignment="center")
    _ph = find_avatar()
    with ph1:
        if _ph:
            st.image(str(_ph), width=130, caption=f"当前：{_ph.name}")
        else:
            st.markdown(
                '<div style="width:130px;height:130px;border-radius:50%;'
                'background:linear-gradient(135deg,#5558D6,#1B2A4A);color:#fff;'
                'display:flex;align-items:center;justify-content:center;'
                'font-size:44px;font-weight:700;">余</div>',
                unsafe_allow_html=True)
            st.caption("还没有照片")
    with ph2:
        up_img = st.file_uploader("上传照片（jpg / png / webp，竖版证件照最好）",
                                  type=["jpg", "jpeg", "png", "webp"], key="photo_up")
        if up_img is not None:
            st.image(up_img.getvalue(), width=120, caption="预览")
            if st.button("✅ 用这张照片", type="primary", key="photo_save"):
                dst = resume_builder.save_photo(up_img.getvalue())
                st.success(f"已保存到 {dst.name}")
                st.rerun()
        st.caption("保存位置：简历/照片.jpg　·　想让云端名片也有头像，"
                   "把这张图提交到 GitHub（`git add 简历/照片.jpg && git commit && git push`）")

    st.markdown("---")
    st.markdown("#### 🎨 简历模板")
    st.caption("同一份内容，三种排版。选一个，先在浏览器里打开看一眼，"
               "满意了再用本地脚本出 PDF（照片会自动嵌进去）。")
    tpl_labels = list(resume_templates.TEMPLATES.values())
    tpl_keys = list(resume_templates.TEMPLATES.keys())
    _pv_photo = resume_templates.photo_data_uri()
    st.caption("下面就是三套模板长什么样（缩略图，跟打印稿同一套排版）。"
               "没照片时照片位是空的——所以想看清差别，先在上面传一张。")
    _pv_cols = st.columns(3)
    _tpl_note = {
        "classic": "结果前置的单栏，从上往下扫最顺。默认选这个。",
        "sidebar": "左边一栏放照片 + 联系方式 + 技能，右边只放经历。照片最显眼。",
        "compact": "极简黑白、宋体、细线，不要颜色。投偏传统 / 国企类团队更稳。",
    }
    _equal_h = st.toggle("三列统一高度（裁成一样高对比，底部渐隐；关掉=完整显示）",
                         value=False,
                         help="长模板（classic/compact）本来就比 sidebar 高，"
                              "统一高度只是为了并排对比好看，不代表被裁坏了。")
    for _col, _k in zip(_pv_cols, tpl_keys):
        with _col:
            st.markdown(f"**{_k}**")
            st.caption(_tpl_note[_k])
            st.html(resume_templates.preview_html(_k, photo_uri=_pv_photo,
                                                  zoom=0.42,
                                                  clip_height=470 if _equal_h else 0,
                                                  instance="grid"))
    tpl_pick = st.segmented_control("选一个作为你的模板", tpl_labels,
                                    default=tpl_labels[0], key="tpl_pick")
    tpl_key = tpl_keys[tpl_labels.index(tpl_pick or tpl_labels[0])]
    with st.expander(f"放大看「{tpl_key}」整页（跟我打印出来的一致）", expanded=False):
        st.html(resume_templates.preview_html(tpl_key, photo_uri=_pv_photo,
                                              zoom=0.78, instance="zoom"))
    _html = resume_templates.render_with_photo(tpl_key)
    t1, t2, t3 = st.columns([1, 1, 2])
    t1.download_button("⬇️ 下载这份 HTML", data=_html.encode("utf-8"),
                       file_name=f"余剑-简历-{tpl_key}.html", mime="text/html",
                       key="tpl_dl")
    t2.caption("下载后双击打开 → Ctrl+P → 另存为 PDF，就是当前模板的样子。")
    t3.caption("要高保真 PDF（照片自动嵌入、实测 1 页）就在终端跑："
               f"`python offeragent\\make_resume_pdf.py --template {tpl_key}`")


def page_resume_tailor(embedded: bool = False):
    """按 JD 定制简历 + ATS 关键词覆盖检查。"""
    if not embedded:
        hero("简历定制", "按目标岗位检查关键词覆盖，并给重排与改写建议（只重排已有经历，不编）")
    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    if not jobs:
        st.info("先到「找工作 → 岗位库」添加岗位")
        return
    name = st.selectbox("目标岗位", [j[0] for j in jobs], key="tailor_pick")
    jd = read_text(JDS_DIR / f"{name}.txt")
    st.caption("这一步只做检查、不改内容。简历正文和模板在左边「简历内容 / 模板 / 照片」里管理。")
    resume = resume_source_panel("tailor")

    if st.button("🔬 检查覆盖 + 给建议（调用 DeepSeek）", type="primary", key="tailor_run"):
        if not resume.strip():
            st.warning("简历内容为空")
            return
        resume, _rep = resume_clean.clean(resume)
        if _rep:
            st.caption("已自动清掉 " + "、".join(f"{n}×{c}" for n, c, _ in _rep)
                       + "（本地路径/编码乱码，不属于简历内容）")
        with st.spinner("抽取 JD 关键词 + 本地比对 + 生成建议…"):
            try:
                out = resume_tailor.tailor(resume, jd, lambda p: ask_chat(p))
                st.session_state["tailor_out"] = out
                next_step("ats_done")
            except Exception as e:
                st.error(str(e))

    out = st.session_state.get("tailor_out")
    if not out:
        return
    st.metric("关键词覆盖率", f"{out['rate']}%",
              help="已覆盖算 1 分、部分覆盖算 0.5 分。这是本地字符串比对的结果，不是模型判断。")
    miss = [r for r in out["coverage"] if r["status"] == "缺失"]
    part = [r for r in out["coverage"] if r["status"] == "部分覆盖"]
    c1, c2 = st.columns(2)
    c1.metric("缺失关键词", len(miss))
    c2.metric("部分覆盖", len(part))
    with st.expander("看完整覆盖表（关键词 / 状态 / 类别）", expanded=True):
        for r in out["coverage"]:
            tag = {"已覆盖": "oa-tag-green", "部分覆盖": "oa-tag-amber",
                   "缺失": "oa-tag-red"}.get(r["status"], "oa-tag-blue")
            st.markdown(f'<span class="oa-tag {tag}">{r["status"]}</span> '
                        f'**{r["keyword"]}**　<span style="color:#94A3B8">{r["category"]}</span>',
                        unsafe_allow_html=True)
    if miss:
        st.warning("缺失的关键词：" + "、".join(r["keyword"] for r in miss)
                   + "　→ 简历里没有的不要硬写，先确认你是不是真的做过")
    for key, title in [("reorder.md", "重排建议"), ("bullets.md", "改写建议")]:
        if out["advice"].get(key):
            st.markdown(f"### {title}")
            st.markdown(out["advice"][key])


def page_drill():
    """面试拷问：AI 当面试官，逐题点评。"""
    hero("面试拷问", "AI 当面试官追问你；每答一题给三段反馈。可中断续答")
    jobs = [j for j in list_jobs() if j[1]["status"] != "排除"]
    if not jobs:
        st.info("先到「🎯 找工作 → 岗位库」添加岗位")
        return
    name = st.selectbox("针对哪个岗位练", [j[0] for j in jobs], key="drill_pick")
    jd = read_text(JDS_DIR / f"{name}.txt")
    profile = read_text(PROFILE_PATH) or read_text(ME_PATH)
    state = interview_drill.load_state(name)

    c1, c2 = st.columns([1, 1])
    if c1.button("🎤 生成 10 个追问（调用 DeepSeek）", type="primary"):
        with st.spinner("面试官在想问题…"):
            try:
                text, qs = interview_drill.make_questions(profile, jd,
                                                          lambda p: ask_chat(p))
                state["questions"] = text
                state["items"] = [{"q": q, "a": "", "f": ""} for q in qs]
                interview_drill.save_state(state)
                st.rerun()
            except Exception as e:
                st.error(str(e))
    if c2.button("↺ 重来（清空这个岗位的记录）"):
        state = {"job": name, "questions": "", "items": []}
        interview_drill.save_state(state)
        st.rerun()

    items = state.get("items") or []
    if not items:
        st.caption("点上面的按钮开始。生成的题目会存在本地，明天回来接着答。")
        return

    answered = sum(1 for it in items if it.get("a", "").strip())
    st.progress(answered / len(items), text=f"已答 {answered} / {len(items)} 题")
    for i, it in enumerate(items):
        with st.expander(f"{i + 1}. {it['q'][:60]}", expanded=(i == answered)):
            ans = st.text_area("你的回答", it.get("a", ""), key=f"ans_{name}_{i}", height=110)
            if st.button(f"提交第 {i + 1} 题并要反馈", key=f"fb_{name}_{i}"):
                if not ans.strip():
                    st.warning("先写点内容")
                else:
                    with st.spinner("面试官在点评…"):
                        try:
                            it["a"] = ans.strip()
                            it["f"] = interview_drill.feedback(it["q"], it["a"],
                                                               lambda p: ask_chat(p))
                            interview_drill.save_state(state)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
            if it.get("f"):
                st.markdown(it["f"])

    if answered == len(items):
        if st.button("📋 生成总评（最危险的三个问题 + 该补的一件事）", type="primary"):
            with st.spinner("汇总中…"):
                try:
                    st.session_state[f"drill_review_{name}"] = interview_drill.total_review(
                        items, lambda p: ask_chat(p))
                except Exception as e:
                    st.error(str(e))
        if st.session_state.get(f"drill_review_{name}"):
            st.markdown(st.session_state[f"drill_review_{name}"])
        st.markdown("---")
        st.caption("把这轮拷问存进复盘库，数字分身就能拿它调整以后的回答（存本地，不上传）。")
        if st.button("💾 存进复盘库（数字分身据此进化）", key=f"drill_save_{name}"):
            lines = []
            for i, it in enumerate(items, 1):
                lines.append(f"Q{i}. {it['q']}")
                if it.get("a"):
                    lines.append(f"我的回答：{it['a']}")
            if st.session_state.get(f"drill_review_{name}"):
                lines.append("\n【模拟面试总评】\n"
                             + st.session_state[f"drill_review_{name}"])
            body = "\n".join(lines) + "\n\n（来源：面试拷问模式·模拟练习）"
            meta_board = dict((j[0], j[1]) for j in jobs)
            digital_twin.save_review(name, meta_board.get(name, {}).get("company", ""), body)
            st.success(f"已存进复盘库：{name}")
        st.caption("去「🧬 我的 → 复盘入库」能看到它，"
                   "点「提炼画像更新」会给你画像修改建议。")


def page_applications():
    """投递记录：每一条投了什么、用了什么话术、该跟进谁。

    统计口径统一收敛到「今天 → 数据与日志」那一页，这里只记录事实，避免同一个数字
    在三个页面各算一遍。
    """
    hero("投递记录", "每一条投了什么、用了什么话术、该跟进谁")
    rows = apply_assist.load_applications()
    all_jobs = list_jobs()
    applied_jobs = [j for j in all_jobs
                    if j[1]["status"] in ("已投", "面试中", "已拒", "Offer")]
    st.caption(f"共 {len(rows)} 条记录。漏斗和趋势在「🚀 今天 → 数据与日志」里看。")

    # 跟进提醒
    follow = pipeline.needs_followup(all_jobs, days=7)
    if follow:
        st.markdown("### ⏰ 该跟进了（投出去超过 7 天没更新状态）")
        for f in follow[:8]:
            st.markdown(f"- **{f['meta'].get('company') or f['name']}** · {f['name']}"
                        f" · 已投 {f['days']} 天")
        st.caption("跟进话术去「投递台 → 单条精修」用「内推消息」或「BOSS 打招呼」模板改写。")
    else:
        st.caption("暂时没有需要跟进的岗位（投出去满 7 天会自动出现在这里）。")

    # 邮件 / 消息 → 状态识别（粘贴式，不接邮箱）
    with st.expander("📨 收到邮件或消息？粘贴进来，帮你判断该怎么改状态"):
        st.caption("不接邮箱、不要授权。你把内容粘进来，程序判断类型并给改状态的建议。"
                   "内容不会上传保存，除非你自己点保存。")
        mail = st.text_area("粘贴邮件或聊天内容", key="inbox_text", height=160,
                            placeholder="例：您好，我们想邀请您参加线上技术面试，时间定在……")
        if st.button("🔎 判断这是什么消息", key="inbox_go"):
            if not mail.strip():
                st.warning("先粘贴内容")
            else:
                with st.spinner("判断中…"):
                    try:
                        info = inbox_parse.classify(mail, lambda p: ask_chat(p))
                        st.session_state["inbox_out"] = info
                    except Exception as e:
                        st.error(str(e))
        info = st.session_state.get("inbox_out")
        if info:
            st.success(f"类型：**{info['type']}**"
                       f"{'　公司：' + info['company'] if info['company'] else ''}"
                       f"{'　岗位：' + info['job'] if info['job'] else ''}"
                       f"{'　时间：' + info['time'] if info['time'] else ''}")
            st.info("建议：" + info["hint"])
            st.caption("改状态请去「岗位」→ 岗位库，或「今日」里点对应岗位的按钮。"
                       "程序不会自动改，避免误判。")

    # 被拒归因
    rejected = [r for r in rows if r.get("status") == "已拒"]
    rejected_names = [n for n, m, _ in all_jobs if m.get("status") == "已拒"]
    if rejected_names:
        st.markdown("### 🔍 被拒归因")
        st.caption(f"库里标记为「已拒」的岗位有 {len(rejected_names)} 个。"
                   "连续被拒 3 个以上时，归因才有参考价值。")
        if len(rejected_names) >= 3:
            if st.button("分析这些被拒岗位的共同点（调用 DeepSeek）"):
                with st.spinner("分析中…"):
                    try:
                        recs = [{"job": n, "company": m.get("company"),
                                 "score": m.get("match_score"), "note": ""}
                                for n, m, _ in all_jobs if m.get("status") == "已拒"]
                        st.session_state["reject_analysis"] = pipeline.analyze_rejections(
                            recs, lambda p: ask_chat(p))
                    except Exception as e:
                        st.error(str(e))
            if st.session_state.get("reject_analysis"):
                st.markdown(st.session_state["reject_analysis"])
        else:
            st.info(f"现在只有 {len(rejected_names)} 个「已拒」，再多几个再跑归因。")

    if not rows and not applied_jobs:
        st.info("还没有投递记录。去「🚀 今日」投第一家，投完点「标记已投」就会记在这里。")
        return

    if rows:
        st.markdown("### 投递流水")
        for r in rows[:30]:
            with st.expander(f"**{r.get('company') or r['job']}** · {r['job']} · "
                             f"{r.get('time', '')[:16]}"
                             f"{' · 匹配度 ' + str(r['score']) if r.get('score') else ''}"):
                if r.get("url"):
                    st.caption("岗位链接：" + r["url"])
                if r.get("talk"):
                    st.markdown("**当时发的话术**")
                    st.code(r["talk"], language="text")
                else:
                    st.caption("没存话术（当时可能没用工具生成）")
                if r.get("note"):
                    st.caption("备注：" + r["note"])

    if applied_jobs:
        st.markdown("### 岗位库里的投递状态")
        for name, meta, _ in applied_jobs:
            st.markdown(
                f"- {status_tag(meta.get('status', '已投'))} **{meta.get('company') or name}**"
                f" · {name}"
                f"{' · 匹配度 ' + str(meta.get('match_score')) if meta.get('match_score') else ''}"
                f"{' · ' + meta.get('applied_at', '')[:16] if meta.get('applied_at') else ''}",
                unsafe_allow_html=True)


# ============================================================
# 导航：用 Streamlit 原生多页（st.navigation）
# 为什么换掉自定义导航：
#   1. 原生导航有真实 URL（/resume、/apply…）→ 可刷新、可前进后退、可分享
#   2. 侧边栏是真·两级树（分区标题 + 页），不再是"横排按钮组"那种说不清层级的东西
#   3. 跨页跳转用 st.switch_page，不用再靠 session_state 里塞"待跳转标记"
# 规则不变：一个动作只有一个入口；同一个数字只有一个出处。
# ============================================================
