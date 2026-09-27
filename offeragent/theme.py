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
    "E Night（深色·GitHub 风）": CSS_E,
    "D 精修（浅色·结合版）": CSS_D,
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
