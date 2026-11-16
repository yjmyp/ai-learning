# -*- coding: utf-8 -*-
"""
theme_pro.py · 产品级组件库（设计令牌 + 卡片/列表/统计组件）
=================================================
样式（CSS）统一在 theme.py 的 CSS_P（唯一设计语言），本模块只负责组件 HTML。
设计方向：Stripe + Linear 结合
- 主色：靛蓝（Indigo）→ 紫蓝渐变，克制不艳
- 背景：极浅的灰蓝渐变，不是纯白也不是死灰
- 卡片：大圆角 16px + 极轻阴影 + 1px 半透明边框
- 间距：大留白，信息层级靠间距不靠分割线
- 字体：字重对比强烈，标题用 700-800，正文 400，辅助文字 12px
- 动效：所有交互 200ms cubic-bezier(.4,0,.2,1)
"""

import streamlit as st


# ============================================================
# 设计令牌（Design Tokens）
# ============================================================
TOKENS = {
    # 主色 - 靛蓝系
    "primary-50":  "#EEF2FF",
    "primary-100": "#E0E7FF",
    "primary-200": "#C7D2FE",
    "primary-300": "#A5B4FC",
    "primary-400": "#818CF8",
    "primary-500": "#6366F1",
    "primary-600": "#4F46E5",
    "primary-700": "#4338CA",
    
    # 强调色 - 青绿色（用于成功/增长）
    "accent-500":  "#06B6D4",
    "success-500": "#10B981",
    "warning-500": "#F59E0B",
    "danger-500":  "#EF4444",
    
    # 中性色 - Slate 系
    "slate-50":   "#F8FAFC",
    "slate-100":  "#F1F5F9",
    "slate-200":  "#E2E8F0",
    "slate-300":  "#CBD5E1",
    "slate-400":  "#94A3B8",
    "slate-500":  "#64748B",
    "slate-600":  "#475569",
    "slate-700":  "#334155",
    "slate-800":  "#1E293B",
    "slate-900":  "#0F172A",
    
    # 圆角
    "radius-sm":  "8px",
    "radius-md":  "12px",
    "radius-lg":  "16px",
    "radius-xl":  "20px",
    
    # 阴影
    "shadow-sm":  "0 1px 2px 0 rgba(15, 23, 42, 0.04)",
    "shadow-md":  "0 4px 6px -1px rgba(15, 23, 42, 0.06), 0 2px 4px -2px rgba(15, 23, 42, 0.04)",
    "shadow-lg":  "0 10px 15px -3px rgba(15, 23, 42, 0.08), 0 4px 6px -4px rgba(15, 23, 42, 0.05)",
    "shadow-xl":  "0 20px 25px -5px rgba(15, 23, 42, 0.08), 0 8px 10px -6px rgba(15, 23, 42, 0.05)",
}


def _flat(html: str) -> str:
    """把多行缩进 HTML 压成一行。

    Streamlit 的 Markdown 渲染器遇到「空行 + 缩进」会把后续内容当代码块，
    组件 HTML 里的换行会整块变成代码，所以统一压平后再渲染。
    """
    return " ".join(line.strip() for line in html.strip().splitlines())


# ============================================================
# 公共接口
# ============================================================
def sidebar_brand(title="OfferAgent", subtitle="求职智能体 Pro", initials="OA"):
    """侧边栏品牌区。"""
    st.markdown(_flat(f"""
    <div class="p-brand">
        <div class="p-brand-logo">{initials}</div>
        <div>
            <div class="p-brand-title">{title}</div>
            <div class="p-brand-sub">{subtitle}</div>
        </div>
    </div>
    """), unsafe_allow_html=True)


def sidebar_section(title):
    """侧边栏分组标题。"""
    st.markdown(f'<div class="p-section-label">{title}</div>', unsafe_allow_html=True)


def hero(title, subtitle="", stats=None, label=None, visual=None):
    """Hero / 页面头横幅。

    stats : [(值, 标签)]，最多 4 个；有 stats 时不再显示为紧凑头
    visual: 右侧插槽（原始 HTML 字符串）；传入时启用左右两栏布局
    """
    label_html = f'<div class="p-hero-label">{label}</div>' if label else ""

    stats_html = ""
    if stats:
        items = "".join(
            f'<div class="p-hero-stat"><div class="p-hero-stat-num">{v}</div>'
            f'<div class="p-hero-stat-label">{l}</div></div>'
            for v, l in stats[:4]
        )
        stats_html = f'<div class="p-hero-stats">{items}</div>'

    cls = "p-hero" if (stats or visual) else "p-hero p-hero--slim"
    right_html = f'<div class="p-hero-right">{visual}</div>' if visual else ""

    html = (
        f'<div class="{cls}"><div class="p-hero-grid"><div class="p-hero-left">'
        f'{label_html}<div class="p-hero-title">{title}</div>'
        f'<p class="p-hero-sub">{subtitle}</p>{stats_html}'
        f'</div>{right_html}</div></div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def stat_card(title, value, delta=None, delta_direction=None, sparkline=None):
    """数据统计卡片。
    
    delta_direction: "up"/"down"/None
    """
    if delta_direction == "up":
        delta_class = "up"
        delta_icon = "↑"
    elif delta_direction == "down":
        delta_class = "down"
        delta_icon = "↓"
    else:
        delta_class = "flat"
        delta_icon = "—"
    
    delta_html = f'<div class="p-stat-card-delta {delta_class}">{delta_icon} {delta}</div>' if delta else ""

    return _flat(f"""
    <div class="p-stat-card">
        <div class="p-stat-card-label">{title}</div>
        <div class="p-stat-card-value">{value}</div>
        {delta_html}
    </div>
    """)


def section_title(title, action=None):
    """分节标题。"""
    action_html = f'<div class="p-section-action">{action}</div>' if action else ""
    st.markdown(_flat(f"""
    <div class="p-section">
        <div class="p-section-title">{title}</div>
        {action_html}
    </div>
    """), unsafe_allow_html=True)


def quick_action(icon, title, desc):
    """快捷入口卡片。"""
    return _flat(f"""
    <div class="p-quick-card">
        <div class="p-quick-icon">{icon}</div>
        <div class="p-quick-text">
            <div class="p-quick-title">{title}</div>
            <div class="p-quick-desc">{desc}</div>
        </div>
        <div class="p-quick-arrow">→</div>
    </div>
    """)


def tag(text, variant="primary"):
    """标签。variant: primary/success/warning/danger/slate/accent"""
    return f'<span class="p-tag {variant}">{text}</span>'


def progress(value, max_val=100):
    """进度条。"""
    pct = min(100, max(0, value / max_val * 100))
    return f'<div class="p-progress"><div class="p-progress-bar" style="width:{pct}%"></div></div>'


def list_item(icon, title, sub="", right_text="", right_tag=None):
    """列表项。"""
    right_tag_html = f'<div>{tag(right_tag[0], right_tag[1])}</div>' if right_tag else ""
    right_html = f'<div class="p-list-right">{right_tag_html}<div style="font-size:11px;color:var(--slate-500);margin-top:4px">{right_text}</div></div>' if (right_text or right_tag) else ""
    return _flat(f"""
    <div class="p-list-item">
        <div class="p-list-avatar">{icon}</div>
        <div class="p-list-content">
            <div class="p-list-title">{title}</div>
            <div class="p-list-sub">{sub}</div>
        </div>
        {right_html}
    </div>
    """)


def card_start():
    """白色卡片容器开始。"""
    st.markdown('<div class="p-card">', unsafe_allow_html=True)


def card_end():
    """白色卡片容器结束。"""
    st.markdown('</div>', unsafe_allow_html=True)
