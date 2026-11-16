# -*- coding: utf-8 -*-
"""
twin_avatar · 数字人虚拟形象（Streamlit Custom Components v2）
==============================================================
一个竖版人像舞台：形象 + 状态徽章 + 说话波形 + 呼吸光晕。两种形态：

  1) 有形象图（data/avatar.png 或 assets/avatar.*）→ 人像卡（推荐，最像虚拟人）
  2) 没有图 → 自绘动画 SVG 虚拟人（会呼吸 / 眨眼 / 说话波形）

想换成真人的照片：把方形或竖版图存成 data/avatar.png 即可，代码不用动。
CCv2 说明（Streamlit >= 1.57）：组件跑在 shadow DOM 里，样式不会漏进 app；
组件只在模块导入时注册一次（重复注册会出怪问题）。
"""
from pathlib import Path

import streamlit as st

_STATES = {"idle": "待机", "thinking": "思考中", "speaking": "说话中"}

_HTML = """
<div class="oa-vh" data-state="idle" data-photo="0">
  <div class="vh-stage">
    <div class="vh-glow"></div>
    <img class="vh-photo" alt="" />
    <svg class="vh-svg" viewBox="0 0 180 220" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="oaHead" x1="0.1" y1="0" x2="0.9" y2="1">
          <stop offset="0%" stop-color="#6366F1"/>
          <stop offset="55%" stop-color="#8B5CF6"/>
          <stop offset="100%" stop-color="#22D3EE"/>
        </linearGradient>
        <radialGradient id="oaHalo" cx="50%" cy="50%" r="50%">
          <stop offset="55%" stop-color="rgba(99,102,241,0)"/>
          <stop offset="82%" stop-color="rgba(99,102,241,.30)"/>
          <stop offset="100%" stop-color="rgba(34,211,238,0)"/>
        </radialGradient>
        <clipPath id="oaFaceClip">
          <rect x="50" y="44" width="80" height="92" rx="40"/>
        </clipPath>
      </defs>

      <circle class="vh-halo" cx="90" cy="90" r="76" fill="url(#oaHalo)"/>
      <circle class="vh-think" cx="90" cy="90" r="84" fill="none"/>

      <g class="vh-bust">
        <path class="vh-shoulder" d="M34 218 C 42 172 62 152 90 152 C 118 152 138 172 146 218 Z"
              fill="url(#oaHead)" opacity=".93"/>
        <path d="M78 164 h24" stroke="#FFFFFF" stroke-width="3" stroke-linecap="round" opacity=".35"/>
      </g>

      <g class="vh-head">
        <rect x="90" y="132" width="20" height="22" rx="9" fill="url(#oaHead)" opacity=".7"/>
        <rect x="50" y="44" width="80" height="92" rx="40" fill="url(#oaHead)"/>
        <g clip-path="url(#oaFaceClip)">
          <rect class="vh-shine" x="40" y="30" width="26" height="130" rx="13"/>
        </g>
        <rect x="60" y="72" width="60" height="44" rx="17" fill="rgba(9,12,26,.86)"/>

        <g class="vh-eyes">
          <rect class="vh-eye" x="73" y="87" width="12" height="7" rx="3.5" fill="#E8EBFF"/>
          <rect class="vh-eye" x="95" y="87" width="12" height="7" rx="3.5" fill="#E8EBFF"/>
        </g>

        <g class="vh-mouth">
          <rect x="76" y="104" width="3.4" height="7" rx="1.7"/>
          <rect x="82" y="104" width="3.4" height="7" rx="1.7"/>
          <rect x="88" y="104" width="3.4" height="7" rx="1.7"/>
          <rect x="94" y="104" width="3.4" height="7" rx="1.7"/>
          <rect x="100" y="104" width="3.4" height="7" rx="1.7"/>
        </g>
      </g>
    </svg>
    <div class="vh-ring"></div>
    <div class="vh-badge"><span class="vh-dot"></span><span class="vh-state-text">待机</span></div>
    <div class="vh-eq"><i></i><i></i><i></i><i></i><i></i></div>
  </div>
  <div class="vh-name"></div>
  <div class="vh-cap"></div>
</div>
"""

_CSS = """
:host {
  --brand1: #6366F1; --brand2: #8B5CF6; --brand3: #22D3EE;
  --vh-w: 178px; --vh-h: 216px;
}
.oa-vh {
  display: flex; flex-direction: column; align-items: center;
  padding: 2px 6px 4px; font-family: Inter, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}
.oa-vh .vh-stage {
  position: relative; width: var(--vh-w); height: var(--vh-h);
  display: flex; align-items: center; justify-content: center;
}
.oa-vh .vh-glow {
  position: absolute; inset: -16px; border-radius: 34px;
  background:
    radial-gradient(58% 58% at 50% 38%, rgba(99,102,241,.38), rgba(139,92,246,.16) 56%, rgba(34,211,238,0) 80%),
    radial-gradient(40% 40% at 78% 78%, rgba(34,211,238,.22), rgba(34,211,238,0) 72%);
  filter: blur(10px); animation: vhPulse 5s ease-in-out infinite;
}
.oa-vh .vh-photo {
  position: relative; width: 100%; height: 100%; object-fit: cover; object-position: 50% 18%;
  border-radius: 26px; border: 2px solid rgba(255,255,255,.88);
  box-shadow: 0 24px 48px -24px rgba(30,34,90,.62);
  animation: vhBreath 6.4s ease-in-out infinite;
}
.oa-vh[data-photo="0"] .vh-photo { display: none; }
.oa-vh[data-photo="1"] .vh-svg { display: none; }
.oa-vh .vh-svg { position: relative; width: 100%; height: 100%; display: block; }
.oa-vh .vh-ring {
  position: absolute; inset: -8px; border-radius: 32px; pointer-events: none;
  border: 2px solid rgba(34,211,238,.0); opacity: 0;
  transition: opacity .35s ease, border-color .35s ease;
}
.oa-vh .vh-halo { animation: vhSpin 26s linear infinite; transform-origin: 90px 90px; }
.oa-vh .vh-think {
  stroke: url(#oaHead); stroke-width: 2.4; stroke-linecap: round;
  stroke-dasharray: 30 64; opacity: 0;
  animation: vhSpin 3.4s linear infinite; transform-origin: 90px 90px;
}
.oa-vh .vh-head { animation: vhBreath 4.8s ease-in-out infinite; transform-origin: 90px 138px; }
.oa-vh .vh-shine { fill: rgba(255,255,255,.32); opacity: .9; }
.oa-vh .vh-eye { transform-origin: 50% 50%; animation: vhBlink 6.4s infinite; }
.oa-vh .vh-mouth rect { fill: #E8EBFF; opacity: .45; transform-box: fill-box; transform-origin: 50% 50%; }

.oa-vh .vh-badge {
  position: absolute; left: 50%; bottom: -11px; transform: translateX(-50%);
  display: inline-flex; align-items: center; gap: 6px; white-space: nowrap;
  background: rgba(255,255,255,.96); border: 1px solid rgba(99,102,241,.28);
  border-radius: 999px; padding: 4px 12px;
  font-size: 11.5px; font-weight: 650; color: #4338CA;
  box-shadow: 0 8px 20px -10px rgba(30,34,90,.5);
  transition: background .3s, border-color .3s, color .3s;
}
.oa-vh .vh-dot {
  width: 6px; height: 6px; border-radius: 50%; background: #6366F1;
  animation: vhBlinkDot 1.8s ease-in-out infinite;
}
.oa-vh .vh-eq {
  position: absolute; left: 50%; bottom: 12px; transform: translateX(-50%);
  display: flex; align-items: flex-end; gap: 4px; height: 22px;
  opacity: 0; transition: opacity .25s ease;
}
.oa-vh .vh-eq i {
  width: 4px; height: 8px; border-radius: 3px; background: rgba(255,255,255,.92);
  box-shadow: 0 2px 8px rgba(20,24,60,.45);
}
.oa-vh .vh-name {
  margin-top: 20px; font-size: 15px; font-weight: 720; color: #0B1020; letter-spacing: -.01em;
}
.oa-vh .vh-cap { margin-top: 3px; font-size: 12px; color: #7A8699; }

@keyframes vhBreath {
  0%, 100% { transform: scale(1) translateY(0); }
  50%      { transform: scale(1.016) translateY(-1.6px); }
}
@keyframes vhBlink {
  0%, 91%, 100% { transform: scaleY(1); }
  94%           { transform: scaleY(.12); }
}
@keyframes vhSpin { to { transform: rotate(360deg); } }
@keyframes vhPulse {
  0%, 100% { opacity: .72; transform: scale(1); }
  50%      { opacity: 1; transform: scale(1.05); }
}
@keyframes vhBlinkDot {
  0%, 100% { opacity: 1; } 50% { opacity: .25; }
}
@keyframes vhSpeak {
  0%, 100% { transform: scaleY(.35); }
  50%      { transform: scaleY(1.9); }
}
@keyframes vhRing {
  0%, 100% { opacity: .55; } 50% { opacity: 1; }
}

/* ---- 思考中 ---- */
.oa-vh[data-state="thinking"] .vh-think { opacity: 1; }
.oa-vh[data-state="thinking"] .vh-glow { animation-duration: 1.9s; }
.oa-vh[data-state="thinking"] .vh-ring {
  opacity: 1; border-color: rgba(34,211,238,.75); animation: vhRing 1.2s ease-in-out infinite;
}
.oa-vh[data-state="thinking"] .vh-badge {
  background: rgba(236,254,255,.97); border-color: rgba(34,211,238,.45); color: #0E7490;
}
.oa-vh[data-state="thinking"] .vh-dot { background: #22D3EE; }

/* ---- 说话中 ---- */
.oa-vh[data-state="speaking"] .vh-mouth rect {
  opacity: 1; animation: vhSpeak .42s ease-in-out infinite;
}
.oa-vh[data-state="speaking"] .vh-mouth rect:nth-child(2) { animation-delay: .07s; }
.oa-vh[data-state="speaking"] .vh-mouth rect:nth-child(3) { animation-delay: .14s; }
.oa-vh[data-state="speaking"] .vh-mouth rect:nth-child(4) { animation-delay: .21s; }
.oa-vh[data-state="speaking"] .vh-mouth rect:nth-child(5) { animation-delay: .28s; }
.oa-vh[data-state="speaking"] .vh-eq { opacity: 1; }
.oa-vh[data-state="speaking"] .vh-eq i { animation: vhSpeak .5s ease-in-out infinite; }
.oa-vh[data-state="speaking"] .vh-eq i:nth-child(2) { animation-delay: .08s; }
.oa-vh[data-state="speaking"] .vh-eq i:nth-child(3) { animation-delay: .16s; }
.oa-vh[data-state="speaking"] .vh-eq i:nth-child(4) { animation-delay: .24s; }
.oa-vh[data-state="speaking"] .vh-eq i:nth-child(5) { animation-delay: .32s; }
.oa-vh[data-state="speaking"] .vh-glow { animation-duration: 2.4s; }
.oa-vh[data-state="speaking"] .vh-ring {
  opacity: 1; border-color: rgba(16,185,129,.7); animation: vhRing 1.6s ease-in-out infinite;
}
.oa-vh[data-state="speaking"] .vh-badge {
  background: rgba(236,253,245,.97); border-color: rgba(16,185,129,.45); color: #047857;
}
.oa-vh[data-state="speaking"] .vh-dot { background: #10B981; }

@media (prefers-reduced-motion: reduce) {
  .oa-vh * { animation: none !important; }
}
"""

_JS = """
export default function (component) {
  const { data, parentElement } = component
  const root = parentElement.querySelector(".oa-vh")
  if (!root) return

  const state = (data && data.state) || "idle"
  root.dataset.state = state

  const photo = root.querySelector(".vh-photo")
  const img = (data && data.image) || ""
  if (photo) {
    if (img) { photo.src = img; root.dataset.photo = "1" }
    else { root.dataset.photo = "0"; photo.removeAttribute("src") }
  }
  root.querySelector(".vh-name").textContent = (data && data.name) || ""
  root.querySelector(".vh-cap").textContent = (data && data.caption) || ""
  root.querySelector(".vh-state-text").textContent =
    state === "speaking" ? "说话中" : state === "thinking" ? "思考中" : "待机"

  // 说话状态 6 秒后在客户端自行回落，避免"永远在说话"
  if (root._vhTimer) { clearTimeout(root._vhTimer); root._vhTimer = null }
  if (state === "speaking") {
    root._vhTimer = setTimeout(function () {
      root.dataset.state = "idle"
      root.querySelector(".vh-state-text").textContent = "待机"
    }, 6000)
  }

  return function cleanup() {
    if (root._vhTimer) { clearTimeout(root._vhTimer); root._vhTimer = null }
  }
}
"""

_virtual_human = st.components.v2.component(
    "oa_virtual_human",
    html=_HTML,
    css=_CSS,
    js=_JS,
)


# twin_avatar.* 是数字分身专用形象（放 assets/ 会进仓库，云端也有）；
# avatar.* 是“本人照片”槽位，两者建议不要混。
PHOTO_CANDIDATES = ["twin_avatar.png", "twin_avatar.jpg", "twin_avatar.jpeg",
                    "twin_avatar.webp", "avatar.png", "avatar.jpg",
                    "avatar.jpeg", "avatar.webp"]


def load_photo(data_dir=None) -> str:
    """有形象图就转成 data URI 给前端；找不到返回空串（前端自动退回 SVG 版）。

    找图顺序：data/avatar.* → assets/avatar.*
    """
    import base64
    here = Path(__file__).parent
    bases = [Path(data_dir) if data_dir else (here / "data"), here / "assets"]
    for base in bases:
        for nm in PHOTO_CANDIDATES:
            p = base / nm
            if not p.exists() or not p.is_file():
                continue
            try:
                b = p.read_bytes()
                if len(b) > 3_500_000:
                    continue
                suf = p.suffix.lower()
                mime = "image/png" if suf == ".png" else (
                    "image/webp" if suf == ".webp" else "image/jpeg")
                return f"data:{mime};base64," + base64.b64encode(b).decode("ascii")
            except Exception:
                continue
    return ""


def virtual_human(state: str = "idle", name: str = "数字分身",
                  caption: str = "", height: int = 300, photo: str = None) -> None:
    """渲染虚拟人形象。state: idle / thinking / speaking。"""
    st_val = state if state in _STATES else "idle"
    if photo is None:
        photo = load_photo()
    _virtual_human(
        key="oa_twin_avatar",
        data={"state": st_val, "name": name, "caption": caption, "image": photo},
        height=height,
    )
