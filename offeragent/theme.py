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
CSS_P = """<style>
/* ============================================================
   OfferAgent · Aurora Light（自研设计系统 · 2026-10-19）
   浅色画布 + 深色侧边栏 + 极光 Hero + 精细控件
   ============================================================ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  /* 语义色（CSS_D 既有变量名，保证既有规则与页面内联样式继续生效） */
  --brand: #5B5BD6;
  --brand-hover: #4A4AC2;
  --brand-soft: #EEF0FF;
  --ink: #0B1020;
  --muted: #5A6478;
  --faint: #98A2B3;
  --bg: #F6F7FB;
  --card: #FFFFFF;
  --line: #E9EBF5;
  --line-soft: #F1F3FA;
  --radius: 16px;
  --shadow-sm: 0 1px 2px rgba(16,24,40,.05);
  --shadow-md: 0 2px 6px -1px rgba(16,24,40,.07), 0 10px 28px -18px rgba(16,24,40,.22);
  /* 设计令牌（.p-* 组件与页面内联样式用） */
  --primary-50:#EEF2FF; --primary-100:#E0E7FF; --primary-200:#C7D2FE;
  --primary-300:#A5B4FC; --primary-400:#818CF8; --primary-500:#6366F1;
  --primary-600:#4F46E5; --primary-700:#4338CA;
  --accent-500:#06B6D4; --success-500:#10B981; --warning-500:#F59E0B; --danger-500:#EF4444;
  --slate-50:#F8FAFC; --slate-100:#F1F5F9; --slate-200:#E2E8F0; --slate-300:#CBD5E1;
  --slate-400:#94A3B8; --slate-500:#64748B; --slate-600:#475569; --slate-700:#334155;
  --slate-800:#1E293B; --slate-900:#0F172A;
  --radius-sm:8px; --radius-md:12px; --radius-lg:16px; --radius-xl:20px;
  --shadow-lg: 0 10px 15px -3px rgba(15,23,42,.08), 0 4px 6px -4px rgba(15,23,42,.05);
  --ease: cubic-bezier(.4,0,.2,1);
}

/* ---------------- 全局骨架 ---------------- */
html, body, [class*="css"] {
  font-family: Inter, "Segoe UI", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
  font-size: 14.5px;
  -webkit-font-smoothing: antialiased;
}
.stApp { background: #F6F7FB; }
.stApp::before {
  content: ""; position: fixed; top: 0; left: 0; right: 0; height: 340px; z-index: 0;
  background:
    radial-gradient(900px 320px at 18% -70px, rgba(99,102,241,.11), transparent 70%),
    radial-gradient(760px 300px at 78% -90px, rgba(139,92,246,.10), transparent 72%),
    radial-gradient(520px 240px at 52% -120px, rgba(34,211,238,.08), transparent 75%);
  pointer-events: none;
}
.block-container, section.main > div.block-container {
  max-width: 1180px !important;
  padding-top: 2.2rem !important;
  padding-bottom: 4.5rem !important;
  position: relative; z-index: 1;
}
[data-testid="stVerticalBlock"] { gap: .95rem; }
[data-testid="stHorizontalBlock"] { gap: .85rem; }
#MainMenu, footer, [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stHeaderActionElements"],
[data-testid="stAppDeployButton"] { display: none !important; }

/* 顶栏不能整个隐藏：
   Streamlit 把「展开侧栏」按钮 stExpandSidebarButton 渲染在 stHeader 里，
   一旦 display:none，侧栏收起后用户就再也点不开了。
   正确做法是保留顶栏容器，只把它的背景/装饰去掉。 */
[data-testid="stHeader"] {
  background: transparent !important;
  box-shadow: none !important;
  height: auto !important;
}
[data-testid="stHeader"] [data-testid="stToolbar"] {
  right: .75rem !important;
  padding: 0 !important;
  height: 3.1rem !important;
}
[data-testid="stExpandSidebarButton"] {
  display: inline-flex !important;
  visibility: visible !important;
  opacity: 1 !important;
  align-items: center; justify-content: center;
  width: 34px !important; height: 34px !important;
  border-radius: 10px !important;
  border: 1px solid #E4E7F2 !important;
  background: #FFFFFF !important;
  color: #4A5170 !important;
  box-shadow: 0 1px 2px rgba(16,24,40,.06);
  transition: background .16s ease, border-color .16s ease, color .16s ease;
}
[data-testid="stExpandSidebarButton"]:hover {
  background: #F6F7FF !important;
  border-color: #C9CDF6 !important;
  color: #2A2F6B !important;
}
[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {
  font-size: 18px !important; color: inherit !important;
}
hr { border: none; border-top: 1px solid var(--line); margin: 22px 0; }

/* ---------------- 排版层级 ---------------- */
h1, h2, h3, h4 { color: var(--ink); }
h1, [data-testid="stMarkdownContainer"] h1 {
  font-size: 26px !important; font-weight: 750 !important;
  letter-spacing: -.022em !important; line-height: 1.25 !important;
}
h2, [data-testid="stMarkdownContainer"] h2 {
  font-size: 19px !important; font-weight: 700 !important;
  letter-spacing: -.012em !important; margin-top: .4rem !important;
}
h3, [data-testid="stMarkdownContainer"] h3 { font-size: 15.5px !important; font-weight: 650 !important; }
p, li { line-height: 1.78; }
a { color: var(--brand); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ---------------- 侧边栏：深色玻璃 ---------------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0C1120 0%, #111A30 100%);
  border-right: 1px solid rgba(255,255,255,.07);
  width: 268px !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.1rem; }
[data-testid="stSidebar"] * { color: #A9B4CF; }
[data-testid="stSidebar"] hr { border-top: 1px solid rgba(255,255,255,.08); margin: 14px 0; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #6C7899 !important; font-size: 12px; }
[data-testid="stSidebarNavItems"] { gap: 2px; }
[data-testid="stSidebarNav"] ul { padding-left: 0 !important; }
[data-testid="stNavSectionHeader"] {
  padding: 14px 12px 4px 12px !important; background: transparent !important;
}
[data-testid="stNavSectionHeader"] p {
  font-size: 10.5px !important; font-weight: 700 !important; letter-spacing: .14em !important;
  text-transform: uppercase; color: #5B6787 !important; margin: 0;
}
[data-testid="stNavSectionHeader"] span[data-testid="stIconMaterial"] { color: #44506E !important; }
[data-testid="stSidebarNavLink"] {
  border-radius: 10px !important; padding: 8px 12px !important; margin: 1px 7px !important;
  font-size: 13.8px !important; font-weight: 500 !important;
  transition: background .16s var(--ease), color .16s var(--ease);
}
[data-testid="stSidebarNavLink"]:hover { background: rgba(255,255,255,.07) !important; }
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: linear-gradient(90deg, rgba(99,102,241,.34) 0%, rgba(139,92,246,.16) 100%) !important;
  box-shadow: inset 3px 0 0 #8B93FF;
}
[data-testid="stSidebarNavLink"][aria-current="page"] * { color: #FFFFFF !important; font-weight: 650 !important; }

/* 侧边栏里的小控件（下拉/按钮）也要能看清 */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background: rgba(255,255,255,.06) !important; border-color: rgba(255,255,255,.12) !important;
}
[data-testid="stSidebar"] .stButton > button {
  background: rgba(255,255,255,.07) !important; color: #D6DEF2 !important;
  border-color: rgba(255,255,255,.14) !important;
}

/* ---------------- 按钮 ---------------- */
.stButton > button, .stDownloadButton > button, .stLinkButton > a, .stFormSubmitButton > button {
  border-radius: 11px !important; font-weight: 600 !important; font-size: 13.5px !important;
  padding: 8px 16px !important; border: 1px solid var(--line) !important;
  background: #FFFFFF !important; color: #28324A !important;
  box-shadow: 0 1px 2px rgba(16,24,40,.05);
  transition: transform .18s var(--ease), box-shadow .18s var(--ease),
              border-color .18s var(--ease), background .18s var(--ease) !important;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {
  transform: translateY(-1px); border-color: #D6DCEC !important;
  box-shadow: 0 4px 14px -6px rgba(16,24,40,.28) !important;
}
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"],
.stFormSubmitButton > button[kind="primary"] {
  background: linear-gradient(135deg, #6366F1 0%, #7C5CFC 100%) !important;
  color: #FFFFFF !important; border: none !important;
  box-shadow: 0 8px 20px -10px rgba(99,102,241,.85) !important;
}
.stButton > button[kind="primary"]:hover { filter: brightness(1.05); }

/* ---------------- 输入类控件 ---------------- */
.stTextInput input, .stNumberInput input, .stTextArea textarea,
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {
  background: #FBFBFE !important; border: 1px solid #E4E7F2 !important;
  border-radius: 11px !important; font-size: 13.5px !important; color: var(--ink) !important;
  transition: border-color .16s var(--ease), box-shadow .16s var(--ease) !important;
}
.stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus,
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within {
  border-color: #9AA6FF !important; box-shadow: 0 0 0 4px rgba(99,102,241,.13) !important;
  background: #FFFFFF !important;
}
label[data-testid="stWidgetLabel"] p, .stRadio > label p {
  font-size: 12.8px !important; font-weight: 600 !important; color: #3A4661 !important;
}
[data-testid="stTooltipIcon"] { opacity: .38; }
[data-testid="stTooltipIcon"]:hover { opacity: 1; }
[data-testid="stTooltipIcon"] svg { width: 13px !important; height: 13px !important; }

/* ---------------- 标签页（胶囊） ---------------- */
[data-testid="stTabs"] [role="tablist"] {
  gap: 6px !important; border-bottom: none !important; background: transparent !important;
}
[data-testid="stTab"] {
  border-radius: 10px !important; padding: 7px 14px !important;
  font-size: 13.5px !important; font-weight: 600 !important;
  border: 1px solid transparent !important;
  transition: background .16s var(--ease), color .16s var(--ease) !important;
}
[data-testid="stTab"]:hover { background: rgba(99,102,241,.07) !important; }
[data-testid="stTab"][aria-selected="true"] {
  background: #FFFFFF !important; color: #4F46E5 !important;
  border-color: var(--line) !important; box-shadow: 0 1px 3px rgba(16,24,40,.07);
}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none !important; }

/* ---------------- 卡片类原生控件 ---------------- */
div[data-testid="stMetric"] {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 15px 18px; box-shadow: var(--shadow-sm);
  transition: box-shadow .18s var(--ease), transform .18s var(--ease);
}
div[data-testid="stMetric"]:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
div[data-testid="stMetric"] label p { font-size: 12px !important; color: var(--faint) !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
  font-size: 25px !important; font-weight: 750 !important; color: var(--ink) !important;
}
div[data-testid="stExpander"] {
  border: 1px solid var(--line) !important; border-radius: var(--radius) !important;
  background: var(--card); box-shadow: var(--shadow-sm); overflow: hidden;
}
div[data-testid="stExpander"] summary { padding: 11px 16px !important; font-size: 13.6px !important; }
div[data-testid="stExpander"] summary:hover { background: #FAFBFF !important; }
[data-testid="stDataFrame"], [data-testid="stTable"] {
  border: 1px solid var(--line) !important; border-radius: var(--radius) !important;
  overflow: hidden; box-shadow: var(--shadow-sm);
}
[data-testid="stAlert"] {
  border-radius: 12px !important; border-width: 1px !important;
  padding: 11px 14px !important; font-size: 13.3px !important; line-height: 1.7 !important;
  box-shadow: var(--shadow-sm);
}
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] p { margin: 0; }
[data-testid="stAlert"] svg { width: 16px !important; height: 16px !important; }
div[data-testid="stSpinner"] {
  background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  padding: 10px 14px; font-size: 13px; color: var(--muted);
}
[data-testid="stProgress"] div[role="progressbar"] > div > div {
  background: linear-gradient(90deg, #6366F1, #8B5CF6) !important; border-radius: 999px;
}
[data-testid="stProgress"] div[role="progressbar"] > div { background: #EDEFF7 !important; border-radius: 999px; }
.stCodeBlock pre, code {
  border-radius: 10px !important; border: 1px solid var(--line) !important;
  background: #FAFBFF !important; font-size: 12.8px !important;
}
[data-testid="stChatMessage"] {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 12px 14px; box-shadow: var(--shadow-sm);
}
[data-testid="stChatInput"] textarea { border-radius: 12px !important; }
[data-testid="stPlotlyChart"] { border-radius: var(--radius); overflow: hidden; }
[data-testid="stFileUploaderDropzone"] {
  border-radius: 12px !important; border: 1px dashed #D3DAEA !important; background: #FBFBFE !important;
}
[data-testid="stFileUploaderDropzone"] button {
  border-radius: 10px !important; background: #fff !important; border: 1px solid var(--line) !important;
}

/* ---------------- 自定义：页头 / 流程条 ---------------- */
.oa-head { margin-bottom: 8px; }
.oa-head-title {
  font-size: 26px !important; font-weight: 750 !important;
  letter-spacing: -.022em; color: var(--ink);
}
.oa-head-sub { font-size: 13.4px !important; color: var(--muted) !important; margin-top: 6px !important; }
.oa-flow {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  padding: 10px 14px; box-shadow: var(--shadow-sm); font-size: 12.8px;
}
.oa-flow-step { color: var(--muted); }
.oa-flow-step b { color: var(--ink); font-weight: 700; margin-left: 3px; }
.oa-flow-arrow { color: #CBD3E4; }
.oa-flow-today {
  margin-left: auto; background: var(--brand-soft); color: var(--primary-600) !important;
  font-weight: 650; border-radius: 999px; padding: 5px 12px;
}
.oa-side-stat {
  background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.10);
  border-radius: 12px; padding: 11px 13px; font-size: 12.8px; line-height: 1.75;
}
.oa-side-stat b { color: #FFFFFF !important; font-weight: 700; }

/* ---------------- 自定义：卡片 / 标签 / 列表 ---------------- */
.oa-card {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 16px 18px; box-shadow: var(--shadow-sm);
}
.oa-tag {
  display: inline-block; font-size: 11.5px; font-weight: 650;
  border-radius: 999px; padding: 3px 10px; letter-spacing: .01em;
}
.oa-tag-blue  { background: #EEF0FF; color: #4344B8; }
.oa-tag-green { background: #E4F7EC; color: #157347; }
.oa-tag-amber { background: #FEF3E2; color: #8A5A12; }
.oa-tag-red   { background: #FDECEC; color: #A32B2B; }
.oa-pro-card {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
}

/* ---------------- 自定义：空态 / 错误块 / 引导 ---------------- */
.oa-empty {
  background: linear-gradient(180deg, #FFFFFF 0%, #FBFBFF 100%);
  border: 1px dashed #D8DEF0; border-radius: var(--radius);
  padding: 40px 24px; text-align: center; margin: 6px 0;
}
.oa-empty-icon { font-size: 34px; line-height: 1; margin-bottom: 12px; }
.oa-empty-title { font-size: 15px; font-weight: 700; color: var(--ink); }
.oa-empty-desc { font-size: 13px; color: var(--muted); margin-top: 6px; }
.oa-empty-hint { font-size: 12.4px; color: var(--faint); margin-top: 10px; }
.oa-errbox {
  background: #FFF5F5; border: 1px solid #FBD5D5; border-left: 3px solid #EF4444;
  border-radius: 12px; padding: 12px 15px; margin: 6px 0;
}
.oa-errbox-title { font-size: 13.3px; font-weight: 700; color: #9B1C1C; }
.oa-errbox-detail { font-size: 12.5px; color: #B42318; margin-top: 5px; line-height: 1.7; }
.oa-onboard {
  background: linear-gradient(135deg, #F3F4FF 0%, #FFFFFF 60%);
  border: 1px solid #E4E7F9; border-radius: var(--radius);
  padding: 18px 20px; margin: 4px 0 8px;
}
.oa-onboard-head {
  font-size: 13.6px; font-weight: 750; color: var(--ink); margin-bottom: 12px;
  letter-spacing: -.01em;
}
.oa-step { display: flex; gap: 12px; align-items: flex-start; margin-bottom: 10px; }
.oa-step-dot {
  flex: 0 0 22px; width: 22px; height: 22px; border-radius: 50%;
  background: linear-gradient(135deg, #6366F1, #8B5CF6); color: #FFFFFF !important;
  font-size: 11.5px; font-weight: 700; line-height: 22px; text-align: center;
}
.oa-step-title { font-size: 13.4px; font-weight: 650; color: var(--ink); }
.oa-step-hint { font-size: 12.4px; color: var(--muted); margin-top: 2px; }

/* ================= .p-* 产品级组件 ================= */
.p-brand { display: flex; align-items: center; gap: 11px; padding: 6px 12px 16px; }
.p-brand-logo {
  width: 34px; height: 34px; border-radius: 10px; flex: 0 0 34px;
  background: linear-gradient(135deg, #6366F1, #8B5CF6); color: #fff !important;
  font-size: 13px; font-weight: 800; line-height: 34px; text-align: center;
  box-shadow: 0 6px 16px -8px rgba(99,102,241,.9);
}
.p-brand-title { font-size: 14.5px; font-weight: 750; color: #FFFFFF !important; }
.p-brand-sub { font-size: 11.5px; color: #7C88A8 !important; margin-top: 1px; }
.p-section-label {
  font-size: 10.5px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase;
  color: #5B6787 !important; padding: 12px 12px 4px;
}

.p-hero {
  position: relative; overflow: hidden;
  background: #FFFFFF; border: 1px solid var(--line);
  border-radius: 20px; padding: 34px 36px; margin-bottom: 24px;
  box-shadow: 0 26px 60px -44px rgba(28,32,80,.55);
}
.p-hero::before {
  content: ""; position: absolute; top: -60%; left: -10%; right: -10%; height: 150%;
  background:
    radial-gradient(420px 220px at 10% 6%, rgba(99,102,241,.22), transparent 70%),
    radial-gradient(380px 210px at 46% 0%, rgba(139,92,246,.18), transparent 72%),
    radial-gradient(360px 200px at 88% 8%, rgba(34,211,238,.15), transparent 74%);
  pointer-events: none;
}
.p-hero > * { position: relative; }
.p-hero-label {
  font-size: 10.5px; font-weight: 750; letter-spacing: .16em; text-transform: uppercase;
  color: #5B5BD6; margin-bottom: 10px;
}
.p-hero-title {
  font-size: 31px; font-weight: 800; letter-spacing: -.028em; line-height: 1.18;
  color: #0B1020; margin: 0 0 10px;
}
.p-hero-sub { font-size: 14.4px; color: #59637A; margin: 0; max-width: 720px; line-height: 1.7; }
.p-hero-stats { display: flex; gap: 40px; margin-top: 24px; flex-wrap: wrap; }
.p-hero-stat { display: flex; flex-direction: column; }
.p-hero-stat-num {
  font-size: 26px; font-weight: 800; letter-spacing: -.02em; color: #141A2E;
  font-variant-numeric: tabular-nums;
}
.p-hero-stat-label { font-size: 12px; color: #7A8699; margin-top: 2px; }

.p-section { display: flex; align-items: baseline; justify-content: space-between; margin: 20px 0 10px; }
.p-section-title { font-size: 16.5px; font-weight: 720; color: var(--ink); letter-spacing: -.012em; }
.p-section-action { font-size: 12.4px; color: var(--faint); }

.p-stat-card {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 16px 18px; box-shadow: var(--shadow-sm);
  transition: box-shadow .18s var(--ease), transform .18s var(--ease);
}
.p-stat-card:hover { box-shadow: var(--shadow-md); transform: translateY(-1px); }
.p-stat-card-label { font-size: 12px; color: var(--faint); font-weight: 600; }
.p-stat-card-value {
  font-size: 26px; font-weight: 780; color: var(--ink); margin-top: 6px;
  letter-spacing: -.02em; font-variant-numeric: tabular-nums;
}
.p-stat-card-delta { font-size: 12px; margin-top: 4px; font-weight: 600; }
.p-stat-card-delta.up { color: #157347; }
.p-stat-card-delta.down { color: #B42318; }
.p-stat-card-delta.flat { color: var(--faint); }

.p-card {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 16px 20px; box-shadow: var(--shadow-sm);
}
.p-quick-card {
  display: flex; align-items: center; gap: 13px;
  background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  padding: 14px 16px; box-shadow: var(--shadow-sm); cursor: pointer;
  transition: transform .18s var(--ease), box-shadow .18s var(--ease), border-color .18s var(--ease);
}
.p-quick-card:hover {
  transform: translateY(-2px); border-color: #DCE1F5; box-shadow: var(--shadow-md);
}
.p-quick-icon {
  width: 38px; height: 38px; flex: 0 0 38px; border-radius: 11px;
  background: linear-gradient(135deg, #EEF0FF, #F3EEFF); color: #4F46E5 !important;
  font-size: 17px; line-height: 38px; text-align: center;
}
.p-quick-text { flex: 1; min-width: 0; }
.p-quick-title { font-size: 13.6px; font-weight: 680; color: var(--ink); }
.p-quick-desc { font-size: 12.2px; color: var(--muted); margin-top: 2px; }
.p-quick-arrow { color: #C3CBDE; font-size: 15px; transition: transform .18s var(--ease), color .18s var(--ease); }
.p-quick-card:hover .p-quick-arrow { color: var(--brand); transform: translateX(3px); }

.p-tag {
  display: inline-block; border-radius: 999px; padding: 3px 10px;
  font-size: 11.5px; font-weight: 650; background: #EEF0FF; color: #4344B8;
}
.p-tag.success { background: #E4F7EC; color: #157347; }
.p-tag.warning { background: #FEF3E2; color: #8A5A12; }
.p-tag.danger  { background: #FDECEC; color: #A32B2B; }
.p-tag.slate   { background: #F1F3F9; color: #4A5468; }
.p-tag.accent  { background: #E3F7FB; color: #0E7490; }
.p-tag.primary { background: #EEF0FF; color: #4344B8; }

.p-progress { height: 8px; background: #EDEFF7; border-radius: 999px; overflow: hidden; }
.p-progress-bar {
  height: 100%; border-radius: 999px;
  background: linear-gradient(90deg, #6366F1, #8B5CF6);
  transition: width .5s var(--ease);
}

.p-list-item {
  display: flex; align-items: center; gap: 13px;
  padding: 11px 4px; border-bottom: 1px solid var(--line-soft);
}
.p-list-item:last-child { border-bottom: none; }
.p-list-avatar {
  width: 36px; height: 36px; flex: 0 0 36px; border-radius: 11px;
  background: linear-gradient(135deg, #EEF0FF, #F4EEFF); color: #4F46E5 !important;
  font-size: 16px; line-height: 36px; text-align: center;
}
.p-list-content { flex: 1; min-width: 0; }
.p-list-title { font-size: 13.6px; font-weight: 650; color: var(--ink); }
.p-list-sub { font-size: 12.2px; color: var(--muted); margin-top: 2px; }
.p-list-right { text-align: right; flex: 0 0 auto; }

.p-job-card {
  background: var(--card); border: 1px solid var(--line); border-radius: var(--radius);
  padding: 16px 18px; box-shadow: var(--shadow-sm); margin-bottom: 10px;
  transition: transform .18s var(--ease), box-shadow .18s var(--ease), border-color .18s var(--ease);
}
.p-job-card:hover { transform: translateY(-1px); border-color: #DCE1F5; box-shadow: var(--shadow-md); }
.p-job-card-header { display: flex; align-items: center; gap: 12px; }
.p-job-title { font-size: 14.6px; font-weight: 700; color: var(--ink); }
.p-job-company { font-size: 12.6px; color: var(--muted); margin-top: 3px; }
.p-job-info { font-size: 12.4px; color: var(--muted); margin-top: 8px; line-height: 1.7; }
.p-job-icon {
  width: 38px; height: 38px; flex: 0 0 38px; border-radius: 11px;
  background: linear-gradient(135deg, #EEF0FF, #F3EEFF); color: #4F46E5 !important;
  font-size: 17px; line-height: 38px; text-align: center;
}
.p-job-score {
  text-align: center; min-width: 62px; border-radius: 12px;
  background: #F6F7FF; padding: 7px 10px;
}
.p-job-score-num { font-size: 19px; font-weight: 800; color: #4F46E5; font-variant-numeric: tabular-nums; }
.p-job-score-label { font-size: 10.5px; color: var(--faint); }
.p-job-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
.p-search-bar {
  display: flex; gap: 10px; align-items: center;
  background: var(--card); border: 1px solid var(--line); border-radius: 14px;
  padding: 12px 14px; box-shadow: var(--shadow-sm);
}

.p-cta {
  position: relative; overflow: hidden; text-align: center;
  background: linear-gradient(135deg, #4F46E5 0%, #7C5CFC 100%);
  border-radius: var(--radius-lg); padding: 32px 28px; margin-top: 24px;
  box-shadow: 0 22px 46px -28px rgba(79,70,229,.75);
}
.p-cta-title { font-size: 19px; font-weight: 780; color: #FFFFFF; letter-spacing: -.015em; }
.p-cta-desc { font-size: 13.4px; color: rgba(255,255,255,.82); margin-top: 8px; line-height: 1.7; }
.p-cta-btn {
  display: inline-block; margin-top: 18px; background: #FFFFFF; color: #4338CA !important;
  font-size: 13.4px; font-weight: 720; border-radius: 11px; padding: 10px 20px;
  box-shadow: 0 10px 24px -14px rgba(0,0,0,.6);
}

/* ---------------- 响应式 ---------------- */
@media (max-width: 900px) {
  .p-hero { padding: 26px 22px; }
  .p-hero-title { font-size: 24px; }
  .p-hero-stats { gap: 24px; }
  .block-container { padding-left: 14px !important; padding-right: 14px !important; }
}

/* ---------------- 原生控件皮肤（insert 2026-10-19）---------------- */
/* ============================================================
   原生控件皮肤（Streamlit widgets）· 2026-10-19
   与 .p-* 组件同一设计语言：白底 / 11px 圆角 / 靛蓝焦点环
   ============================================================ */
/* —— 文本 / 数字 / 日期 / 多行输入 —— */
div[data-baseweb="input"], div[data-baseweb="textarea"] {
  background: #FFFFFF !important; border: 1px solid var(--line) !important;
  border-radius: 11px !important; box-shadow: none !important;
  transition: border-color .16s var(--ease), box-shadow .16s var(--ease);
}
div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within {
  border-color: var(--primary-300) !important;
  box-shadow: 0 0 0 3.5px rgba(99,102,241,.15) !important;
}
div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea,
[data-testid="stNumberInput"] input, [data-testid="stDateInput"] input {
  color: var(--ink) !important; background: transparent !important;
  font-size: 14px !important; font-weight: 500 !important;
}
div[data-baseweb="input"] input::placeholder, div[data-baseweb="textarea"] textarea::placeholder {
  color: var(--faint) !important;
}

/* —— 下拉选择 / 多选 —— */
div[data-baseweb="select"] > div {
  background: #FFFFFF !important; border: 1px solid var(--line) !important;
  border-radius: 11px !important; box-shadow: none !important; min-height: 42px;
  transition: border-color .16s var(--ease), box-shadow .16s var(--ease);
}
div[data-baseweb="select"] > div:hover { border-color: var(--primary-200) !important; }
div[data-baseweb="select"] > div:focus-within {
  border-color: var(--primary-300) !important;
  box-shadow: 0 0 0 3.5px rgba(99,102,241,.15) !important;
}
div[data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
div[data-baseweb="select"] input { color: var(--ink) !important; font-size: 14px !important; }
span[data-baseweb="tag"] {
  background: var(--primary-50) !important; color: var(--primary-700) !important;
  border: 1px solid #DCE1FF !important; border-radius: 8px !important;
  font-weight: 650 !important; font-size: 12.5px !important;
}
span[data-baseweb="tag"] span { color: var(--primary-700) !important; }
span[data-baseweb="tag"] svg { fill: var(--primary-600) !important; }

/* —— 下拉面板 —— */
div[data-baseweb="popover"] div[role="listbox"], div[data-baseweb="popover"] ul {
  border-radius: 13px !important; border: 1px solid var(--line) !important;
  box-shadow: 0 18px 42px -22px rgba(16,24,40,.34) !important; padding: 5px !important;
}
li[role="option"] { border-radius: 8px !important; }
li[role="option"][aria-selected="true"], li[role="option"]:hover {
  background: var(--primary-50) !important; color: var(--primary-700) !important;
}

/* —— 滑块 —— */
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
  background: var(--primary-600) !important; border: 2.5px solid #FFFFFF !important;
  box-shadow: 0 2px 8px rgba(79,70,229,.42) !important; height: 20px !important;
  width: 20px !important; margin-top: -4px !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] div[data-testid="stSliderThumbValue"],
[data-testid="stSlider"] [data-baseweb="slider"] div[data-testid="stSliderTickBarMin"],
[data-testid="stSlider"] [data-baseweb="slider"] div[data-testid="stSliderTickBarMax"] {
  color: var(--primary-700) !important; font-weight: 650 !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] > div > div:first-child,
[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stSliderTrack"] {
  background: var(--slate-200) !important; height: 6px !important; border-radius: 99px !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] > div > div:first-child > div {
  background: linear-gradient(90deg, var(--primary-500), var(--primary-400)) !important;
  border-radius: 99px !important;
}

/* —— 复选框 / 开关 —— */
[data-baseweb="checkbox"] div[data-checked="true"] {
  background-color: var(--primary-600) !important; border-color: var(--primary-600) !important;
}
[data-baseweb="checkbox"] div[data-checked="true"] svg { fill: #FFFFFF !important; }
[data-baseweb="toggle"] div { background-color: var(--primary-600) !important; }
[data-baseweb="radio"] div[aria-checked="true"], [data-baseweb="radio"] div[data-checked="true"] {
  background-color: var(--primary-600) !important; border-color: var(--primary-600) !important;
}

/* —— 标签页 —— */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: 4px !important; border-bottom: 1px solid var(--line) !important; background: transparent !important;
}
[data-testid="stTab"] {
  height: 40px !important; padding: 0 14px !important; border-radius: 10px 10px 0 0 !important;
  color: var(--muted) !important; font-weight: 600 !important; font-size: 13.6px !important;
}
[data-testid="stTab"]:hover { background: rgba(99,102,241,.06) !important; color: var(--primary-700) !important; }
[data-testid="stTab"][aria-selected="true"] { color: var(--primary-700) !important; background: transparent !important; }
[data-testid="stTabHighlight"], [data-baseweb="tab-highlight"] {
  background: linear-gradient(90deg, var(--primary-500), var(--primary-400)) !important; height: 2.5px !important;
}
[data-baseweb="tab-border"] { background: var(--line) !important; height: 1px !important; }

/* —— 提示条（info / success / warning / error）—— */
[data-testid="stAlertContainer"] {
  border-radius: 13px !important; border: 1px solid var(--line) !important;
  box-shadow: var(--shadow-sm) !important; padding: 13px 16px !important;
}
[data-testid="stAlertContainer"] [data-testid="stMarkdownContainer"] p {
  font-size: 13.4px !important; line-height: 1.7 !important;
}

/* —— 按钮 —— */
[data-testid^="stBaseButton"] {
  border-radius: 11px !important; font-weight: 650 !important; font-size: 13.6px !important;
  transition: transform .16s var(--ease), box-shadow .16s var(--ease), background .16s var(--ease) !important;
}
[data-testid="stBaseButton-secondary"] {
  background: #FFFFFF !important; border: 1px solid var(--line) !important; color: var(--ink) !important;
}
[data-testid="stBaseButton-secondary"]:hover {
  border-color: var(--primary-300) !important; color: var(--primary-700) !important;
  box-shadow: 0 6px 18px -12px rgba(79,70,229,.6) !important;
}

/* —— 表格 / 数据框 —— */
[data-testid="stDataFrame"], [data-testid="stTable"] {
  border: 1px solid var(--line) !important; border-radius: 13px !important; overflow: hidden !important;
  box-shadow: var(--shadow-sm) !important;
}

/* —— 展开器 —— */
[data-testid="stExpander"] details {
  border: 1px solid var(--line) !important; border-radius: 13px !important;
  background: #FFFFFF !important; box-shadow: var(--shadow-sm) !important; overflow: hidden !important;
}
[data-testid="stExpander"] summary { font-weight: 620 !important; font-size: 13.8px !important; }

/* —— 进度条 —— */
[data-testid="stProgress"] > div > div > div {
  background: linear-gradient(90deg, var(--primary-500), var(--primary-400)) !important; border-radius: 99px !important;
}
[data-testid="stProgress"] > div > div { background: var(--slate-200) !important; border-radius: 99px !important; }

/* —— 指标 —— */
[data-testid="stMetric"] {
  background: #FFFFFF !important; border: 1px solid var(--line) !important;
  border-radius: var(--radius) !important; padding: 14px 18px !important; box-shadow: var(--shadow-sm) !important;
}
[data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 780 !important; color: var(--ink) !important; letter-spacing: -.02em !important; }
[data-testid="stMetricLabel"] { color: var(--faint) !important; font-weight: 600 !important; }

/* —— 上传 / 聊天输入 —— */
[data-testid="stFileUploaderDropzone"] {
  border: 1.5px dashed var(--primary-200) !important; border-radius: 14px !important;
  background: linear-gradient(180deg, #FBFBFF, #F7F8FE) !important;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--primary-400) !important; background: var(--primary-50) !important; }
[data-testid="stChatInput"] { border: 1px solid var(--line) !important; border-radius: 14px !important; background: #FFFFFF !important; }

/* ---------------- 提示条配色（去 Streamlit 默认蓝）· 2026-10-19 ---------------- */
[data-baseweb="notification"] {
  border-radius: 13px !important; box-shadow: var(--shadow-sm) !important;
  padding: 13px 16px !important;
}
[data-baseweb="notification"][kind="info"]     { background: #F4F5FF !important; border: 1px solid #E3E6FF !important; }
[data-baseweb="notification"][kind="positive"] { background: #F1FBF5 !important; border: 1px solid #D3F0DE !important; }
[data-baseweb="notification"][kind="warning"]  { background: #FFF9EE !important; border: 1px solid #FBE7C0 !important; }
[data-baseweb="notification"][kind="negative"] { background: #FEF3F2 !important; border: 1px solid #FBDCD8 !important; }
[data-baseweb="notification"] [data-testid="stMarkdownContainer"] p,
[data-baseweb="notification"] [data-testid="stMarkdownContainer"] { color: var(--ink) !important; }

/* ---------------- Hero v2：两栏 + 右侧进度面板 · 2026-10-19 ---------------- */
.p-hero { padding: 34px 38px; }
.p-hero--slim { padding: 22px 28px; margin-bottom: 18px; }
.p-hero--slim .p-hero-title { font-size: 23px; margin-bottom: 6px; }
.p-hero--slim .p-hero-sub { font-size: 13.6px; max-width: 860px; }
.p-hero-grid { display: flex; gap: 38px; align-items: center; }
.p-hero-left { flex: 1 1 auto; min-width: 0; }
.p-hero-right { flex: 0 0 292px; }

.hv-card {
  background: rgba(255,255,255,.74); backdrop-filter: blur(10px);
  border: 1px solid #E6E8F5; border-radius: 18px; padding: 16px 18px 18px;
  box-shadow: 0 26px 54px -36px rgba(28,32,80,.62);
}
.hv-card-head { display: flex; align-items: center; gap: 6px; margin-bottom: 14px; }
.hv-dot { width: 7px; height: 7px; border-radius: 50%; background: #D9DDF0; }
.hv-dot:nth-child(1) { background: #A5B4FC; }
.hv-dot:nth-child(2) { background: #C4B5FD; }
.hv-dot:nth-child(3) { background: #99E3F0; }
.hv-card-title {
  margin-left: 4px; font-size: 11px; font-weight: 750; letter-spacing: .1em;
  text-transform: uppercase; color: #7A8699;
}
.hv-ring {
  position: relative; width: 108px; height: 108px; margin: 2px auto 0; border-radius: 50%;
  background: conic-gradient(#6366F1 calc(var(--pct, 0) * 1%), #E9EBF5 0);
  transition: background .4s var(--ease);
}
.hv-ring::after {
  content: ""; position: absolute; inset: 11px; background: #FFFFFF; border-radius: 50%;
  box-shadow: inset 0 1px 3px rgba(16,24,40,.06);
}
.hv-ring-inner { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; z-index: 1; }
.hv-ring-inner b { font-size: 25px; font-weight: 800; color: #141A2E; letter-spacing: -.02em; }
.hv-ring-inner span { font-size: 12px; font-weight: 700; color: #98A2B3; margin: 8px 0 0 1px; }
.hv-card-foot { text-align: center; font-size: 12px; color: #7A8699; margin-top: 13px; line-height: 1.6; }
.hv-card-foot b { color: var(--primary-700); }

@media (max-width: 1150px) {
  .p-hero-right { display: none; }
  .p-hero-grid { gap: 0; }
}

/* ---------------- 子页页头（.oa-head）升级为卡头 · 2026-10-19 ---------------- */
.oa-head {
  position: relative; overflow: hidden;
  background: #FFFFFF; border: 1px solid var(--line); border-radius: 18px;
  padding: 20px 26px 20px 28px; margin-bottom: 20px;
  box-shadow: 0 18px 40px -34px rgba(28,32,80,.5);
}
.oa-head::before {
  content: ""; position: absolute; left: 0; top: 14px; bottom: 14px; width: 4px;
  border-radius: 0 4px 4px 0;
  background: linear-gradient(180deg, #6366F1, #8B5CF6 58%, #22D3EE);
}
.oa-head::after {
  content: ""; position: absolute; right: -70px; top: -80px; width: 280px; height: 200px;
  background: radial-gradient(closest-side, rgba(99,102,241,.15), transparent 72%);
  pointer-events: none;
}
.oa-head > * { position: relative; }
.oa-head-title { font-size: 21px; font-weight: 730; color: var(--ink); letter-spacing: -.02em; }
.oa-head-sub { font-size: 13px; color: var(--muted); margin-top: 5px; line-height: 1.65; }
</style>
"""


THEMES = {
    "P 产品级（浅色）": CSS_P,
}


# ============================================================
# CSS_V2 · Aurora Pro（2026-10-19 视觉重构层）
# 只做「覆盖」不做「重写」：加载顺序在主题之后，尽量不动既有页面结构。
# ============================================================
CSS_V2 = """<style>
:root {
  --v2-canvas: #F4F5FA;
  --v2-line: #E8EAF3;
  --v2-ink: #0A1024;
  --v2-sub: #5B6478;
  --v2-faint: #8C94A8;
  --v2-brand: #5B5BD6;
  --v2-brand-2: #7C6CF6;
  --v2-cyan: #22D3EE;
  --v2-shadow-1: 0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.03);
  --v2-shadow-2: 0 2px 6px -2px rgba(16,24,40,.06), 0 18px 38px -26px rgba(16,24,40,.42);
  --v2-shadow-3: 0 28px 64px -40px rgba(24,28,72,.55);
}

/* ---------- 画布：一层很淡的极光，不要脏 ---------- */
.stApp {
  background:
    radial-gradient(900px 460px at 12% -8%, rgba(99,102,241,.10), transparent 62%),
    radial-gradient(760px 420px at 88% -12%, rgba(34,211,238,.09), transparent 60%),
    linear-gradient(180deg, #F6F7FC 0%, #F3F4FA 46%, #F5F6FB 100%);
  background-attachment: fixed;
}
.block-container, section.main > div.block-container {
  max-width: 1220px !important;
  padding-top: 2.1rem !important;
  padding-bottom: 4.5rem !important;
}

/* ---------- 排版 ---------- */
html, body, [class*="css"], .stApp {
  font-family: Inter, "SF Pro SC", "PingFang SC", "Hiragino Sans GB",
               "Microsoft YaHei", system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
h1 { font-size: 30px !important; font-weight: 780 !important; letter-spacing: -.028em !important; }
h2 { font-size: 19px !important; font-weight: 720 !important; letter-spacing: -.018em !important; }
h3 { font-size: 16px !important; font-weight: 680 !important; letter-spacing: -.012em !important; }
h4 { font-size: 14.5px !important; font-weight: 680 !important; letter-spacing: -.01em !important; }
p, li { color: #303A52; }

/* ---------- 侧边栏：深色玻璃 + 品牌头 ---------- */
[data-testid="stSidebar"] {
  background:
    radial-gradient(420px 220px at 50% -6%, rgba(99,102,241,.30), transparent 68%),
    linear-gradient(180deg, #0B1022 0%, #0D1330 52%, #090D1E 100%) !important;
  border-right: 1px solid rgba(140,160,255,.10) !important;
  box-shadow: 24px 0 60px -50px rgba(6,10,30,.9);
}
[data-testid="stSidebar"] > div:first-child { padding: 14px 12px 8px !important; }
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: 0 !important; }

.oa-brand {
  display: flex; align-items: center; gap: 11px;
  padding: 12px 10px 16px; margin: 2px 2px 10px;
  border-bottom: 1px solid rgba(140,160,255,.10);
}
.oa-brand-mark {
  width: 36px; height: 36px; border-radius: 11px; flex: 0 0 auto;
  display: flex; align-items: center; justify-content: center;
  font-size: 17px; font-weight: 800; color: #fff; letter-spacing: -.03em;
  background: linear-gradient(140deg, #6D6DF0 0%, #8B5CF6 52%, #22D3EE 128%);
  box-shadow: 0 8px 20px -10px rgba(99,102,241,.95),
              inset 0 1px 0 rgba(255,255,255,.34);
}
.oa-brand-txt { display: flex; flex-direction: column; line-height: 1.25; min-width: 0; }
.oa-brand-name { font-size: 14.5px; font-weight: 720; color: #F4F6FF; letter-spacing: -.01em; }
.oa-brand-sub { font-size: 10.5px; font-weight: 500; color: #7581AC; letter-spacing: .06em; text-transform: uppercase; margin-top: 2px; }

[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] {
  font-size: 10px !important; font-weight: 700 !important;
  letter-spacing: .13em !important; text-transform: uppercase;
  color: #5C6788 !important; padding: 16px 12px 6px !important;
}
[data-testid="stSidebar"] [data-testid="stNavSectionHeader"] * { color: #5C6788 !important; }
[data-testid="stSidebarNavLink"] {
  border-radius: 10px !important;
  padding: 8px 11px !important;
  margin: 1px 0 !important;
  font-size: 13.5px !important;
  font-weight: 560 !important;
  color: #A8B3D4 !important;
  border: 1px solid transparent;
  transition: background .16s ease, color .16s ease, transform .16s ease, border-color .16s ease;
}
[data-testid="stSidebarNavLink"]:hover {
  background: rgba(255,255,255,.055) !important;
  color: #E6EBFF !important;
  transform: translateX(1px);
}
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: linear-gradient(90deg, rgba(99,102,241,.30) 0%, rgba(99,102,241,.10) 60%, rgba(99,102,241,.02) 100%) !important;
  border: 1px solid rgba(129,140,248,.26) !important;
  box-shadow: inset 3px 0 0 0 #818CF8, 0 8px 22px -16px rgba(99,102,241,.9) !important;
  color: #FFFFFF !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"] span,
[data-testid="stSidebarNavLink"][aria-current="page"] p { color: #FFFFFF !important; font-weight: 650 !important; }
[data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] { font-size: 15px !important; opacity: .9; }

.oa-side-stat {
  background: rgba(255,255,255,.045);
  border: 1px solid rgba(140,160,255,.12);
  border-radius: 12px; padding: 11px 13px;
  font-size: 12px; color: #8C99C4 !important; line-height: 1.7;
}
.oa-side-stat b { color: #EDF1FF !important; font-weight: 700; font-size: 13px; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #5F6B90 !important; font-size: 11px !important; }

/* ---------- 卡片：统一升级为“浮起的纸” ---------- */
div[class*="st-key-oa-card"],
.p-card,
div[data-testid="stExpander"] {
  background: #FFFFFF !important;
  border: 1px solid var(--v2-line) !important;
  border-radius: 16px !important;
  box-shadow: var(--v2-shadow-1) !important;
  transition: box-shadow .22s ease, border-color .22s ease, transform .22s ease;
}
div[class*="st-key-oa-card"] { padding: 6px 18px 12px !important; }
div[class*="st-key-oa-card"]:hover,
.p-card:hover { box-shadow: var(--v2-shadow-2) !important; border-color: #DBDFEF !important; }
div[data-testid="stExpander"] summary { padding: 10px 14px !important; }
div[data-testid="stExpander"] summary:hover { background: #FAFBFF; border-radius: 14px; }

/* ---------- 主页 Hero ---------- */
.p-hero, .oa-hero {
  border-radius: 24px !important;
  border: 1px solid rgba(140,160,255,.16) !important;
  background:
    radial-gradient(680px 300px at 8% -20%, rgba(99,102,241,.16), transparent 62%),
    radial-gradient(520px 260px at 92% 0%, rgba(34,211,238,.12), transparent 58%),
    linear-gradient(180deg, #FFFFFF 0%, #FBFCFF 100%) !important;
  box-shadow: var(--v2-shadow-3) !important;
  position: relative;
  overflow: hidden;
}
.p-hero::after {
  content: ""; position: absolute; inset: 0; pointer-events: none;
  background-image: radial-gradient(rgba(20,30,70,.05) 1px, transparent 1px);
  background-size: 18px 18px;
  mask-image: linear-gradient(120deg, #000 0%, transparent 55%);
  -webkit-mask-image: linear-gradient(120deg, #000 0%, transparent 55%);
}
.p-hero-title { font-size: 34px !important; font-weight: 800 !important; letter-spacing: -.035em !important; line-height: 1.16 !important; }
.p-hero-sub { font-size: 14px !important; color: #525C74 !important; line-height: 1.7 !important; }
.p-hero-label {
  font-size: 10.5px !important; letter-spacing: .16em !important;
  font-weight: 750 !important; color: #6D6DF0 !important;
}

/* ---------- 区块标题 ---------- */
.p-sec-title, .oa-sec-title { font-size: 17px !important; font-weight: 740 !important; letter-spacing: -.018em !important; }
.p-sec-action { font-size: 12px !important; color: var(--v2-faint) !important; }

/* ---------- 按钮 ---------- */
.stButton > button, .stDownloadButton > button, .stLinkButton > a {
  border-radius: 10px !important;
  font-weight: 620 !important;
  font-size: 13.5px !important;
  border: 1px solid #E4E7F2 !important;
  background: #FFFFFF !important;
  color: #1A2138 !important;
  box-shadow: var(--v2-shadow-1);
  transition: transform .14s ease, box-shadow .18s ease, border-color .18s ease, background .18s ease;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {
  border-color: #C9CDF6 !important;
  background: #FAFAFF !important;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px -10px rgba(79,70,229,.55);
}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
  background: linear-gradient(135deg, #5F5FE6 0%, #6F5BF0 55%, #7C6CF6 100%) !important;
  border: 1px solid #5A55D8 !important;
  color: #FFFFFF !important;
  box-shadow: 0 10px 24px -14px rgba(93,88,224,.95), inset 0 1px 0 rgba(255,255,255,.22) !important;
}
.stButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #5454DC 0%, #6450E6 100%) !important;
  box-shadow: 0 14px 30px -14px rgba(93,88,224,1) !important;
}

/* ---------- 输入控件 ---------- */
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div,
.stNumberInput input, .stDateInput input {
  border-radius: 10px !important;
  border-color: #E4E7F2 !important;
  background: #FCFCFE !important;
  transition: border-color .16s ease, box-shadow .16s ease, background .16s ease;
  font-size: 13.5px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus,
[data-baseweb="select"] > div:focus-within {
  border-color: #A9AEEC !important;
  background: #FFFFFF !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,.12) !important;
}

/* ---------- 页内跳转链接（st.page_link）做成次级按钮 ---------- */
[data-testid="stPageLink"] a, .stPageLink a {
  display: inline-flex !important; align-items: center; gap: 6px;
  padding: 7px 13px !important; border-radius: 9px !important;
  border: 1px solid #E4E7F2 !important; background: #FFFFFF !important;
  font-size: 12.5px !important; font-weight: 640 !important;
  color: #3B3F82 !important; text-decoration: none !important;
  box-shadow: 0 1px 2px rgba(16,24,40,.04);
  transition: transform .14s ease, box-shadow .18s ease, border-color .18s ease, background .18s ease;
  white-space: nowrap;
}
[data-testid="stPageLink"] a:hover, .stPageLink a:hover {
  border-color: #C9CDF6 !important; background: #FAFAFF !important;
  transform: translateY(-1px);
  box-shadow: 0 6px 16px -10px rgba(79,70,229,.55);
}
[data-testid="stPageLink"] a p, .stPageLink a p { font-size: 12.5px !important; font-weight: 640 !important; color: inherit !important; }
[data-testid="stPageLink"] a [data-testid="stIconMaterial"] { font-size: 15px !important; }

/* ---------- Tabs：胶囊分段 ---------- */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  gap: 4px; border-bottom: none !important;
  background: #EFF1F8; border-radius: 12px; padding: 4px;
  width: fit-content; max-width: 100%;
}
[data-testid="stTabs"] button[role="tab"] {
  border-radius: 9px !important; padding: 7px 15px !important;
  font-size: 13px !important; font-weight: 600 !important;
  color: #5D6680 !important; border: none !important;
  transition: background .16s ease, color .16s ease, box-shadow .16s ease;
}
[data-testid="stTabs"] button[role="tab"]:hover { color: #1B2440 !important; background: rgba(255,255,255,.62) !important; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
  background: #FFFFFF !important; color: #2A2F6B !important;
  box-shadow: 0 2px 6px -2px rgba(16,24,40,.16) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-highlight"], [data-testid="stTabs"] [data-baseweb="tab-border"] { display: none !important; }

/* ---------- 指标 ---------- */
div[data-testid="stMetric"] {
  background: linear-gradient(180deg, #FFFFFF 0%, #FCFCFF 100%) !important;
  border: 1px solid var(--v2-line) !important;
  border-radius: 14px !important;
  padding: 14px 16px !important;
  box-shadow: var(--v2-shadow-1);
  transition: box-shadow .2s ease, transform .2s ease;
}
div[data-testid="stMetric"]:hover { transform: translateY(-1px); box-shadow: var(--v2-shadow-2); }
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
  font-size: 27px !important; font-weight: 760 !important; letter-spacing: -.03em !important;
  background: linear-gradient(135deg, #1A2140 0%, #3B3F82 100%);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
div[data-testid="stMetric"] label p { font-size: 12px !important; color: #6B7488 !important; font-weight: 550 !important; }

/* ---------- 徽章 / 药丸 / 标签 ---------- */
.stBadge, [data-testid="stBadge"] { border-radius: 999px !important; font-weight: 600 !important; }
.stPills button, [data-testid="stPills"] button { border-radius: 999px !important; font-size: 12.5px !important; }

/* ---------- 聊天气泡 ---------- */
[data-testid="stChatMessage"] {
  background: #FFFFFF; border: 1px solid var(--v2-line);
  border-radius: 16px; padding: 12px 16px;
  box-shadow: var(--v2-shadow-1);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
  background: linear-gradient(180deg, #F7F8FF 0%, #F3F5FF 100%);
  border-color: #E4E7FA;
}
[data-testid="stChatInput"] {
  border-radius: 14px !important; border: 1px solid #E2E6F3 !important;
  background: #FFFFFF !important; box-shadow: var(--v2-shadow-2);
}

/* ---------- 分隔线 ---------- */
hr { border-color: #EDEFF7 !important; }

/* ---------- 滚动条 ---------- */
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: #D7DBEA; border-radius: 8px; border: 3px solid transparent; background-clip: padding-box; }
::-webkit-scrollbar-thumb:hover { background: #C2C8DE; background-clip: padding-box; }

/* ---------- 入场动画（只对卡片，克制） ---------- */
@media (prefers-reduced-motion: no-preference) {
  div[class*="st-key-oa-card"], .p-card, .p-hero {
    animation: oa-rise .42s cubic-bezier(.22,.61,.36,1) both;
  }
  @keyframes oa-rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
}

/* ---------- 首页专用 ---------- */
.oa-kpi-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 4px; }
.oa-kpi {
  background: rgba(255,255,255,.72); border: 1px solid rgba(210,216,240,.75);
  border-radius: 14px; padding: 12px 14px; backdrop-filter: blur(6px);
}
.oa-kpi-n { font-size: 24px; font-weight: 780; letter-spacing: -.035em; color: #101733; line-height: 1.1; }
.oa-kpi-l { font-size: 11.5px; color: #6B7488; margin-top: 3px; font-weight: 550; }
.oa-kpi-hl .oa-kpi-n { background: linear-gradient(135deg,#5F5FE6,#8B5CF6); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }

.oa-next {
  display: flex; align-items: center; gap: 16px;
  background: linear-gradient(120deg, #12173A 0%, #1B2050 55%, #232A63 100%);
  border: 1px solid rgba(140,160,255,.22);
  border-radius: 18px; padding: 18px 20px; color: #E9EDFF;
  box-shadow: 0 26px 54px -34px rgba(12,18,60,.95);
  position: relative; overflow: hidden;
}
.oa-next::after {
  content: ""; position: absolute; right: -40px; top: -70px; width: 260px; height: 200px;
  background: radial-gradient(closest-side, rgba(34,211,238,.35), transparent 70%);
}
.oa-next-ico {
  width: 46px; height: 46px; border-radius: 13px; flex: 0 0 auto;
  display: flex; align-items: center; justify-content: center; font-size: 21px;
  background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.16);
}
.oa-next-t { font-size: 15px; font-weight: 720; color: #F6F8FF; letter-spacing: -.01em; }
.oa-next-d { font-size: 12.5px; color: #A9B4DC; margin-top: 3px; }
.oa-next-c { margin-left: auto; font-size: 12.5px; font-weight: 700; color: #8FE9FF; white-space: nowrap; }

.oa-funnel-row { display: flex; align-items: center; gap: 10px; margin: 9px 0; }
.oa-funnel-l { width: 62px; font-size: 12px; color: #5B6478; flex: 0 0 auto; }
.oa-funnel-bar { flex: 1; height: 9px; background: #EFF1F8; border-radius: 999px; overflow: hidden; }
.oa-funnel-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg,#6366F1,#8B5CF6 60%,#22D3EE); }
.oa-funnel-n { width: 30px; text-align: right; font-size: 12.5px; font-weight: 700; color: #1A2140; }

@media (max-width: 900px) {
  .oa-kpi-strip { grid-template-columns: repeat(2, 1fr); }
  .p-hero-title { font-size: 26px !important; }
}
</style>
"""


def get_css(name: str = None) -> str:
    """按名字取样式；名字不认识（含不传）就返回默认主题（THEMES 第一项）。

    末尾统一追加全局卡片样式，保证哪套主题都有统一的卡片观感。
    """
    if name and name in THEMES:
        base = THEMES[name]
    elif name:
        base = next((v for k, v in THEMES.items() if name[0].upper() == k[0]), None)
        base = base or next(iter(THEMES.values()))
    else:
        base = next(iter(THEMES.values()))
    return base + CSS_V2 + CSS_CARDS

# ============================================================
# 统一卡片块（2026-10-19）
# 页面里用 st.container(border=True, key="oa-card-xxx") 就会吃到这套样式；
# Streamlit 会把 key 变成 st-key-oa-card-xxx 这个 class，所以选择器是稳的。
# ============================================================
CSS_CARDS = """
<style>
div[class*="st-key-oa-card"] {
  background: #FFFFFF;
  border: 1px solid var(--line, #E6E9F2);
  border-radius: 16px;
  box-shadow: 0 14px 34px -28px rgba(28,32,80,.55);
  padding: 8px 18px 12px;
}
div[class*="st-key-oa-card"] [data-testid="stVerticalBlock"] { gap: .55rem; }
.oa-card-head {
  display: flex; align-items: center; gap: 8px;
  font-size: 14.5px; font-weight: 700; color: var(--ink, #0B1020);
  letter-spacing: -.01em; padding: 10px 0 2px;
}
.oa-card-sub {
  font-size: 12.5px; color: var(--muted, #7A8699);
  margin: -2px 0 8px; line-height: 1.6;
}
</style>
"""
