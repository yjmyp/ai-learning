# -*- coding: utf-8 -*-
"""简历页域：简历内容管理 / 模板选择 / 照片 / ATS 定制 —— 从 pages_more.py 拆出。

拆出来的原因（也是分层思路）：
- pages_more.py 原来 36KB 装 8 个页面，简历相关（内容/模板/照片/定制）自成一块。
- 简历页只依赖「内容层(resume_templates) + 工具层(store/llm/ui_kit/doc_io/resume_builder…)」，
  和拷问/投递记录等其他页面没有互相调用 —— 拆开互不影响。
"""
import streamlit as st

from store import *
from llm import *
from ui_kit import *
from pages_twin import find_avatar
import doc_io
import resume_builder
import resume_clean
import resume_tailor
import resume_templates


def _render_pdf_bytes(tpl: str) -> bytes | None:
    """本地无头 Edge 渲染 PDF；云端等无 Edge 环境返回 None（按钮降级为提示）。"""
    try:
        import make_resume_pdf as mk
        tmp = mk.RESUME_DIR / "_dl_tmp.pdf"
        mk.html_to_pdf(resume_templates.render_with_photo(tpl), tmp)
        data = tmp.read_bytes()
        tmp.unlink(missing_ok=True)
        return data
    except Exception:
        return None


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
    st.caption("同一份内容，**七套不同布局的整体模板**（不是小改版，是结构不同的七种简历）。"
               "下面是模板卡片墙：每张卡片 = 一套模板的**版式缩略**，点「选用」切换；"
               "下载按钮对应**选中的那套**（照片自动嵌入）。")
    tpl_labels = list(resume_templates.TEMPLATES.values())
    tpl_keys = list(resume_templates.TEMPLATES.keys())
    _pv_photo = resume_templates.photo_data_uri()
    st.caption(f"模板引擎版本 `{resume_templates.build_tag()}`"
               "（这个指纹和云端不一致 = 云端还在跑旧代码，去 Manage app → Reboot）")

    # 记忆上次选的模板（刷新不丢）
    tpl_key = st.session_state.get("tpl_pick_key", "classic")
    if tpl_key not in tpl_keys:
        tpl_key = "classic"

    # ---- 模板卡片墙：4 列排开，卡片 = 版式缩略 + 描述 + 选用按钮 ----
    st.markdown("###### 选一套模板（点卡片下的「选用」）")
    # 卡片标题用中文短名：之前只显示 "选用「classic」" 这种英文 key，
    # 用户得靠猜哪套是哪套（缩略图里的小字看不见）。
    def _short_name(k):
        return resume_templates.TEMPLATES.get(k, k).split("（")[0].strip()

    for row in range(0, len(tpl_keys), 4):
        cols = st.columns(4)
        for _k, col in zip(tpl_keys[row:row + 4], cols):
            with col:
                st.markdown(f"**{_short_name(_k)}**")
                st.html(resume_templates.preview_html(
                    _k, photo_uri=_pv_photo, zoom=0.20, instance=f"card_{_k}"))
                _active = (_k == tpl_key)
                if st.button(
                        f"选用「{_short_name(_k)}」",
                        key=f"tpl_card_{_k}",
                        type="primary" if _active else "secondary",
                        use_container_width=True):
                    st.session_state["tpl_pick_key"] = _k
                    st.rerun()
                st.caption(resume_templates.TEMPLATE_DESC.get(_k, ""))

    # ---- 选中的那套：放大看整页 ----
    st.markdown("---")
    st.markdown(f"###### 放大看「**{_short_name(tpl_key)}**」整页（跟我打印出来的一致）")
    st.html(resume_templates.preview_html(tpl_key, photo_uri=_pv_photo,
                                          zoom=0.78, instance="zoom"))

    # ---- 每套完整预览（不裁切，能完整看排版）----
    with st.expander("每套模板的完整预览（跟打印稿同一套排版，完整显示不裁切）"):
        for _k in tpl_keys:
            st.markdown(f"**{_k}**　—　{resume_templates.TEMPLATE_DESC.get(_k, '')}")
            st.html(resume_templates.preview_html(_k, photo_uri=_pv_photo,
                                                  zoom=0.42, instance=f"full_{_k}"))

    st.markdown("---")
    _html = resume_templates.render_with_photo(tpl_key)
    _md = resume_templates.to_markdown()
    _pdf_bytes = _render_pdf_bytes(tpl_key)
    t1, t2, t3 = st.columns([1, 1, 1])
    t1.download_button("⬇️ 下载 HTML", data=_html.encode("utf-8"),
                       file_name=f"余剑-简历-{tpl_key}.html", mime="text/html",
                       key="tpl_dl_html")
    if _pdf_bytes:
        t2.download_button("⬇️ 下载 PDF（含照片）", data=_pdf_bytes,
                           file_name=f"余剑-简历-{tpl_key}.pdf",
                           mime="application/pdf", key="tpl_dl_pdf")
    else:
        t2.caption("PDF 需本地生成（云端无 Edge）\n"
                   f"终端跑：`python offeragent\\make_resume_pdf.py "
                   f"--template {tpl_key}`")
    t3.download_button("⬇️ 下载 Markdown（可编辑）", data=_md.encode("utf-8"),
                       file_name="余剑-简历.md", mime="text/markdown",
                       key="tpl_dl_md")
    st.caption("HTML = 双击 → Ctrl+P 也能存 PDF；PDF = 高保真、照片已嵌入、实测 1 页；"
               "Markdown = 纯文本，可贴进 BOSS/邮件正文或继续改。")


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
