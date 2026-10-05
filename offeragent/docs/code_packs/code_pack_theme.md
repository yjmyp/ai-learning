# 代码包：主题与 UI 工具（视觉层）

> 内容包括：主题 CSS（theme.py，纯样式）、UI 公共组件（ui_kit.py）、v41 模块。目标是让 AI 在需要改视觉时能看懂主题结构。

## 怎么喂
把本文件全文复制给 DeepSeek，开头加一句：
> 「先读完全文代码，再按我的水平逐块讲解，一次一小步，先框架后填空，不直接给完整答案。」

## 包含的文件

| 文件 | 行数 | 说明 |
|---|---|---|
| `offeragent/theme.py` | 763 | 见下方代码 |
| `offeragent/ui_kit.py` | 244 | 见下方代码 |
| `offeragent/v41.py` | 236 | 见下方代码 |

**合计 1243 行**（约 4KB），在 DeepSeek 上下文内。

---

## ===== offeragent/theme.py（763 行）=====

```python
# -*- coding: utf-8 -*-
"""
theme · OfferAgent v4 界面样式
==============================
设计原则（参考多个求职/简历类产品的视觉）：
  1. 石板灰中性色打底 + 深蓝主色 + 极少青绿点缀。求职是严肃场合，不搞花哨渐变。
  2. 一屏之内信息密度可控：紧凑页头、卡片边界清晰、留白一致。
  3. 只用 12px 圆角、1px 边框、极轻阴影，靠层次而不是颜色堆砌。
"""

CSS = """
<style>
:root {
  --brand: #1D4ED8;
  --brand-hover: #1E40AF;
  --brand-soft: #EFF4FF;
  --ink: #0F172A;
  --muted: #64748B;
  --bg: #F8FAFC;
  --card: #FFFFFF;
  --line: #E2E8F0;
  --line-strong: #CBD5E1;
  --radius: 12px;
}
.stApp { background: var(--bg); }
/* 内容宽度和顶部留白：Streamlit 的容器类名是 .block-container（前面没有 main） */
.block-container, section.main > div.block-container {
  max-width: 1180px !important;
  padding-top: 1.6rem !important;
  padding-bottom: 3rem !important;
}
/* 元素之间的默认间距收一点，页面更紧凑 */
[data-testid="stVerticalBlock"] { gap: 0.65rem; }
[data-testid="stHorizontalBlock"] { gap: 0.65rem; }

/* 侧边栏 */
[data-testid="stSidebar"] { background: #0F172A; border-right: 1px solid #1E293B; }
[data-testid="stSidebar"] * { color: #E2E8F0; }
[data-testid="stSidebar"] hr { border-color: #1E293B; }
[data-testid="stSidebar"] > div:first-child { padding-top: 1.1rem; }
[data-testid="stSidebar"] h2 {
  font-size: 17px; letter-spacing: .01em; color: #F8FAFC !important;
}
[data-testid="stSidebar"] .stRadio label {
  font-size: 14.5px; padding: 9px 12px; border-radius: 8px;
  margin-bottom: 3px; transition: background .15s ease, color .15s ease;
  border: 1px solid transparent;
}
[data-testid="stSidebar"] .stRadio label:hover {
  background: rgba(255,255,255,0.07); border-color: rgba(255,255,255,0.08);
}
/* 选中项：左侧一条蓝色竖线 + 浅底，像产品菜单 */
[data-testid="stSidebar"] .stRadio label:has(input:checked) {
  background: rgba(29,78,216,0.18); border-color: rgba(29,78,216,0.45);
  box-shadow: inset 3px 0 0 var(--brand);
}
[data-testid="stSidebar"] .stRadio label:has(input:checked) * { color: #FFFFFF; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #94A3B8; }

/* 排版 */
html, body, [class*="css"] { font-size: 15px; }
h1, h2, h3 { color: var(--ink); letter-spacing: -0.01em; line-height: 1.35; }
h2 { font-size: 17px; }
h3 { font-size: 15.5px; }
p, li { line-height: 1.7; }

/* 紧凑页头（替代原来的渐变 hero） */
.oa-head { border-bottom: 1px solid var(--line); padding-bottom: 12px; margin-bottom: 18px; }
.oa-head-title { font-size: 22px; font-weight: 650; color: var(--ink); }
.oa-head-sub { font-size: 13px; color: var(--muted); margin-top: 4px; }

/* 指标 */
div[data-testid="stMetric"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 14px 16px;
  transition: border-color .15s ease, box-shadow .15s ease;
}
div[data-testid="stMetric"]:hover {
  border-color: var(--line-strong); box-shadow: 0 4px 12px rgba(15,23,42,.06);
}
div[data-testid="stMetric"] label { color: var(--muted); font-size: 12.5px; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
  color: var(--ink); font-weight: 650; font-size: 26px;
}

/* 按钮 */
.stButton > button {
  border-radius: 9px; border: 1px solid var(--line); background: var(--card);
  color: var(--ink); font-weight: 600; font-size: 14px; transition: all .15s ease;
}
.stButton > button:hover {
  border-color: var(--brand); color: var(--brand); background: var(--brand-soft);
}
.stButton > button[kind="primary"] {
  background: var(--brand); border: 1px solid var(--brand); color: #fff;
}
.stButton > button[kind="primary"]:hover { background: var(--brand-hover); color: #fff; }
textarea, .stTextInput input, [data-baseweb="select"] > div { border-radius: 9px !important; }

/* 卡片 / 展开 / 标签页 */
div[data-testid="stExpander"] {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
}
div[data-testid="stExpander"] summary { font-weight: 600; font-size: 14.5px; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--line); }
[data-testid="stTabs"] button[role="tab"] { border-radius: 8px 8px 0 0; padding: 8px 14px; font-size: 14.5px; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { color: var(--brand); font-weight: 600; }
[data-testid="stStatusWidget"] { display: none; }

.oa-card {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 15px 17px; margin-bottom: 10px; line-height: 1.75;
}
.oa-tag {
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 11.5px; font-weight: 600; margin-right: 6px;
}
.oa-tag-blue  { background: #DBEAFE; color: #1D4ED8; }
.oa-tag-green { background: #D1FAE5; color: #065F46; }
.oa-tag-amber { background: #FEF3C7; color: #92400E; }
.oa-tag-red   { background: #FEE2E2; color: #991B1B; }
.stCodeBlock pre { border-radius: 10px; font-size: 13.5px; }

/* 聊天（问答式蒸馏） */
[data-testid="stChatMessage"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 13px 15px; margin-bottom: 9px;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: var(--brand-soft); border-color: #DBEAFE;
}
[data-testid="stChatMessage"] p { margin-bottom: 5px; }
[data-testid="stChatInput"] {
  border-radius: 11px; border: 1px solid var(--line-strong); background: var(--card);
}

/* 其他 */
[data-testid="stProgress"] div[role="progressbar"] > div > div {
  background: var(--brand); border-radius: 999px;
}
[data-testid="stPlotlyChart"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 8px;
}
[data-testid="stDataFrame"] {
  border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden;
}
[data-testid="stAlert"] { border-radius: 10px; font-size: 14px; }
hr { border-color: var(--line); margin: 16px 0; }
textarea:focus, .stTextInput input:focus {
  border-color: var(--brand) !important;
  box-shadow: 0 0 0 3px rgba(29,78,216,.12) !important;
}
@media (max-width: 640px) {
  .oa-head-title { font-size: 19px; }
  main .block-container { padding-left: 12px; padding-right: 12px; }
}
</style>
"""
CSS_B = """
<style>
/* ===== 方案 B · Linear 风格：深色窄侧边栏 + 紧凑高密度内容区 ===== */
:root {
  --brand: #5E6AD2;
  --brand-hover: #4F5ABF;
  --brand-soft: #EEF0FC;
  --ink: #14161A;
  --muted: #6B7280;
  --bg: #FCFCFD;
  --card: #FFFFFF;
  --line: #E6E6E9;
  --radius: 7px;
}
.stApp { background: var(--bg); }
.block-container, section.main > div.block-container {
  max-width: 1320px !important; padding-top: 1rem !important; padding-bottom: 2.4rem !important;
}
[data-testid="stVerticalBlock"] { gap: 0.42rem; }
[data-testid="stHorizontalBlock"] { gap: 0.5rem; }

/* 深色窄侧边栏 */
[data-testid="stSidebar"] {
  background: #0B0D12; border-right: 1px solid #1B1F27; width: 232px !important;
}
[data-testid="stSidebar"] * { color: #C9CDD6; }
[data-testid="stSidebar"] hr { border-color: #1B1F27; margin: 10px 0; }
[data-testid="stSidebar"] > div:first-child { padding-top: .9rem; }
[data-testid="stSidebar"] h2 { font-size: 15px !important; color: #FFFFFF !important; letter-spacing: .01em; }
[data-testid="stSidebar"] .stRadio label {
  font-size: 13px; padding: 6px 10px; border-radius: 6px; margin-bottom: 1px;
  transition: background .12s ease;
}
[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.06); }
[data-testid="stSidebar"] .stRadio label:has(input:checked) {
  background: rgba(255,255,255,0.09); box-shadow: none;
}
[data-testid="stSidebar"] .stRadio label:has(input:checked) * { color: #FFFFFF; }

/* 紧凑排版 */
html, body, [class*="css"] { font-size: 13.5px; }
h1, h2, h3 { color: var(--ink); line-height: 1.3; letter-spacing: -0.005em; }
h2 { font-size: 15.5px; }
p, li { line-height: 1.5; }
.oa-head { border-bottom: 1px solid var(--line); padding-bottom: 9px; margin-bottom: 12px; }
.oa-head-title { font-size: 18px; font-weight: 600; color: var(--ink); }
.oa-head-sub { font-size: 12.5px; color: var(--muted); margin-top: 3px; }

/* 小号指标 */
div[data-testid="stMetric"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 10px 12px;
}
div[data-testid="stMetric"]:hover { border-color: #D4D4D8; }
div[data-testid="stMetric"] label { color: var(--muted); font-size: 11.5px; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
  color: var(--ink); font-weight: 600; font-size: 21px;
}

/* 小号按钮 */
.stButton > button {
  border-radius: 6px; border: 1px solid var(--line); background: var(--card);
  color: var(--ink); font-weight: 500; font-size: 13px; padding: 3px 10px; min-height: 30px;
}
.stButton > button:hover { border-color: var(--brand); color: var(--brand); background: var(--card); }
.stButton > button[kind="primary"] { background: var(--brand); border-color: var(--brand); color: #fff; }
.stButton > button[kind="primary"]:hover { background: var(--brand-hover); color: #fff; }
textarea, .stTextInput input, [data-baseweb="select"] > div { border-radius: 6px !important; font-size: 13.5px; }

div[data-testid="stExpander"] {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
}
div[data-testid="stExpander"] summary { font-weight: 500; font-size: 13.5px; padding: 6px 10px; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 2px; border-bottom: 1px solid var(--line); }
[data-testid="stTabs"] button[role="tab"] { border-radius: 5px 5px 0 0; padding: 6px 11px; font-size: 13px; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { color: var(--brand); font-weight: 600; }
[data-testid="stStatusWidget"] { display: none; }

.oa-card {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 11px 13px; margin-bottom: 7px; line-height: 1.55;
}
.oa-tag { display:inline-block; padding:1px 8px; border-radius:5px; font-size:11px; font-weight:500; margin-right:5px; }
.oa-tag-blue{background:#E6E9FB;color:#3F4BB8} .oa-tag-green{background:#E3F5EA;color:#1F7A45}
.oa-tag-amber{background:#FBF0DC;color:#8A5A12} .oa-tag-red{background:#FBE9E9;color:#A02B2B}
.stCodeBlock pre { border-radius: 6px; font-size: 12.5px; }

[data-testid="stChatMessage"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 7px; padding: 10px 12px; margin-bottom: 6px;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: var(--brand-soft); border-color: #DDE0F5;
}
[data-testid="stChatInput"] { border-radius: 8px; border: 1px solid var(--line); background: var(--card); }
[data-testid="stProgress"] div[role="progressbar"] > div > div { background: var(--brand); border-radius: 999px; }
[data-testid="stPlotlyChart"] {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 6px;
}
[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius: var(--radius); overflow:hidden; }
[data-testid="stAlert"] { border-radius: 6px; font-size: 13px; }
hr { border-color: var(--line); margin: 10px 0; }
textarea:focus, .stTextInput input:focus { border-color: var(--brand) !important; box-shadow: 0 0 0 2px rgba(94,106,210,.14) !important; }
</style>
"""

CSS_C = """
<style>
/* ===== 方案 C · Stripe / Material 风格：浅色侧边栏 + 宽松留白 ===== */
:root {
  --brand: #635BFF;
  --brand-hover: #544DE0;
  --brand-soft: #F2F1FF;
  --ink: #0A2540;
  --muted: #425466;
  --bg: #F6F9FC;
  --card: #FFFFFF;
  --line: #E6EBF1;
  --radius: 12px;
}
.stApp { background: var(--bg); }
.block-container, section.main > div.block-container {
  max-width: 1080px !important; padding-top: 2rem !important; padding-bottom: 4rem !important;
}
[data-testid="stVerticalBlock"] { gap: 1.05rem; }
[data-testid="stHorizontalBlock"] { gap: 1rem; }

/* 浅色侧边栏（和方案 B 形成对比） */
[data-testid="stSidebar"] {
  background: #FFFFFF; border-right: 1px solid var(--line); width: 258px !important;
}
[data-testid="stSidebar"] * { color: var(--ink); }
[data-testid="stSidebar"] hr { border-color: var(--line); margin: 14px 0; }
[data-testid="stSidebar"] > div:first-child { padding-top: 1.4rem; }
[data-testid="stSidebar"] h2 { font-size: 18px !important; color: var(--ink) !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: var(--muted); }
[data-testid="stSidebar"] .stRadio label {
  font-size: 15px; padding: 10px 14px; border-radius: 9px; margin-bottom: 4px;
  transition: background .15s ease, box-shadow .15s ease;
}
[data-testid="stSidebar"] .stRadio label:hover { background: #F0F4F9; }
[data-testid="stSidebar"] .stRadio label:has(input:checked) {
  background: #F0F4F9; box-shadow: inset 3px 0 0 var(--brand);
}
[data-testid="stSidebar"] .stRadio label:has(input:checked) * { color: var(--brand); font-weight: 600; }

/* 宽松排版 */
html, body, [class*="css"] { font-size: 15.5px; }
h1, h2, h3 { color: var(--ink); line-height: 1.4; }
h2 { font-size: 19px; }
p, li { line-height: 1.8; }
.oa-head { border-bottom: 1px solid var(--line); padding-bottom: 16px; margin-bottom: 24px; }
.oa-head-title { font-size: 26px; font-weight: 700; color: var(--ink); letter-spacing: -0.02em; }
.oa-head-sub { font-size: 14px; color: var(--muted); margin-top: 6px; }

/* 大号指标 */
div[data-testid="stMetric"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 18px 20px;
  box-shadow: 0 1px 2px rgba(10,37,64,.05);
}
div[data-testid="stMetric"]:hover { box-shadow: 0 4px 12px rgba(10,37,64,.08); }
div[data-testid="stMetric"] label { color: var(--muted); font-size: 13px; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
  color: var(--ink); font-weight: 700; font-size: 30px;
}

/* 大号按钮 */
.stButton > button {
  border-radius: 8px; border: 1px solid var(--line); background: var(--card);
  color: var(--ink); font-weight: 600; font-size: 15px; padding: 9px 16px; min-height: 42px;
}
.stButton > button:hover { border-color: var(--brand); color: var(--brand); background: var(--brand-soft); }
.stButton > button[kind="primary"] { background: var(--brand); border-color: var(--brand); color: #fff; }
.stButton > button[kind="primary"]:hover { background: var(--brand-hover); color: #fff; }
textarea, .stTextInput input, [data-baseweb="select"] > div { border-radius: 8px !important; font-size: 15px; }

div[data-testid="stExpander"] {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
  box-shadow: 0 1px 2px rgba(10,37,64,.04);
}
div[data-testid="stExpander"] summary { font-weight: 600; font-size: 15px; padding: 10px 14px; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid var(--line); }
[data-testid="stTabs"] button[role="tab"] { border-radius: 8px 8px 0 0; padding: 10px 18px; font-size: 15px; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { color: var(--brand); font-weight: 600; }
[data-testid="stStatusWidget"] { display: none; }

.oa-card {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 20px 22px; margin-bottom: 14px; line-height: 1.85;
  box-shadow: 0 1px 3px rgba(10,37,64,.05);
}
.oa-tag { display:inline-block; padding:3px 12px; border-radius:999px; font-size:12.5px; font-weight:600; margin-right:7px; }
.oa-tag-blue{background:#EAE8FF;color:#4638D6} .oa-tag-green{background:#DFF5E8;color:#1F7A45}
.oa-tag-amber{background:#FDF2DF;color:#8A5A12} .oa-tag-red{background:#FDE8E8;color:#A02B2B}
.stCodeBlock pre { border-radius: 9px; font-size: 14px; }

[data-testid="stChatMessage"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 18px 20px; margin-bottom: 12px;
  box-shadow: 0 1px 2px rgba(10,37,64,.04);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: var(--brand-soft); border-color: #E0DDFF;
}
[data-testid="stChatInput"] { border-radius: 10px; border: 1px solid var(--line); background: var(--card); }
[data-testid="stProgress"] div[role="progressbar"] > div > div { background: var(--brand); border-radius: 999px; }
[data-testid="stPlotlyChart"] {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); padding: 12px;
  box-shadow: 0 1px 2px rgba(10,37,64,.04);
}
[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius: var(--radius); overflow:hidden; }
[data-testid="stAlert"] { border-radius: 10px; font-size: 14.5px; }
hr { border-color: var(--line); margin: 22px 0; }
textarea:focus, .stTextInput input:focus { border-color: var(--brand) !important; box-shadow: 0 0 0 3px rgba(99,91,255,.14) !important; }
@media (max-width: 640px) {
  .oa-head-title { font-size: 21px; }
  .block-container { padding-left: 14px !important; padding-right: 14px !important; }
}
</style>
"""

CSS_D = """
<style>
/* ===== 方案 D · 精修结合版：C 的浅色宽松 + B 的精准（导航态/边框纪律/密度控制） ===== */
:root {
  --brand: #5558D6;
  --brand-hover: #474AC4;
  --brand-soft: #EEEFFF;
  --ink: #101A2B;
  --muted: #5C6B7A;
  --faint: #93A1AF;
  --bg: #F4F6FA;
  --card: #FFFFFF;
  --line: #E3E8EF;
  --line-soft: #EEF2F7;
  --radius: 14px;
  --shadow-sm: 0 1px 2px rgba(16,24,40,.04);
  --shadow-md: 0 2px 6px rgba(16,24,40,.06), 0 8px 24px -12px rgba(16,24,40,.12);
}
.stApp { background: var(--bg); }
.block-container, section.main > div.block-container {
  max-width: 1120px !important;
  padding-top: 2.1rem !important;
  padding-bottom: 4rem !important;
}
[data-testid="stVerticalBlock"] { gap: 1rem; }
[data-testid="stHorizontalBlock"] { gap: .9rem; }

/* ---------- 侧边栏：浅色但更利落 ---------- */
[data-testid="stSidebar"] {
  background: #FBFCFE; border-right: 1px solid var(--line); width: 262px !important;
}
[data-testid="stSidebar"] * { color: var(--ink); }
[data-testid="stSidebar"] > div:first-child { padding-top: 1.3rem; }
[data-testid="stSidebar"] h2 {
  font-size: 19px !important; font-weight: 750 !important; letter-spacing: -.01em;
  color: var(--ink) !important;
}
[data-testid="stSidebar"] h2::after {
  content: ""; display: block; width: 26px; height: 3px; border-radius: 2px;
  background: var(--brand); margin-top: 7px;
}
[data-testid="stSidebar"] hr { border-color: var(--line); margin: 15px 0; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  color: var(--faint) !important; font-size: 12.5px;
}
[data-testid="stSidebar"] .stRadio > label:first-of-type {
  color: var(--faint) !important; font-size: 11.5px; letter-spacing: .06em;
  text-transform: uppercase; margin-bottom: 4px;
}
[data-testid="stSidebar"] .stRadio label {
  font-size: 14.5px; padding: 10px 13px; border-radius: 10px; margin-bottom: 3px;
  color: var(--muted); transition: background .15s ease, color .15s ease;
}
[data-testid="stSidebar"] .stRadio label * { color: inherit !important; }
[data-testid="stSidebar"] .stRadio label:hover { background: #F1F5F9; color: var(--ink); }
[data-testid="stSidebar"] .stRadio label:has(input:checked) {
  background: var(--brand-soft); color: var(--brand); font-weight: 650;
  box-shadow: inset 3px 0 0 var(--brand);
}

/* 侧边栏状态卡 */
.oa-side-stat {
  background: #FFFFFF; border: 1px solid var(--line); border-radius: 11px;
  padding: 11px 13px; font-size: 13px; color: var(--muted); line-height: 1.7;
}
.oa-side-stat b { color: var(--ink); font-weight: 650; }

/* 顶部流程条：一行看清自己在哪一步 */
.oa-flow {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
  background: #FFFFFF; border: 1px solid var(--line); border-radius: 11px;
  padding: 9px 14px; font-size: 12.5px; color: var(--muted);
}
.oa-flow-step { color: var(--muted); }
.oa-flow-step b { color: var(--ink); font-weight: 650; margin-left: 2px; }
.oa-flow-arrow { color: #C3CBD8; }
.oa-flow-today {
  margin-left: auto; padding: 2px 10px; border-radius: 999px;
  background: var(--brand-soft, #EFF4FF); color: var(--brand, #1D4ED8);
  font-weight: 600;
}

/* ---------- 排版 ---------- */
html, body, [class*="css"] { font-size: 15.5px; }
h1, h2, h3 { color: var(--ink); line-height: 1.4; }
h2 {
  font-size: 18px !important; font-weight: 680 !important;
  display: flex; align-items: center; gap: 9px; margin-top: .4rem !important;
}
h2::before {
  content: ""; width: 4px; height: 15px; border-radius: 2px; background: var(--brand);
  display: inline-block; flex: none;
}
h3 { font-size: 16px; font-weight: 650; }
p, li { line-height: 1.8; }
.oa-head {
  border-bottom: 1px solid var(--line); padding-bottom: 16px; margin-bottom: 22px;
}
.oa-head-title {
  font-size: 27px; font-weight: 750; color: var(--ink); letter-spacing: -.025em;
}
.oa-head-sub { font-size: 14px; color: var(--muted); margin-top: 7px; }

/* ---------- 指标卡：数字更大、标签更克制 ---------- */
div[data-testid="stMetric"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 18px 20px; box-shadow: var(--shadow-sm);
  transition: box-shadow .18s ease, transform .18s ease, border-color .18s ease;
}
div[data-testid="stMetric"]:hover {
  box-shadow: var(--shadow-md); border-color: #D8E0EA; transform: translateY(-1px);
}
div[data-testid="stMetric"] label {
  color: var(--faint); font-size: 12px; letter-spacing: .04em;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
  color: var(--ink); font-weight: 750; font-size: 32px; letter-spacing: -.02em;
}

/* ---------- 按钮 ---------- */
.stButton > button {
  border-radius: 10px; border: 1px solid var(--line); background: var(--card);
  color: var(--ink); font-weight: 600; font-size: 14.5px; padding: 9px 16px;
  min-height: 40px; transition: all .16s ease; box-shadow: var(--shadow-sm);
}
.stButton > button:hover {
  border-color: #CFD8E3; color: var(--brand); background: #FCFCFF;
  box-shadow: var(--shadow-md); transform: translateY(-1px);
}
.stButton > button[kind="primary"] {
  background: var(--brand); border-color: var(--brand); color: #fff;
}
.stButton > button[kind="primary"]:hover { background: var(--brand-hover); color: #fff; }

/* ---------- 输入控件 ---------- */
textarea, .stTextInput input, [data-baseweb="select"] > div {
  border-radius: 10px !important; font-size: 15px !important;
  border-color: var(--line) !important; background: #FFFFFF !important;
}
textarea:focus, .stTextInput input:focus {
  border-color: var(--brand) !important;
  box-shadow: 0 0 0 3px rgba(85,88,214,.13) !important;
}

/* ---------- 卡片 / 展开 / 标签页 ---------- */
div[data-testid="stExpander"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); box-shadow: var(--shadow-sm); overflow: hidden;
}
div[data-testid="stExpander"] summary {
  font-weight: 620; font-size: 15px; padding: 12px 16px;
}
div[data-testid="stExpander"] summary:hover { background: #FBFCFE; }
/* 标签页做成胶囊样式，比下划线更现代 */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: 6px; border-bottom: 1px solid var(--line); padding-bottom: 8px;
}
[data-testid="stTabs"] button[role="tab"] {
  border-radius: 9px; padding: 8px 16px; font-size: 14.5px; color: var(--muted);
  border: 1px solid transparent;
}
[data-testid="stTabs"] button[role="tab"]:hover { background: #F1F5F9; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
  background: var(--brand-soft); color: var(--brand); font-weight: 650;
  border-color: #DDDEFB;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] { display: none; }
[data-testid="stStatusWidget"] { display: none; }

.oa-card {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 20px 22px; margin-bottom: 14px; line-height: 1.85; box-shadow: var(--shadow-sm);
}
.oa-tag {
  display: inline-block; padding: 3px 12px; border-radius: 999px;
  font-size: 12.5px; font-weight: 620; margin-right: 7px;
}
.oa-tag-blue  { background: #EAEAFF; color: #4344B8; }
.oa-tag-green { background: #DEF5E7; color: #1C7A46; }
.oa-tag-amber { background: #FCF0DC; color: #8A5A12; }
.oa-tag-red   { background: #FDE7E7; color: #A02B2B; }
.stCodeBlock pre {
  background: #F8FAFC !important; border: 1px solid var(--line);
  border-radius: 10px; font-size: 14px;
}

/* ---------- 聊天 ---------- */
[data-testid="stChatMessage"] {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 18px 20px; margin-bottom: 12px; box-shadow: var(--shadow-sm);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: var(--brand-soft); border-color: #DDDEFB;
}
[data-testid="stChatInput"] {
  border-radius: 12px; border: 1px solid var(--line); background: #FFFFFF;
  box-shadow: var(--shadow-sm);
}

/* ---------- 其他 ---------- */
[data-testid="stProgress"] div[role="progressbar"] > div > div {
  background: var(--brand); border-radius: 999px;
}
[data-testid="stPlotlyChart"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 12px; box-shadow: var(--shadow-sm);
}
[data-testid="stDataFrame"] {
  border: 1px solid var(--line); border-radius: var(--radius);
  overflow: hidden; box-shadow: var(--shadow-sm);
}
[data-testid="stAlert"] { border-radius: 11px; font-size: 14.5px; }
hr { border-color: var(--line); margin: 24px 0; }
@media (max-width: 640px) {
  .oa-head-title { font-size: 22px; }
  .block-container { padding-left: 14px !important; padding-right: 14px !important; }
}
</style>
"""


# ============================================================
# E · Night（GitHub Dark 风格 · 深色现代）
# 参考 GitHub Dark / Linear：近黑背景 + 蓝紫主色 + 高对比文字
# ============================================================
CSS_E = """
<style>
:root {
  --brand: #58A6FF;
  --brand-hover: #79C0FF;
  --brand-soft: rgba(88,166,255,0.14);
  --ink: #E6EDF3;
  --muted: #8B949E;
  --bg: #0D1117;
  --card: #161B22;
  --line: #30363D;
  --line-strong: #484F58;
  --radius: 12px;
}
.stApp { background: var(--bg); color: var(--ink); }
.block-container, section.main > div.block-container {
  max-width: 1180px !important;
  padding-top: 1.6rem !important;
  padding-bottom: 3rem !important;
}
[data-testid="stVerticalBlock"] { gap: 0.65rem; }
[data-testid="stHorizontalBlock"] { gap: 0.65rem; }

/* 侧边栏：比主区更黑 */
[data-testid="stSidebar"] { background: #010409; border-right: 1px solid #21262D; }
[data-testid="stSidebar"] * { color: #C9D1D9; }
[data-testid="stSidebar"] hr { border-color: #21262D; }
[data-testid="stSidebar"] > div:first-child { padding-top: 1.1rem; }
[data-testid="stSidebar"] h2 { font-size: 17px; letter-spacing: .01em; color: #F0F6FC !important; }
[data-testid="stSidebar"] .stRadio label {
  font-size: 14.5px; padding: 9px 12px; border-radius: 8px;
  margin-bottom: 3px; transition: background .15s ease, border-color .15s ease;
  border: 1px solid transparent; color: #C9D1D9;
}
[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.06); }
[data-testid="stSidebar"] .stRadio label:has(input:checked) {
  background: rgba(88,166,255,0.16); border-color: rgba(88,166,255,0.45);
  box-shadow: inset 3px 0 0 var(--brand);
}
[data-testid="stSidebar"] .stRadio label:has(input:checked) * { color: #F0F6FC; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #8B949E; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  background: #161B22; border-color: #30363D;
}

/* 排版 */
html, body, [class*="css"] { font-size: 15px; color: var(--ink); }
h1, h2, h3 { color: #F0F6FC; letter-spacing: -0.01em; line-height: 1.35; }
h2 { font-size: 17px; } h3 { font-size: 15.5px; }
p, li { line-height: 1.7; color: #C9D1D9; }
a { color: #58A6FF; }
hr { border-color: #21262D; }

.oa-head { border-bottom: 1px solid var(--line); padding-bottom: 12px; margin-bottom: 18px; }
.oa-head-title { font-size: 22px; font-weight: 650; color: #F0F6FC; }
.oa-head-sub { font-size: 13px; color: var(--muted); margin-top: 4px; }

/* 指标卡片 */
div[data-testid="stMetric"] {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 14px 16px;
  transition: border-color .15s ease, box-shadow .15s ease;
}
div[data-testid="stMetric"]:hover { border-color: var(--line-strong); box-shadow: 0 4px 14px rgba(0,0,0,.4); }
div[data-testid="stMetric"] label { color: var(--muted) !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #F0F6FC !important; }
div[data-testid="stMetric"] [data-testid="stMetricDelta"] { color: #8B949E !important; }

/* 输入控件 */
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea, [data-testid="stDateInput"] input {
  background: #0D1117; color: #E6EDF3; border-color: #30363D;
}
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
  border-color: var(--brand);
}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  background: #0D1117; border-color: #30363D; color: #E6EDF3;
}
[data-baseweb="menu"] { background: #161B22; }
[data-baseweb="menu"] li { color: #E6EDF3; }
[data-baseweb="popover"] div[data-baseweb="menu"] { background: #161B22; border-color: #30363D; }

/* 按钮 */
.stButton > button, [data-testid="stBaseButton-primary"] {
  background: #21262D; color: #F0F6FC; border: 1px solid #30363D;
  border-radius: 8px; font-weight: 500;
}
.stButton > button:hover { border-color: #8B949E; background: #30363D; }
.stButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
  background: #238636; border-color: #2EA043; color: #FFFFFF;
}
.stButton > button[kind="primary"]:hover { background: #2EA043; }
.stButton > button:disabled { background: #161B22; color: #484F58; }

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] { border-bottom: 1px solid #21262D; }
[data-testid="stTabs"] [data-baseweb="tab"] { color: #8B949E; }
[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
  color: #F0F6FC; border-bottom: 2px solid #F78166;
}

/* Expander */
[data-testid="stExpander"] details { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius); }
[data-testid="stExpander"] summary { color: #E6EDF3; }

/* 代码块 */
[data-testid="stCode"] pre, .stCodeBlock pre {
  background: #161B22 !important; border: 1px solid #30363D; color: #E6EDF3;
}

/* 卡片与标签（App 自定义类） */
.oa-card {
  background: var(--card); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 14px 16px; color: #E6EDF3;
}
.oa-tag {
  display: inline-block; padding: 2px 10px; border-radius: 999px;
  font-size: 12px; font-weight: 500;
}
.oa-tag-green { background: rgba(63,185,80,.15); color: #3FB950; }
.oa-tag-amber { background: rgba(210,153,34,.15); color: #D29922; }
.oa-tag-red   { background: rgba(248,81,73,.15); color: #F85149; }
.oa-side-stat { color: #8B949E; font-size: 13px; line-height: 1.8; }
.oa-side-stat b { color: #F0F6FC; }

/* 消息 */
[data-testid="stAlert"] { border-radius: var(--radius); }

/* 数据表 */
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: var(--radius); }
</style>
"""

# 主题注册表：A 默认（深蓝·中庸）/ B Linear（深色紧凑）/ C Stripe（浅色宽松）/
#           D 精修结合版 / E Night（GitHub 深色）
THEMES = {
    "D 精修（浅色·结合版）": CSS_D,
    "E Night（深色·GitHub 风）": CSS_E,
    "A 默认（深蓝·中庸）": CSS,
    "B Linear（深色紧凑）": CSS_B,
    "C Stripe（浅色宽松）": CSS_C,
}


def get_css(name: str = None) -> str:
    """按名字取样式；名字不认识就返回默认。"""
    if name and name in THEMES:
        return THEMES[name]
    if name:
        for k, v in THEMES.items():
            if name[0].upper() == k[0]:
                return v
    return CSS
```

## ===== offeragent/ui_kit.py（244 行）=====

```python
# -*- coding: utf-8 -*-
"""
ui_kit.py —— OfferAgent 渲染层（2026-09-29 从 offer_agent_app.py 抽出）
============================================================================
纯展示辅助：页头/标签/仪表盘图形/岗位档案/报告卡片/下一步提示。
依赖 streamlit + plotly，被页面函数 import。
"""
import re

import plotly.graph_objects as go
import streamlit as st

import job_detail
import job_quality
import theme

from store import MATCH_DIR, read_text, save_meta


def score_color(score):
    if score >= 75:
        return "#0F766E"
    if score >= 60:
        return "#2563EB"
    if score >= 45:
        return "#D97706"
    return "#B91C1C"


def score_gauge(score: int):
    color = score_color(score)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "%", "font": {"size": 44, "color": color, "family": "Arial Black"}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#CBD5E1"},
                "bar": {"color": color, "thickness": 0.28},
                "bgcolor": "#F1F5F9",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 45], "color": "#FEE2E2"},
                    {"range": [45, 60], "color": "#FEF3C7"},
                    {"range": [60, 75], "color": "#DBEAFE"},
                    {"range": [75, 100], "color": "#D1FAE5"},
                ],
            },
        )
    )
    fig.update_layout(height=240, margin=dict(l=20, r=20, t=10, b=10))
    return fig


def dim_radar(dims: dict):
    names = list(dims.keys())
    values = list(dims.values())
    fig = go.Figure(
        go.Scatterpolar(
            r=values + values[:1],
            theta=names + names[:1],
            fill="toself",
            line=dict(color="#2563EB", width=2),
            fillcolor="rgba(37,99,235,0.25)",
        )
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10))),
        height=280,
        margin=dict(l=30, r=30, t=10, b=10),
        showlegend=False,
    )
    return fig


def rank_bar(jobs):
    rows = [(m["name"], m["match_score"] or 0) for _, m, _ in jobs
            if m["status"] != "排除" and m["match_score"] is not None]
    if not rows:
        return None
    rows.sort(key=lambda x: x[1])
    names = [r[0] for r in rows]
    scores = [r[1] for r in rows]
    colors = [score_color(s) for s in scores]
    fig = go.Figure(go.Bar(
        x=scores, y=names, orientation="h",
        marker=dict(color=colors),
        text=[f"{s}%" for s in scores], textposition="outside",
    ))
    fig.update_layout(
        xaxis=dict(range=[0, 105], title="匹配度", tickfont=dict(size=11)),
        yaxis=dict(tickfont=dict(size=12)),
        height=max(220, len(names) * 42),
        margin=dict(l=10, r=50, t=10, b=10),
        bargap=0.35,
    )
    return fig


def inject_css(variant: str = None):
    """样式统一在 theme.py 维护。三套主题：A 默认 / B Linear / C Stripe。"""
    st.markdown(theme.get_css(variant), unsafe_allow_html=True)


def hero(title, subtitle, sub2=""):
    """紧凑页头：标题 + 一行说明。不再用大块渐变，保持求职场合的克制。"""
    sub = subtitle or ""
    if sub2:
        sub = f"{sub}　|　{sub2}" if sub else sub2
    st.markdown(
        f'<div class="oa-head"><div class="oa-head-title">{title}</div>'
        f'<div class="oa-head-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def status_tag(status: str):
    m = {"待投": ("oa-tag-blue", "待投"), "已投": ("oa-tag-green", "已投"),
         "排除": ("oa-tag-red", "排除")}
    cls, label = m.get(status, ("oa-tag-amber", status))
    return f'<span class="oa-tag {cls}">{label}</span>'


def render_job_detail(name: str, meta: dict, jd: str):
    """岗位档案：为什么在列表里 + 为什么保留/排除 + 这个岗位要什么人。"""
    head = f"**{meta.get('company') or name}** · {meta.get('city') or '城市未填'}"
    if meta.get("salary"):
        head += f" · 薪资 {meta['salary']}"
    st.markdown(head)

    st.markdown("**① 它是怎么进到列表里的**")
    for r in job_detail.entry_reasons(meta):
        st.markdown(f"- {r['label']}：{r['detail']}")

    st.markdown("**② 为什么保留 / 为什么排除**")
    for r in job_detail.keep_or_drop(meta):
        icon = "✅" if r.get("ok") else ("❔" if r.get("ok") is None else "⛔")
        st.markdown(f"- {icon} {r['label']}：{r['detail']}")

    parts = job_detail.split_jd(jd)
    st.markdown("**③ 这个岗位要什么人**")
    if parts["duty"]:
        st.markdown("岗位职责：")
        st.markdown(parts["duty"][:1200])
    if parts["req"]:
        st.markdown("任职要求：")
        st.markdown(parts["req"][:1200])
    if not parts["duty"] and not parts["req"]:
        st.caption("这份 JD 没有明显的「职责 / 要求」分段，下面是原文：")
        st.text((parts["other"] or jd)[:1200])
    elif parts["other"].strip():
        with st.expander("其他信息 / 原文剩余部分"):
            st.text(parts["other"][:1200])

    report = read_text(MATCH_DIR / f"match_{name}.md")
    if report:
        m = re.search(r"## 结论\s*\n+(.+)", report)
        if m:
            st.markdown("**④ 匹配结论**")
            st.markdown(m.group(1).strip())

    if not isinstance(meta.get("quality"), dict):
        st.caption("这个岗位还没有质量检查结果（早期入库的岗位没有这项）")
    if st.button("🔄 跑一次质量检查并保存", key=f"qc_{name}"):
        meta["quality"] = job_quality.assess({
            "jd": jd, "company": meta.get("company", ""),
            "city": meta.get("city", ""), "salary": meta.get("salary", ""),
            "url": meta.get("source_url", ""),
        })
        save_meta(name, meta)
        st.success("质量检查已保存，刷新后能在上面看到逐项依据")
        st.rerun()


def render_section_cards(sections: dict):
    """把解析后的报告渲染成彩色卡片组（比 markdown 好看）"""
    style_map = {
        "匹配点": ("✅ 匹配点", "#0F766E", "#D1FAE5"),
        "差距": ("📌 差距", "#1D4ED8", "#DBEAFE"),
        "短板与风险": ("⚠️ 短板与风险", "#B45309", "#FEF3C7"),
        "结论": ("🎯 结论", "#1E293B", "#E2E8F0"),
    }
    for key in ("匹配点", "差距", "短板与风险", "结论"):
        items = sections.get(key) or sections.get("短板") or []
        if not items:
            continue
        label, color, bg = style_map.get(key, (key, "#334155", "#F1F5F9"))
        lis = "".join(
            f'<div style="padding:4px 0;font-size:14px;line-height:1.6">{"• " + it}</div>'
            for it in items if it
        )
        st.markdown(
            f'<div style="background:{bg};border:1px solid {color}33;'
            f'border-radius:12px;padding:12px 16px;margin-bottom:10px">'
            f'<div style="color:{color};font-weight:700;font-size:14px;margin-bottom:4px">{label}</div>'
            f'{lis}</div>',
            unsafe_allow_html=True,
        )


NEXT_HINTS = {
    "saved_job": "下一步：去「匹配分析」跑一次匹配，看这个岗位值不值得投。",
    "matched": "下一步：在同一个岗位卡片里点「ATS 检查」，看简历关键词覆盖够不够。",
    "ats_done": "下一步：生成投递话术，复制后去招聘平台发送。",
    "talk_done": "下一步：把话术发出去，然后回来点「标记已投」；7 天后没动静会自动进跟进提醒。",
    "applied": "下一步：等消息。有回信就粘到「投递记录 → 邮件识别」里判断怎么改状态。",
    "profile_done": "下一步：去「岗位」搜一次岗，勾选入库后跑匹配。",
    "resume_saved": "下一步：去「投递 → 简历定制」，选一个目标岗位做 ATS 覆盖检查。",
}


def next_step(key: str, extra: str = "", defer: bool = False):
    """每个动作完成后，明确告诉用户下一步做什么。
    defer=True 用于「紧接着就 st.rerun()」的场景：提示先存起来，重跑完在页面底部显示。"""
    hint = NEXT_HINTS.get(key)
    if not hint:
        return
    text = hint + (("　" + extra) if extra else "")
    if defer:
        st.session_state["_pending_hint"] = text
    else:
        st.info(text)


# ============================================================
# 跨页导航（页面注册表 + 跳转）——拆分后移入公共层
# ============================================================
PAGES = {}


def goto_page(key: str, **focus):
    """跨页跳转：切到目标页，并把要预选的值先塞进 session_state。

    用法：goto_page("match", match_pick="某岗位")
    """
    for k, v in focus.items():
        st.session_state[k] = v
    page = PAGES.get(key)
    if page is None:
        st.warning(f"找不到目标页面：{key}")
        return
    st.switch_page(page)
```

## ===== offeragent/v41.py（236 行）=====

```python
# -*- coding: utf-8 -*-
"""
v41 · OfferAgent v4.1 增强模块
==============================
batch_match          批量匹配（待投且未匹配的岗位一次跑完，自动写报告+回填分数）
check_links          岗位链接有效性检测（投递前重访 URL，提示"链接已失效"）
funnel_fig           投递漏斗图（已投 → 面试 → Offer）
weekly_fig           投递周趋势线（近 14 天每天投递数）
talk_attachments     投递三件套（简历 PDF + 上线项目 + GitHub）
interview_reminders  面试日历提醒（状态"面试中"的岗位倒计时）
hash_password        密码哈希（L1 密码门用）
"""
import datetime
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go
import requests

HERE = Path(__file__).parent
DATA_DIR = HERE / "data"
JDS_DIR = DATA_DIR / "jds"
MATCH_DIR = DATA_DIR / "match_results"
LOG_PATH = DATA_DIR / "applications.jsonl"

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# ---------- 文件小工具（不依赖 app，独立可用） ----------

def read_text(p):
    try:
        return Path(p).read_text(encoding="utf-8")
    except Exception:
        return ""


def write_text(p, s):
    try:
        Path(p).write_text(s, encoding="utf-8")
        return True
    except Exception:
        return False


def load_meta(name):
    p = JDS_DIR / f"{name}.meta.json"
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def save_meta(name, meta):
    try:
        (JDS_DIR / f"{name}.meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def extract_score(text):
    """从匹配报告第一行提匹配度（# 匹配度：82%）。"""
    m = re.search(r"匹配度[:：]?\s*(\d{1,3})\s*%", text or "")
    if m:
        return min(100, max(0, int(m.group(1))))
    return None


# ---------- 1. 批量匹配 ----------

def batch_match(prompt, ask, jobs, profile, progress=None):
    """对全部「待投且未匹配」岗位跑匹配。

    ask: fn(prompt, *materials) -> str
    progress: st.progress 对象（可选）
    返回 [(name, score)]
    """
    todo = [(n, m, j) for n, m, j in jobs
            if m["status"] == "待投" and m.get("match_score") is None]
    if not todo:
        return []
    done = []
    total = len(todo)
    for i, (name, meta, jd) in enumerate(todo):
        try:
            rep = ask(prompt, profile, jd)
            MATCH_DIR.mkdir(parents=True, exist_ok=True)
            write_text(MATCH_DIR / f"match_{name}.md", rep)
            score = extract_score(rep)
            if score is not None:
                meta["match_score"] = score
                save_meta(name, meta)
            done.append((name, score))
            if progress is not None:
                progress.progress((i + 1) / total,
                                  text=f"已匹配 {name}：{score if score is not None else '失败'}%")
        except Exception as e:
            done.append((name, None))
            if progress is not None:
                progress.progress((i + 1) / total, text=f"{name} 出错：{str(e)[:40]}")
    return done


# ---------- 2. 链接有效性检测 ----------

def check_links(jobs):
    """投递前重访岗位链接。

    返回 [(name, company, url, status)]，status ∈ ok / gone / unreachable / no_url
    - gone: 404/410（明确失效，别投了）
    - unreachable: 连不上（网络/超时/反爬 5xx，需人工确认）
    - ok: 可访问（含 403/405 等反爬响应，不代表失效）
    """
    out = []
    for name, meta, _ in jobs:
        url = (meta.get("source_url") or "").strip()
        if not url:
            out.append((name, meta.get("company", "") or name, "", "no_url"))
            continue
        try:
            r = requests.head(url, timeout=6, allow_redirects=True, headers=UA)
            code = r.status_code
            if code in (404, 410):
                status = "gone"
            elif code in (401, 403, 405, 429):
                status = "ok"  # 反爬/需要登录，不代表岗位下架
            elif code < 500:
                status = "ok"
            else:
                status = "unreachable"
        except Exception:
            status = "unreachable"
        out.append((name, meta.get("company", "") or name, url, status))
    return out


# ---------- 3. 投递漏斗图 ----------

def funnel_fig(submitted, interviewed, offers):
    """已投 → 面试 → Offer 转化漏斗。"""
    fig = go.Figure(go.Funnel(
        y=["已投", "面试", "Offer"],
        x=[submitted, interviewed, offers],
        textinfo="value+percent initial",
        marker=dict(color=["#2563EB", "#0EA5E9", "#10B981"]),
        textfont=dict(size=13),
    ))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10),
                      showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
    return fig


# ---------- 4. 投递周趋势 ----------

def weekly_fig(rows, days=14):
    """近 days 天每天投递数折线。rows = applications.jsonl 读出的记录列表。"""
    by_date = defaultdict(int)
    for r in rows:
        d = r.get("date")
        if d:
            by_date[d] += 1
    today = datetime.date.today()
    xs, ys = [], []
    for i in range(days - 1, -1, -1):
        d = (today - datetime.timedelta(days=i)).isoformat()
        xs.append(d[5:])
        ys.append(by_date.get(d, 0))
    fig = go.Figure(go.Scatter(
        x=xs, y=ys, mode="lines+markers",
        line=dict(color="#2563EB", width=2),
        marker=dict(size=6, color="#1D4ED8"),
        fill="tozeroy",
        fillcolor="rgba(37,99,235,0.08)",
    ))
    fig.update_layout(
        height=260, margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(title="日期", tickfont=dict(size=11)),
        yaxis=dict(title="投递数", dtick=1, tickfont=dict(size=11)),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ---------- 5. 投递三件套 ----------

RESUME_PDF = HERE.parent / "简历" / "余剑-应聘AI应用开发实习-本科.pdf"
LIVE_URL = "https://ai-learning-fphncazxmg3pnesntwchz6.streamlit.app/"
GITHUB_URL = "https://github.com/yjmyp/ai-learning"


def talk_attachments() -> str:
    """话术尾部自动附的投递三件套。"""
    parts = []
    if RESUME_PDF.exists():
        parts.append(f"简历 PDF：{RESUME_PDF}")
    parts.append(f"上线项目：{LIVE_URL}")
    parts.append(f"GitHub：{GITHUB_URL}")
    return "\n".join(parts)


# ---------- 6. 面试日历提醒 ----------

def interview_reminders(jobs):
    """返回 [(name, company, date, days_left)]，按剩余天数升序。

    days_left < 0 表示已过日期（提示补状态）。
    """
    out = []
    today = datetime.date.today()
    for name, meta, _ in jobs:
        d = (meta.get("interview_date") or "").strip()
        if meta["status"] != "面试中" or not d:
            continue
        try:
            dt = datetime.date.fromisoformat(d)
            days = (dt - today).days
            out.append((name, meta.get("company", "") or name, d, days))
        except Exception:
            continue
    out.sort(key=lambda x: x[3])
    return out


# ---------- 7. 密码哈希 ----------

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()
```
