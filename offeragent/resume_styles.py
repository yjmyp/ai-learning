# -*- coding: utf-8 -*-
"""
resume_styles · 简历样式层（纯 CSS，不含内容与逻辑）
====================================================
每个模板一段 CSS 常量。新增模板 = 在这里加一段 CSS_DUO 这样的常量，
再到 resume_templates.py 注册表登记 + 写一个渲染函数，内容层不用动。
"""

CSS_CLASSIC = """
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
       color: #1F2328; margin: 0; background: #eceff3; font-size: 13px; line-height: 1.68; }
.page { width: 800px; margin: 18px auto; background: #fff; padding: 42px 50px 34px;
        box-shadow: 0 2px 14px rgba(0,0,0,.12); }
.head { display: flex; gap: 22px; align-items: flex-start; }
.head-main { flex: 1; min-width: 0; }
.photo { flex: 0 0 auto; }
.photo img { width: 104px; height: 140px; object-fit: cover; object-position: center top;
             border: 1px solid #DCE3EC; border-radius: 6px; display: block;
             box-shadow: 0 1px 3px rgba(16,24,40,.10); }
h1 { font-size: 26px; margin: 0 0 7px; letter-spacing: 1px; color: #0F172A; }
.role { display: inline-block; font-size: 12.6px; color: #1D4ED8; font-weight: 700;
        background: #EEF2FF; border-radius: 999px; padding: 2px 11px; margin-bottom: 8px; }
.meta { font-size: 12.5px; color: #4B5563; line-height: 1.8; }
.meta b { color: #111827; }
.links { font-size: 12.5px; color: #1D4ED8; margin-top: 4px; word-break: break-all; }
h2 { font-size: 14px; color: #0F172A; margin: 20px 0 10px; padding-bottom: 5px;
     border-bottom: 1px solid #E5E9F2; letter-spacing: .6px; }
h2::before { content: ''; display: inline-block; width: 4px; height: 13px;
             background: #1D4ED8; border-radius: 2px; margin-right: 8px;
             vertical-align: -1px; }
.proj { margin-bottom: 16px; }
.proj-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.proj-title { font-size: 14px; font-weight: 700; color: #0F172A; }
.proj-date { font-size: 11.5px; color: #6B7280; white-space: nowrap; }
.result { font-size: 12.6px; margin: 5px 0 6px; }
.tech { display: flex; flex-wrap: wrap; gap: 5px; margin: 0 0 6px; }
.chip { font-size: 11px; color: #1D4ED8; background: #F2F5FE; border: 1px solid #E1E8FA;
        border-radius: 5px; padding: 1px 7px; }
ul { margin: 2px 0 0; padding-left: 17px; }
li { margin: 4px 0; }
li::marker { color: #9AA6B8; }
.skills div { margin: 3px 0; }
.skills b { display: inline-block; min-width: 88px; color: #0F172A; }
.note { font-size: 12.2px; color: #4B5563; }
.foot { font-size: 10.5px; color: #9CA3AF; margin-top: 14px; border-top: 1px solid #EEF1F5;
        padding-top: 8px; }
@media print {
  body { background: #fff; font-size: 10.2px; line-height: 1.34; }
  .page { width: auto; margin: 0; box-shadow: none; padding: 0 8mm; }
  h1 { font-size: 20px; margin: 0 0 2px; } .role { font-size: 12px; margin-bottom: 3px; }
  h1 { font-size: 19px; margin: 0 0 2px; } .role { font-size: 11.4px; margin-bottom: 2px; }
  .meta { font-size: 10.1px; line-height: 1.45; } .links { font-size: 10.1px; margin-top: 1px; }
  h2 { font-size: 11.8px; margin: 5px 0 2px; padding-bottom: 1px; }
  .proj { margin-bottom: 3px; }
  .proj-title { font-size: 11.6px; }
  .result { font-size: 10px; margin: 1px 0 2px; }
  .tech { font-size: 9.9px; margin: 1px 0 1px; gap: 3px; }
  ul { padding-left: 12px; } li { margin: 0; }
  .photo img { width: 76px; height: 101px; }
  .foot { margin-top: 3px; padding-top: 3px; }
"""

CSS_SIDEBAR = """
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
       color: #1F2328;
       margin: 0; background: #eceff3; font-size: 12.6px; line-height: 1.6; }
.page { width: 800px; margin: 18px auto; background: #fff; display: flex;
        box-shadow: 0 2px 14px rgba(0,0,0,.12); min-height: 1060px; }
.side { width: 236px; background: #F6F8FC; padding: 32px 20px;
        border-right: 1px solid #E6EBF3; }
.main { flex: 1; padding: 32px 30px 26px; min-width: 0; }
.photo img { width: 120px; height: 158px; object-fit: cover; object-position: center top;
             margin: 0 auto 16px; display: block; background: #fff;
             border: 3px solid #fff; border-radius: 8px;
             box-shadow: 0 2px 8px rgba(16,24,40,.14); }
.side h3 { font-size: 11.5px; color: #1D4ED8; margin: 18px 0 8px; letter-spacing: 1.2px; }
.side h3::after { content: ''; display: block; height: 1px; background: #DCE4F0;
                  margin-top: 6px; }
.side .meta { font-size: 11.6px; color: #3F4756; line-height: 1.78; word-break: break-all; }
.side .meta b { color: #111827; }
.side .skill b { display: block; color: #0F172A; margin-top: 6px; font-weight: 650; }
.side .skill div { margin-bottom: 7px; }
.side ul { padding-left: 15px; margin: 3px 0; }
.side li { margin: 3px 0; font-size: 11.6px; color: #3F4756; }
h1 { font-size: 24px; margin: 0 0 4px; letter-spacing: .8px; color: #0F172A; }
.role { font-size: 13px; color: #1D4ED8; font-weight: 700; margin-bottom: 6px; }
.links { font-size: 11.6px; color: #1D4ED8; word-break: break-all; margin-bottom: 4px; }
h2 { font-size: 13.4px; color: #0F172A; margin: 17px 0 7px; padding-bottom: 4px;
     border-bottom: 1px solid #E5E9F2; letter-spacing: .5px; }
h2::before { content: ''; display: inline-block; width: 4px; height: 12px;
             background: #1D4ED8; border-radius: 2px; margin-right: 7px;
             vertical-align: -1px; }
.proj { margin-bottom: 12px; }
.proj-head { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; }
.proj-title { font-size: 13.2px; font-weight: 700; color: #0F172A; }
.proj-date { font-size: 11.2px; color: #6B7280; white-space: nowrap; }
.result { font-size: 11.6px; margin: 4px 0 5px; }
.tech { display: flex; flex-wrap: wrap; gap: 4px; margin: 0 0 5px; }
.chip { font-size: 10.6px; color: #1D4ED8; background: #F2F5FE; border: 1px solid #E1E8FA;
        border-radius: 5px; padding: 1px 6px; }
ul { margin: 2px 0 0; padding-left: 16px; }
li { margin: 2px 0; }
li::marker { color: #9AA6B8; }
.foot { font-size: 10.4px; color: #9CA3AF; margin-top: 14px; border-top: 1px solid #EEF1F5;
        padding-top: 6px; }
@media print {
  body { background: #fff; font-size: 10.2px; line-height: 1.36; }
  .page { width: auto; margin: 0; box-shadow: none; min-height: 0; }
  .side { width: 168px; padding: 0 10px 0 0; background: #fff;
          border-right: 1px solid #e3e7f0; }
  .main { padding: 0 0 0 12px; }
  h1 { font-size: 18px; margin-bottom: 2px; } .role { font-size: 11px; margin-bottom: 4px; }
  h2 { font-size: 11.6px; margin: 7px 0 3px; padding-bottom: 2px; }
  h2::before { height: 10px; margin-right: 5px; }
  .side h3 { font-size: 10.4px; margin: 9px 0 3px; }
  .side h3::after { margin-top: 3px; }
  .side .meta { font-size: 9.8px; line-height: 1.55; }
  .side li { font-size: 9.8px; margin: 1px 0; }
  .side .skill b { margin-top: 3px; }
  .side .skill div { margin-bottom: 4px; }
  .proj { margin-bottom: 5px; }
  .proj-title { font-size: 11.4px; }
  .result { font-size: 10px; margin: 2px 0 3px; }
  .tech { gap: 3px; margin-bottom: 3px; }
  .chip { font-size: 9.6px; padding: 0 5px; }
  ul { padding-left: 13px; } li { margin: 1px 0; }
  .photo img { width: 76px; height: 100px; margin-bottom: 7px; border-width: 2px; }
  .foot { margin-top: 6px; padding-top: 4px; }
}
"""

CSS_COMPACT = """
* { box-sizing: border-box; }
body { font-family: "SimSun", "Songti SC", "Noto Serif SC", serif; color: #000;
       margin: 0; background: #eee; font-size: 13px; line-height: 1.6; }
.page { width: 800px; margin: 18px auto; background: #fff; padding: 42px 50px 34px;
        box-shadow: 0 2px 12px rgba(0,0,0,.12); }
.head { display: flex; gap: 20px; align-items: flex-start; }
.head-main { flex: 1; min-width: 0; }
.photo { flex: 0 0 auto; }
.photo img { width: 96px; height: 128px; object-fit: cover; object-position: center top;
             border: 1px solid #333; display: block; }
h1 { font-size: 25px; margin: 0 0 5px; letter-spacing: 3px; }
.role { font-size: 13.4px; margin-bottom: 7px; }
.meta { font-size: 12.4px; line-height: 1.72; }
.links { font-size: 12.2px; margin-top: 3px; word-break: break-all; }
h2 { font-size: 13.8px; margin: 17px 0 7px; padding-bottom: 4px;
     border-bottom: 1px solid #000; letter-spacing: 1px; }
.proj { margin-bottom: 12px; }
.proj-head { display: flex; justify-content: space-between; gap: 10px; align-items: baseline; }
.proj-title { font-size: 13.6px; font-weight: 700; }
.proj-date { font-size: 12px; white-space: nowrap; }
.result { font-size: 12.4px; margin: 4px 0; }
.tech { font-size: 11.8px; margin: 2px 0 5px; color: #333; }
.tech .chip { background: none; border: 0; padding: 0; color: #333; font-size: 11.8px; }
.tech .chip + .chip::before { content: ' · '; color: #999; }
ul { margin: 3px 0 0; padding-left: 17px; }
li { margin: 3px 0; }
.skills div { margin: 3px 0; }
.skills b { display: inline-block; min-width: 88px; }
.foot { font-size: 11px; color: #666; margin-top: 14px; border-top: 1px solid #ddd;
        padding-top: 7px; }
@media print {
  body { background: #fff; font-size: 10.1px; line-height: 1.33; }
  .page { width: auto; margin: 0; box-shadow: none; padding: 0 10mm; }
  h1 { font-size: 19px; margin-bottom: 3px; letter-spacing: 2px; }
  h1 { font-size: 18px; margin-bottom: 2px; letter-spacing: 2px; }
  .role { font-size: 11px; margin-bottom: 3px; }
  .meta { font-size: 10px; line-height: 1.42; }
  .links { font-size: 10px; margin-top: 1px; }
  h2 { font-size: 11.6px; margin: 6px 0 3px; padding-bottom: 2px; }
  .proj { margin-bottom: 4px; }
  .proj-title { font-size: 11.4px; }
  .result { font-size: 10px; margin: 1px 0 2px; }
  .tech { font-size: 9.8px; margin-bottom: 2px; }
  ul { padding-left: 13px; } li { margin: 0; }
  .photo img { width: 70px; height: 93px; }
  .foot { margin-top: 4px; padding-top: 3px; }
"""

CSS_TIMELINE = """
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
       color: #2D3748; margin: 0; background: #eceff3; font-size: 13px; line-height: 1.62; }
.page { width: 800px; margin: 18px auto; background: #fff; padding: 44px 52px 34px;
        box-shadow: 0 2px 14px rgba(0,0,0,.12); }
.head { display: flex; gap: 22px; align-items: flex-start; margin-bottom: 10px; }
.head-main { flex: 1; min-width: 0; }
.photo { flex: 0 0 auto; }
.photo img { width: 100px; height: 134px; object-fit: cover; object-position: center top;
             border: 1px solid #E2E8F0; border-radius: 8px; display: block;
             box-shadow: 0 2px 8px rgba(16,24,40,.10); }
h1 { font-size: 27px; margin: 0 0 6px; letter-spacing: 1px; color: #111827; }
.role { display: inline-block; font-size: 12.6px; color: #047857; font-weight: 700;
        background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 999px;
        padding: 2px 11px; margin-bottom: 8px; }
.meta { font-size: 12.4px; color: #4B5563; line-height: 1.8; }
.meta b { color: #111827; }
.links { font-size: 12.4px; color: #047857; margin-top: 4px; word-break: break-all; }
h2 { font-size: 14.5px; color: #111827; margin: 22px 0 12px; letter-spacing: .6px; }
h2::before { content: ''; display: inline-block; width: 5px; height: 14px;
             background: #10B981; border-radius: 2px; margin-right: 9px;
             vertical-align: -1px; }
/* ---- 时间轴 ---- */
.tl { position: relative; padding-left: 26px; }
.tl::before { content: ''; position: absolute; left: 7px; top: 4px; bottom: 4px;
              width: 2px; background: #D1FAE5; border-radius: 2px; }
.tl-item { position: relative; margin-bottom: 15px; }
.tl-item::before { content: ''; position: absolute; left: -26px; top: 5px;
                   width: 12px; height: 12px; border-radius: 50%;
                   background: #10B981; border: 3px solid #D1FAE5; }
.tl-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.tl-title { font-size: 14px; font-weight: 700; color: #111827; }
.tl-date { font-size: 11.5px; color: #6B7280; white-space: nowrap; }
.result { font-size: 12.6px; margin: 5px 0 6px; }
.tech { display: flex; flex-wrap: wrap; gap: 5px; margin: 0 0 6px; }
.chip { font-size: 11px; color: #047857; background: #ECFDF5; border: 1px solid #BBF7D0;
        border-radius: 5px; padding: 1px 7px; }
ul { margin: 2px 0 0; padding-left: 17px; }
li { margin: 3px 0; }
li::marker { color: #9AA6B8; }
.skills div { margin: 3px 0; }
.skills b { display: inline-block; min-width: 88px; color: #111827; }
.note { font-size: 12.2px; color: #4B5563; }
.foot { font-size: 10.5px; color: #9CA3AF; margin-top: 16px; border-top: 1px solid #EEF1F5;
        padding-top: 8px; }
@media print {
  body { background: #fff; font-size: 10.9px; line-height: 1.42; }
  .page { width: auto; margin: 0; box-shadow: none; padding: 0 8mm; }
  h1 { font-size: 20px; margin: 0 0 2px; } .role { font-size: 12px; margin-bottom: 3px; }
  .meta { font-size: 10.6px; line-height: 1.52; } .links { font-size: 10.6px; margin-top: 2px; }
  h2 { font-size: 12.4px; margin: 8px 0 5px; }
  .tl { padding-left: 18px; } .tl::before { left: 5px; }
  .tl-item::before { left: -18px; width: 9px; height: 9px; border-width: 2px; }
  .tl-item { margin-bottom: 6px; }
  .tl-title { font-size: 12.2px; }
  .result { font-size: 10.6px; margin: 2px 0 3px; }
  .tech { font-size: 10.4px; margin: 1px 0 2px; }
  ul { padding-left: 13px; } li { margin: 1px 0; }
  .photo img { width: 80px; height: 107px; }
  .foot { margin-top: 4px; padding-top: 4px; }
}
"""

CSS_BAND = """
* { box-sizing: border-box; }
body { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
       color: #1F2937; margin: 0; background: #E8EDF3; font-size: 13px; line-height: 1.62; }
.page { width: 800px; margin: 18px auto; background: #fff; padding: 0 0 30px;
        box-shadow: 0 2px 14px rgba(0,0,0,.12); }
.band { background: linear-gradient(120deg, #0F172A 0%, #1E3A5F 55%, #2563EB 100%);
        color: #fff; padding: 34px 48px 30px; display: flex; gap: 22px; align-items: center; }
.band-main { flex: 1; min-width: 0; }
.band h1 { font-size: 28px; margin: 0 0 7px; letter-spacing: 1.5px; color: #fff; }
.band .role { display: inline-block; font-size: 12.6px; font-weight: 700;
              background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.35);
              border-radius: 999px; padding: 2px 12px; margin-bottom: 9px; color: #fff; }
.band .meta { font-size: 12.6px; color: #CBD5E1; line-height: 1.8; }
.band .meta b { color: #fff; }
.band .links { font-size: 12.6px; color: #93C5FD; margin-top: 4px; word-break: break-all; }
.photo { flex: 0 0 auto; }
.photo img { width: 96px; height: 128px; object-fit: cover; object-position: center top;
             border: 3px solid #fff; border-radius: 8px; display: block;
             box-shadow: 0 4px 14px rgba(0,0,0,.28); }
.body { padding: 0 48px; }
h2 { font-size: 14px; color: #0F172A; margin: 20px 0 9px; letter-spacing: .6px; }
h2::before { content: ''; display: inline-block; width: 4px; height: 13px;
             background: #2563EB; border-radius: 2px; margin-right: 8px;
             vertical-align: -1px; }
.proj { margin-bottom: 13px; background: #F8FAFC; border: 1px solid #E9EEF5;
        border-left: 3px solid #2563EB; border-radius: 8px; padding: 10px 14px; }
.proj-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.proj-title { font-size: 14px; font-weight: 700; color: #0F172A; }
.proj-date { font-size: 11.5px; color: #6B7280; white-space: nowrap; }
.result { font-size: 12.6px; margin: 6px 0; }
.tech { display: flex; flex-wrap: wrap; gap: 5px; margin: 0 0 6px; }
.chip { font-size: 11px; color: #1E40AF; background: #E0EDFF; border: 1px solid #BFDBFE;
        border-radius: 999px; padding: 1px 9px; }
ul { margin: 2px 0 0; padding-left: 17px; }
li { margin: 3px 0; }
li::marker { color: #9AA6B8; }
.skills div { margin: 3px 0; }
.skills b { display: inline-block; min-width: 88px; color: #0F172A; }
.note { font-size: 12.2px; color: #4B5563; }
.foot { font-size: 10.5px; color: #9CA3AF; margin: 18px 48px 0; border-top: 1px solid #EEF1F5;
        padding-top: 8px; }
@media print {
  body { background: #fff; font-size: 10.8px; line-height: 1.4; }
  .page { width: auto; margin: 0; box-shadow: none; }
  .band { padding: 0 0 10px; background: #fff; color: #000; border-bottom: 2px solid #111; }
  .band h1 { color: #000; font-size: 21px; margin-bottom: 2px; }
  .band .role { background: #fff; border: 1px solid #333; color: #000; font-size: 11px;
                margin-bottom: 3px; }
  .band .meta { color: #333; font-size: 10.4px; line-height: 1.5; }
  .band .meta b { color: #000; }
  .band .links { color: #333; font-size: 10.4px; }
  .body { padding: 0; }
  h2 { font-size: 12.2px; margin: 8px 0 4px; }
  .proj { margin-bottom: 6px; padding: 6px 8px; }
  .proj-title { font-size: 12px; }
  .result { font-size: 10.4px; margin: 3px 0; }
  .tech { margin-bottom: 3px; }
  .chip { font-size: 9.6px; }
  ul { padding-left: 13px; } li { margin: 1px 0; }
  .photo img { width: 72px; height: 96px; border: 1px solid #ccc; }
  .foot { margin: 8px 0 0; padding-top: 4px; }
}
"""

CSS_MODERN = """
* { box-sizing: border-box; }
body { font-family: "Inter", "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
       color: #334155; margin: 0; background: #EEF1F6; font-size: 13px; line-height: 1.6; }
.page { width: 800px; margin: 18px auto; background: #fff; padding: 46px 54px 34px;
        box-shadow: 0 2px 14px rgba(0,0,0,.10); }
.head { display: flex; gap: 22px; align-items: flex-start; margin-bottom: 6px; }
.head-main { flex: 1; min-width: 0; }
.photo { flex: 0 0 auto; }
.photo img { width: 108px; height: 142px; object-fit: cover; object-position: center top;
             border-radius: 12px; display: block; box-shadow: 0 4px 12px rgba(16,24,40,.14); }
h1 { font-size: 32px; margin: 0 0 4px; letter-spacing: .5px; font-weight: 800; color: #0F172A; }
.role { font-size: 13.4px; font-weight: 600; color: #6366F1; margin-bottom: 7px; }
.meta { font-size: 12.4px; color: #475569; line-height: 1.8; }
.meta b { color: #0F172A; }
.links { font-size: 12.4px; color: #6366F1; margin-top: 3px; word-break: break-all; }
h2 { font-size: 13.2px; color: #0F172A; margin: 20px 0 10px; letter-spacing: 1.6px;
     text-transform: uppercase; }
h2::before { content: ''; display: inline-block; width: 22px; height: 3px;
             background: linear-gradient(90deg, #6366F1, #A5B4FC); border-radius: 2px;
             margin-right: 8px; vertical-align: 2px; }
.proj { margin-bottom: 13px; border: 1px solid #E8EDF5; border-radius: 10px;
        padding: 11px 15px; background: #FCFCFF; }
.proj-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.proj-title { font-size: 14px; font-weight: 700; color: #0F172A; }
.proj-date { font-size: 11.5px; color: #94A3B8; white-space: nowrap; }
.result { font-size: 12.6px; margin: 5px 0 6px; }
.tech { display: flex; flex-wrap: wrap; gap: 5px; margin: 0 0 6px; }
.chip { font-size: 10.8px; color: #4F46E5; background: #EEF2FF; border-radius: 6px;
        padding: 2px 8px; font-weight: 600; }
ul { margin: 2px 0 0; padding-left: 17px; }
li { margin: 3px 0; }
li::marker { color: #A5B4FC; }
.skills { display: flex; flex-wrap: wrap; gap: 8px; }
.skills .skill-tag { background: #F1F5F9; border: 1px solid #E2E8F0; border-radius: 999px;
                     padding: 4px 12px; font-size: 12px; color: #334155; }
.skills .skill-tag b { color: #0F172A; }
.skills .skill-tag b::after { content: '：'; color: #94A3B8; font-weight: 400; }
.note { font-size: 12.2px; color: #475569; }
.foot { font-size: 10.5px; color: #9CA3AF; margin-top: 18px; border-top: 1px solid #EEF1F5;
        padding-top: 8px; }
@media print {
  body { background: #fff; font-size: 10.8px; line-height: 1.42; }
  .page { width: auto; margin: 0; box-shadow: none; padding: 0 8mm; }
  h1 { font-size: 22px; margin-bottom: 2px; }
  .role { font-size: 12px; margin-bottom: 3px; }
  .meta { font-size: 10.5px; line-height: 1.52; } .links { font-size: 10.5px; }
  h2 { font-size: 11.4px; margin: 8px 0 4px; }
  .proj { margin-bottom: 6px; padding: 6px 9px; }
  .proj-title { font-size: 12px; }
  .result { font-size: 10.4px; margin: 2px 0 3px; }
  .tech { margin-bottom: 3px; }
  .chip { font-size: 9.4px; }
  ul { padding-left: 13px; } li { margin: 1px 0; }
  .skills { gap: 4px; }
  .skills .skill-tag { padding: 2px 8px; font-size: 9.8px; }
  .photo img { width: 82px; height: 108px; }
  .foot { margin-top: 6px; padding-top: 4px; }
}
"""

# ============================================================
# 新模板：双栏均衡（duo）—— 欧美简历最常见布局
# 左栏 62% 放项目经历（信息主体），右栏 38% 放照片/联系/技能/教育。
# 强调色用青蓝（#0E7490），跟现有模板的蓝/绿/紫区分开。
# ============================================================
CSS_DUO = """
* { box-sizing: border-box; }
body { font-family: "Inter", "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
       color: #1F2937; margin: 0; background: #E9EDF2; font-size: 12.6px; line-height: 1.6; }
.page { width: 800px; margin: 18px auto; background: #fff; display: flex;
        box-shadow: 0 2px 14px rgba(0,0,0,.12); min-height: 1080px; }
.main { flex: 0 0 62%; padding: 36px 26px 28px 36px; min-width: 0; }
.side { flex: 1; background: #F4F7FA; padding: 36px 22px 26px; min-width: 0;
        border-left: 1px solid #E2E8F0; }
.photo { margin-bottom: 14px; }
.photo img { width: 128px; height: 168px; object-fit: cover; object-position: center top;
             border-radius: 10px; display: block; box-shadow: 0 4px 12px rgba(16,24,40,.12); }
h1 { font-size: 28px; margin: 0 0 4px; letter-spacing: .5px; color: #0F172A; }
.role { font-size: 12.8px; font-weight: 600; color: #0E7490; margin-bottom: 8px; }
.main h2 { font-size: 14px; color: #0F172A; margin: 20px 0 9px; letter-spacing: 1.2px;
           text-transform: uppercase; }
.main h2::after { content: ''; display: block; width: 34px; height: 2px;
                  background: #0E7490; margin-top: 4px; }
.side h3 { font-size: 11px; color: #0E7490; margin: 20px 0 7px; letter-spacing: 1.6px;
           text-transform: uppercase; }
.side h3::after { content: ''; display: block; height: 1px; background: #D7E2EC;
                  margin-top: 5px; }
.side .meta { font-size: 11.4px; color: #3F4756; line-height: 1.75; word-break: break-all; }
.side .meta b { color: #111827; }
.side .links { font-size: 11.2px; color: #0E7490; word-break: break-all; margin-bottom: 6px; }
.side ul { padding-left: 14px; margin: 3px 0; }
.side li { margin: 3px 0; font-size: 11.2px; color: #3F4756; }
.side .skill b { display: block; color: #0F172A; margin-top: 7px; font-weight: 650; }
.side .skill div { margin-bottom: 6px; }
.proj { margin-bottom: 14px; }
.proj-head { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.proj-title { font-size: 13.4px; font-weight: 700; color: #0F172A; }
.proj-date { font-size: 11px; color: #6B7280; white-space: nowrap; }
.result { font-size: 12px; margin: 5px 0 6px; }
.tech { display: flex; flex-wrap: wrap; gap: 4px; margin: 0 0 6px; }
.chip { font-size: 10.4px; color: #0E7490; background: #EDF7FA; border: 1px solid #C9E7F0;
        border-radius: 999px; padding: 1px 8px; }
ul { margin: 2px 0 0; padding-left: 16px; }
li { margin: 3px 0; }
li::marker { color: #94A3B8; }
.note { font-size: 11.6px; color: #475569; }
.foot { font-size: 10.2px; color: #9CA3AF; margin: 18px 0 0; border-top: 1px solid #EEF1F5;
        padding-top: 6px; }
@media print {
  body { background: #fff; font-size: 10.4px; line-height: 1.4; }
  .page { width: auto; margin: 0; box-shadow: none; min-height: 0; }
  .main { padding: 0 12px 0 0; }
  .side { padding: 0 0 0 14px; background: #fff; border-left: 1px solid #dde3ec; }
  h1 { font-size: 21px; margin-bottom: 2px; }
  .role { font-size: 11px; margin-bottom: 4px; }
  .main h2 { font-size: 11.8px; margin: 9px 0 4px; }
  .main h2::after { width: 24px; margin-top: 2px; }
  .side h3 { font-size: 9.8px; margin: 11px 0 3px; }
  .side .meta { font-size: 9.6px; line-height: 1.55; }
  .side li { font-size: 9.6px; margin: 1px 0; }
  .side .skill b { margin-top: 4px; }
  .side .skill div { margin-bottom: 4px; }
  .proj { margin-bottom: 6px; }
  .proj-title { font-size: 11.6px; }
  .result { font-size: 10px; margin: 2px 0 3px; }
  .tech { margin-bottom: 3px; }
  .chip { font-size: 9.2px; padding: 0 6px; }
  ul { padding-left: 13px; } li { margin: 1px 0; }
  .photo img { width: 84px; height: 110px; margin-bottom: 6px; }
  .foot { margin: 8px 0 0; padding-top: 4px; }
}
"""
