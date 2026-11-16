# -*- coding: utf-8 -*-
"""
pages_jobs_pro.py · 产品级岗位库页面
====================================
页面结构：
- 顶部搜索栏（关键词 + 城市 + 搜索按钮）
- 筛选条（来源/薪资/状态/排序）
- 岗位列表（卡片式，左中右三段信息）
- 右侧详情面板（点击岗位展开）
"""
import streamlit as st
import json

from theme_pro import (
    section_title, tag, list_item, stat_card, progress
)
from store import list_jobs, read_text, save_meta, MATCH_DIR, ensure_dirs
import job_sources
import job_quality
import job_detail


def page_jobs_pro():
    """产品级岗位库页面。"""
    ensure_dirs()
    all_jobs = list_jobs()

    # ---- 页面标题 ----
    col_title, col_add = st.columns([3, 1])
    with col_title:
        st.markdown("""
        <div style="margin-bottom:20px">
            <h2 style="margin:0 0 4px 0;font-size:22px;font-weight:700;color:var(--ink)">岗位库</h2>
            <p style="margin:0;font-size:13.5px;color:var(--muted)">管理所有岗位，搜索、筛选、批量操作</p>
        </div>
        """, unsafe_allow_html=True)
    with col_add:
        st.markdown("<div style='text-align:right;margin-bottom:20px'>", unsafe_allow_html=True)
        if st.button("➕ 手动添加岗位", key="pro_add_job"):
            st.info("添加岗位表单（开发中）")
        st.markdown("</div>", unsafe_allow_html=True)

    # ---- 数据概览小卡 ----
    c1, c2, c3, c4 = st.columns(4)
    total = len(all_jobs)
    pending = sum(1 for _, m, _ in all_jobs if m.get("status") == "待投")
    matched = sum(1 for _, m, _ in all_jobs if m.get("match_score"))
    applied = sum(1 for _, m, _ in all_jobs if m.get("status") == "已投")
    with c1:
        st.markdown(stat_card("岗位总数", total, f"{len(all_jobs)} 个在库", True), unsafe_allow_html=True)
    with c2:
        st.markdown(stat_card("待投", pending, f"匹配后可投", True), unsafe_allow_html=True)
    with c3:
        st.markdown(stat_card("已匹配", matched, f"AI 打分完成", None), unsafe_allow_html=True)
    with c4:
        st.markdown(stat_card("已投递", applied, f"真实发出", applied > 0), unsafe_allow_html=True)

    # ---- 搜索栏 ----
    st.markdown("""
    <div class="oa-pro-card" style="margin:20px 0;padding:16px 20px">
        <div style="display:flex;gap:12px;align-items:center">
            <div style="flex:1">
                <div style="font-size:12px;color:var(--muted);margin-bottom:4px">搜索岗位</div>
                <div style="font-size:13px;color:var(--muted-2)">输入关键词，如 AI、Agent、RAG、大模型</div>
            </div>
            <div style="width:140px">
                <div style="font-size:12px;color:var(--muted);margin-bottom:4px">城市</div>
                <div style="font-size:13px;color:var(--muted-2)">南京 / 远程</div>
            </div>
            <div style="width:140px">
                <div style="font-size:12px;color:var(--muted);margin-bottom:4px">来源</div>
                <div style="font-size:13px;color:var(--muted-2)">全部平台</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 搜索表单（用原生组件放在卡片后面）
    col_kw, col_city, col_src, col_btn = st.columns([3, 1.5, 1.5, 1])
    with col_kw:
        search_kw = st.text_input("关键词", placeholder="输入岗位名称或关键词，如 AI应用开发", 
                                  label_visibility="collapsed", key="pro_search_kw")
    with col_city:
        city = st.selectbox("城市", ["全部城市", "南京", "上海", "北京", "深圳", "杭州", "远程"], 
                            label_visibility="collapsed", key="pro_search_city")
    with col_src:
        source = st.selectbox("来源", ["全部来源", "牛客", "实习僧", "BOSS直聘", "手动添加"], 
                              label_visibility="collapsed", key="pro_search_src")
    with col_btn:
        st.markdown("<div style='margin-top:2px'>", unsafe_allow_html=True)
        do_search = st.button("🔍 搜索岗位", type="primary", use_container_width=True, key="pro_search_btn")
        st.markdown("</div>", unsafe_allow_html=True)

    # ---- 筛选与排序 ----
    col_filter, col_sort = st.columns([3, 1])
    with col_filter:
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            status_filter = st.selectbox("状态", ["全部", "待投", "已投", "面试中", "已拒", "排除"], 
                                         label_visibility="collapsed", key="pro_filter_status")
        with f2:
            score_filter = st.selectbox("匹配度", ["全部", "75分以上", "60分以上", "未打分"], 
                                        label_visibility="collapsed", key="pro_filter_score")
        with f3:
            salary_filter = st.selectbox("薪资", ["全部薪资", "5k以下", "5-8k", "8-12k", "12k以上"], 
                                         label_visibility="collapsed", key="pro_filter_salary")
        with f4:
            quality_filter = st.selectbox("质量", ["全部", "优质岗", "普通", "可疑"], 
                                          label_visibility="collapsed", key="pro_filter_quality")
    with col_sort:
        sort_by = st.selectbox("排序", ["匹配度 ↓", "最新添加", "薪资 ↓", "公司名称"], 
                               label_visibility="collapsed", key="pro_sort")

    st.divider()

    # ---- 筛选逻辑 ----
    filtered = []
    for name, meta, jd in all_jobs:
        # 状态筛选
        status = meta.get("status", "待投")
        if status_filter != "全部" and status != status_filter:
            continue
        # 匹配度筛选
        score = meta.get("match_score")
        if score_filter == "75分以上" and (not score or score < 75):
            continue
        if score_filter == "60分以上" and (not score or score < 60):
            continue
        if score_filter == "未打分" and score:
            continue
        # 关键词筛选
        if search_kw and search_kw.lower() not in name.lower() and search_kw.lower() not in (meta.get("company") or "").lower():
            if search_kw.lower() not in (jd or "").lower():
                continue
        # 城市筛选
        if city != "全部城市" and (meta.get("city") or "") not in city:
            continue
        # 来源筛选
        if source != "全部来源" and (meta.get("source") or "") != source:
            continue
        filtered.append((name, meta, jd))

    # 排序
    if sort_by == "匹配度 ↓":
        filtered.sort(key=lambda x: x[1].get("match_score", 0) or 0, reverse=True)
    elif sort_by == "最新添加":
        filtered.sort(key=lambda x: x[1].get("added_at", ""), reverse=True)
    elif sort_by == "薪资 ↓":
        def _parse_sal(s):
            if not s: return 0
            import re
            nums = re.findall(r'\d+', s)
            return int(nums[0]) if nums else 0
        filtered.sort(key=lambda x: _parse_sal(x[1].get("salary", "")), reverse=True)

    # ---- 岗位列表 ----
    section_title(f"岗位列表（{len(filtered)} 个）", "批量操作")

    if not filtered:
        st.markdown("""
        <div class="oa-pro-card" style="text-align:center;padding:48px 20px">
            <div style="font-size:48px;margin-bottom:12px">📭</div>
            <div style="font-weight:600;color:var(--ink);margin-bottom:4px;font-size:15px">没有找到岗位</div>
            <div style="font-size:12.5px;color:var(--muted);margin-bottom:16px">调整筛选条件，或点击上方搜索新岗位</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # 岗位卡片列表
    for name, meta, jd in filtered[:20]:  # 先显示前 20 个
        score = meta.get("match_score")
        company = meta.get("company", "未知公司")
        city = meta.get("city", "")
        salary = meta.get("salary", "")
        source = meta.get("source", "手动")
        status = meta.get("status", "待投")

        # 状态标签颜色
        status_color = {
            "待投": "brand",
            "已投": "green",
            "面试中": "green",
            "已拒": "red",
            "排除": "gray",
        }.get(status, "gray")

        # 匹配度标签
        if score:
            if score >= 75:
                score_color = "green"
            elif score >= 60:
                score_color = "brand"
            elif score >= 45:
                score_color = "amber"
            else:
                score_color = "red"
            score_tag = tag(f"{score}% 匹配", score_color)
        else:
            score_tag = tag("未打分", "gray")

        # 岗位质量
        quality = meta.get("quality", {})
        quality_score = quality.get("score") if isinstance(quality, dict) else None

        # 薪资标签
        salary_tag = tag(salary, "gray") if salary else ""

        card_html = f"""
        <div class="oa-pro-card" style="margin-bottom:10px;padding:16px 20px;cursor:pointer">
            <div style="display:flex;gap:16px;align-items:start">
                <!-- 左侧：公司图标 + 基本信息 -->
                <div style="width:44px;height:44px;border-radius:10px;background:linear-gradient(135deg,#EEF2FF,#E0E7FF);display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0">
                    💼
                </div>
                
                <!-- 中间：标题 + 信息 -->
                <div style="flex:1;min-width:0">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                        <span style="font-weight:600;font-size:14.5px;color:var(--ink)">{name}</span>
                        {score_tag}
                        {tag(status, status_color)}
                    </div>
                    <div style="font-size:13px;color:var(--muted);margin-bottom:8px">
                        {company}
                        {' · ' + city if city else ''}
                        {' · ' + source if source else ''}
                    </div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap">
                        {salary_tag}
                        {tag(quality_score + '分质量', 'green') if quality_score else ''}
                        {tag('有 JD', 'brand') if jd else tag('无 JD', 'gray')}
                    </div>
                </div>
                
                <!-- 右侧：操作按钮 -->
                <div style="display:flex;flex-direction:column;gap:6px;align-items:flex-end">
                    <div style="font-size:12px;color:var(--muted)"></div>
                </div>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

    if len(filtered) > 20:
        st.markdown(f"""
        <div style="text-align:center;padding:12px;color:var(--muted);font-size:13px">
            还有 {len(filtered) - 20} 个岗位，继续滚动加载 →
        </div>
        """, unsafe_allow_html=True)
