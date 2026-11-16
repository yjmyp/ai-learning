# -*- coding: utf-8 -*-
"""
twin_stage · 3D 数字人舞台（three.js + VRM）
=============================================
- 真 3D 角色，可眨眼、呼吸、点头、说话口型、跟随鼠标转头
- 完全本地渲染：three.js / three-vrm / .vrm 全部 vendored 到 static/，离线可用
- 形象素材：PolygonalMind/100Avatars（CC0），可换成任意 .vrm

用法：
    from twin_stage import stage, STAGE_AVATARS, save_upload
    stage("speaking", name="余剑", caption="AI 应用开发 · 2027 届")
"""
from pathlib import Path

import streamlit as st

_HTML = r"""<div class="oa-stage" data-state="idle">
  <div class="oa-aura"></div>
  <canvas class="oa-canvas"></canvas>
  <div class="oa-grid"></div>
  <div class="oa-vignette"></div>
  <div class="oa-floor"></div>

  <div class="oa-top">
    <div class="oa-chip"><span class="oa-dot"></span><span class="oa-state-text">待机</span></div>
    <div class="oa-chip oa-chip-ghost oa-ver">3D · VRM</div>
  </div>

  <div class="oa-loading"><div class="oa-ring"></div><span class="oa-load-text">正在唤醒数字分身…</span></div>

  <div class="oa-bottom">
    <div class="oa-id">
      <div class="oa-name"></div>
      <div class="oa-cap"></div>
    </div>
    <div class="oa-eq"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
  </div>
</div>"""

_CSS = r"""@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:host { display:block; height:100%; }
*{box-sizing:border-box}
.oa-stage{
  position:relative; width:100%; height:100%; min-height:180px;
  border-radius:22px; overflow:hidden; isolation:isolate;
  background:
    radial-gradient(120% 85% at 50% 8%, #1b2551 0%, #101733 42%, #0a0e1e 72%, #070a14 100%);
  box-shadow: inset 0 0 0 1px rgba(140,160,255,.14), 0 24px 60px -34px rgba(8,12,32,.9);
  font-family: Inter, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  user-select:none;
}
.oa-canvas{position:absolute; inset:0; width:100%; height:100%; display:block; z-index:2}
.oa-aura{
  position:absolute; z-index:0; left:50%; top:8%; width:74%; aspect-ratio:1; translate:-50% 0;
  border-radius:50%; filter:blur(34px); opacity:.85;
  background:
    radial-gradient(circle at 42% 38%, rgba(99,102,241,.55), transparent 62%),
    radial-gradient(circle at 62% 58%, rgba(34,211,238,.32), transparent 62%),
    radial-gradient(circle at 50% 78%, rgba(139,92,246,.30), transparent 66%);
  animation: oa-breathe 7s ease-in-out infinite;
}
@keyframes oa-breathe{0%,100%{opacity:.62; transform:translate(-50%,0) scale(.96)}50%{opacity:.95; transform:translate(-50%,-2%) scale(1.06)}}
.oa-grid{
  position:absolute; inset:0; z-index:1; pointer-events:none; opacity:.5;
  background-image:
    linear-gradient(rgba(120,140,255,.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(120,140,255,.07) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: radial-gradient(80% 70% at 50% 46%, #000 20%, transparent 78%);
  -webkit-mask-image: radial-gradient(80% 70% at 50% 46%, #000 20%, transparent 78%);
}
.oa-vignette{position:absolute; inset:0; z-index:3; pointer-events:none;
  box-shadow: inset 0 -60px 90px -50px rgba(4,6,16,.95), inset 0 0 120px rgba(4,6,16,.55);}
.oa-floor{position:absolute; z-index:3; left:0; right:0; bottom:0; height:46%;
  background:linear-gradient(to top, #070a14 0%, rgba(7,10,20,.94) 30%, rgba(7,10,20,.66) 58%, transparent 100%); pointer-events:none;}

.oa-top{position:absolute; z-index:5; inset:12px 14px auto 14px; display:flex; justify-content:space-between; align-items:center}
.oa-chip{
  display:inline-flex; align-items:center; gap:7px; height:26px; padding:0 11px; border-radius:999px;
  font-size:11.5px; font-weight:600; letter-spacing:.02em; color:#DCE3FF;
  background:rgba(122,140,255,.12); border:1px solid rgba(140,160,255,.22);
  backdrop-filter: blur(8px);
}
.oa-chip-ghost{color:#8E9BC4; background:rgba(255,255,255,.04); border-color:rgba(140,160,255,.12); font-weight:500}
.oa-dot{width:6px;height:6px;border-radius:50%;background:#4ADE80;box-shadow:0 0 0 0 rgba(74,222,128,.6);animation:oa-pulse 2s infinite}
@keyframes oa-pulse{0%{box-shadow:0 0 0 0 rgba(74,222,128,.55)}70%{box-shadow:0 0 0 7px rgba(74,222,128,0)}100%{box-shadow:0 0 0 0 rgba(74,222,128,0)}}
.oa-stage[data-state="thinking"] .oa-dot{background:#FBBF24;box-shadow:0 0 0 0 rgba(251,191,36,.55);animation:oa-pulse-w 1.1s infinite}
@keyframes oa-pulse-w{0%{box-shadow:0 0 0 0 rgba(251,191,36,.5)}70%{box-shadow:0 0 0 7px rgba(251,191,36,0)}100%{box-shadow:0 0 0 0 rgba(251,191,36,0)}}
.oa-stage[data-state="speaking"] .oa-dot{background:#22D3EE;box-shadow:0 0 0 0 rgba(34,211,238,.55);animation:oa-pulse-c .7s infinite}
@keyframes oa-pulse-c{0%{box-shadow:0 0 0 0 rgba(34,211,238,.5)}70%{box-shadow:0 0 0 7px rgba(34,211,238,0)}100%{box-shadow:0 0 0 0 rgba(34,211,238,0)}}

.oa-bottom{position:absolute; z-index:6; left:16px; right:16px; bottom:14px; display:flex; align-items:flex-end; justify-content:space-between; gap:12px}
.oa-name{font-size:15px; font-weight:700; color:#F3F6FF; letter-spacing:-.01em}
.oa-cap{font-size:11.5px; color:#93A0C6; margin-top:3px; line-height:1.45}
.oa-eq{display:flex; align-items:flex-end; gap:3px; height:20px; opacity:0; transition:opacity .25s ease}
.oa-stage[data-state="speaking"] .oa-eq{opacity:1}
.oa-eq i{width:3px; border-radius:2px; background:linear-gradient(180deg,#67E8F9,#818CF8); animation:oa-eq 900ms ease-in-out infinite}
.oa-eq i:nth-child(1){height:30%;animation-delay:0ms}
.oa-eq i:nth-child(2){height:70%;animation-delay:90ms}
.oa-eq i:nth-child(3){height:45%;animation-delay:180ms}
.oa-eq i:nth-child(4){height:95%;animation-delay:60ms}
.oa-eq i:nth-child(5){height:55%;animation-delay:240ms}
.oa-eq i:nth-child(6){height:80%;animation-delay:150ms}
.oa-eq i:nth-child(7){height:38%;animation-delay:300ms}
@keyframes oa-eq{0%,100%{transform:scaleY(.35)}50%{transform:scaleY(1)}}

.oa-loading{position:absolute; z-index:7; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:12px;
  background:radial-gradient(60% 50% at 50% 45%, rgba(20,28,60,.6), rgba(7,10,20,.92)); transition:opacity .5s ease}
.oa-stage[data-ready="1"] .oa-loading{opacity:0; pointer-events:none}
.oa-ring{width:34px;height:34px;border-radius:50%;border:2px solid rgba(140,160,255,.16);border-top-color:#818CF8;animation:oa-spin .9s linear infinite}
@keyframes oa-spin{to{transform:rotate(360deg)}}
.oa-load-text{font-size:11.5px;color:#8E9BC4;letter-spacing:.04em}
"""

_JS = r"""
export default function (component) {
  const { data, parentElement } = component
  const root = parentElement.querySelector(".oa-stage")
  if (!root) return

  const state = (data && data.state) || "idle"
  const label = { idle: "待机", thinking: "思考中", speaking: "说话中", listening: "聆听中" }[state] || "待机"
  root.dataset.state = state
  root.dataset.ready = ""
  const st = root.querySelector(".oa-state-text"); if (st) st.textContent = label
  if (data && data.height) root.style.height = data.height + "px"
  const nm = root.querySelector(".oa-name"); if (nm) nm.textContent = (data && data.name) || ""
  const cp = root.querySelector(".oa-cap"); if (cp) cp.textContent = (data && data.caption) || ""

  root.__state = state
  root.__baseState = state

  // 语音朗读（twin_voice.py）通过 postMessage 通知舞台：朗读期间张嘴，结束恢复原状态。
  // 只挂一次，避免 Streamlit 每次 rerun 重复添加监听器。
  if (!root.__ttsHooked) {
    root.__ttsHooked = true
    window.addEventListener("message", (e) => {
      const d = e && e.data
      if (!d || d.__oa_tts !== true) return
      const next = d.phase === "start" ? "speaking" : (root.__baseState || "idle")
      root.__state = next
      root.dataset.state = next
      const lbl = root.querySelector(".oa-state-text")
      if (lbl) lbl.textContent = { idle: "待机", thinking: "思考中", speaking: "说话中", listening: "聆听中" }[next] || "待机"
    })
  }

  if (root.__booted) return
  root.__booted = true

  const avatar = (data && data.avatar) || "100Avatars_003_Jimmy.vrm"
  const ORIGIN = window.location.origin
  const BASE = ORIGIN + "/app/static/"
  const canvas = root.querySelector(".oa-canvas")
  const loading = root.querySelector(".oa-loading")
  const loadText = root.querySelector(".oa-load-text")

  const fail = (msg) => { if (loadText) loadText.textContent = msg }

  ;(async () => {
    try {
      const THREE = await import(BASE + "vendor/three.module.js")
      const { GLTFLoader } = await import(BASE + "vendor/GLTFLoader.js")
      const { VRMLoaderPlugin, VRMUtils } = await import(BASE + "vendor/three-vrm.module.js")

      const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true })
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
      renderer.outputColorSpace = THREE.SRGBColorSpace

      const scene = new THREE.Scene()
      const camera = new THREE.PerspectiveCamera(24, 1, 0.1, 60)
      camera.position.set(0, 1.50, 2.38)
      camera.lookAt(0, 1.46, 0)

      const key = new THREE.DirectionalLight(0xffffff, 1.35); key.position.set(1.4, 2.6, 2.4); scene.add(key)
      const fill = new THREE.DirectionalLight(0x9DB2FF, 0.55); fill.position.set(-2.4, 1.8, 1.2); scene.add(fill)
      const rim = new THREE.DirectionalLight(0x7C5CFF, 1.05); rim.position.set(-1.6, 2.2, -2.4); scene.add(rim)
      scene.add(new THREE.AmbientLight(0xffffff, 0.85))

      const loader = new GLTFLoader()
      loader.register((p) => new VRMLoaderPlugin(p))

      loader.load(
        BASE + "avatars/" + avatar,
        (gltf) => {
          const vrm = gltf.userData.vrm
          vrm.scene.rotation.y = Math.PI
          try { VRMUtils.rotateVRM0(vrm) } catch (e) {}
          try { VRMUtils.removeUnnecessaryVertices(gltf.scene) } catch (e) {}
          vrm.scene.traverse((o) => { o.frustumCulled = false })
          scene.add(vrm.scene)

          const em = vrm.expressionManager
          const has = (k) => { try { return !!em.getExpression(k) } catch (e) { return false } }
          const visemes = ["aa", "ih", "ou", "ee", "oh"].filter(has)
          const head = vrm.humanoid && vrm.humanoid.getNormalizedBoneNode("head")
          const neck = vrm.humanoid && vrm.humanoid.getNormalizedBoneNode("neck")
          const spine = vrm.humanoid && vrm.humanoid.getNormalizedBoneNode("spine")
          const chest = vrm.humanoid && vrm.humanoid.getNormalizedBoneNode("chest")

          // 把 T-pose 手臂放下来（VRM 默认是 T-pose，直接摆着很出戏）
          const bn = (n) => { try { return vrm.humanoid.getNormalizedBoneNode(n) } catch (e) { return null } }
          const lua = bn("leftUpperArm"), rua = bn("rightUpperArm")
          const lla = bn("leftLowerArm"), rla = bn("rightLowerArm")
          const lh = bn("leftHand"), rh = bn("rightHand")
          if (lua) { lua.rotation.z = 1.16; lua.rotation.x = 0.10 }
          if (rua) { rua.rotation.z = -1.16; rua.rotation.x = 0.10 }
          if (lla) lla.rotation.z = 0.18
          if (rla) rla.rotation.z = -0.18
          if (lh) lh.rotation.z = 0.10
          if (rh) rh.rotation.z = -0.10

          root.dataset.ready = "1"
          if (loading) loading.style.display = "none"

          let t = 0, last = performance.now(), nextBlink = 1.4, blinkT = -99
          let mx = 0, my = 0, tx = 0, ty = 0

          root.addEventListener("pointermove", (e) => {
            const r = root.getBoundingClientRect()
            tx = ((e.clientX - r.left) / r.width) * 2 - 1
            ty = ((e.clientY - r.top) / r.height) * 2 - 1
          })
          root.addEventListener("pointerleave", () => { tx = 0; ty = 0 })

          const resize = () => {
            const w = Math.max(120, root.clientWidth)
            const h = Math.max(140, root.clientHeight)
            renderer.setSize(w, h, false)
            camera.aspect = w / h
            camera.updateProjectionMatrix()
          }
          resize()
          try { new ResizeObserver(resize).observe(root) } catch (e) { window.addEventListener("resize", resize) }

          const lerp = (a, b, k) => a + (b - a) * Math.min(1, k)

          function loop(now) {
            const dt = Math.min(0.05, (now - last) / 1000) || 0.016
            last = now
            t += dt
            const s = root.__state || "idle"

            mx = lerp(mx, tx, 0.06)
            my = lerp(my, ty, 0.06)

            // 眨眼
            if (t > nextBlink && t - blinkT > 0.4) { blinkT = t; nextBlink = t + 2.2 + Math.random() * 3.4 }
            const bt = t - blinkT
            let blink = 0
            if (bt >= 0 && bt < 0.20) blink = bt < 0.07 ? bt / 0.07 : Math.max(0, 1 - (bt - 0.07) / 0.13)
            if (has("blink")) em.setValue("blink", blink)

            // 清除口型
            visemes.forEach((k) => em.setValue(k, 0))

            if (s === "speaking") {
              const env = 0.42 + 0.32 * Math.sin(t * 3.1) + 0.2 * Math.sin(t * 7.7 + 1.3) + 0.12 * Math.sin(t * 13.3)
              const amp = Math.max(0.06, Math.min(1, env))
              const idx = Math.floor(t * 9) % Math.max(1, visemes.length)
              if (visemes.length) em.setValue(visemes[idx], amp)
              if (head) { head.rotation.x = lerp(head.rotation.x, -0.02 + Math.sin(t * 4.2) * 0.03, 0.2) }
              if (chest) chest.rotation.z = Math.sin(t * 1.6) * 0.012
            } else if (s === "thinking") {
              if (head) {
                head.rotation.y = lerp(head.rotation.y, -0.20 + Math.sin(t * 0.7) * 0.05, 0.06)
                head.rotation.x = lerp(head.rotation.x, 0.10 + Math.sin(t * 0.9) * 0.03, 0.06)
                head.rotation.z = lerp(head.rotation.z, 0.05, 0.06)
              }
            } else if (s === "listening") {
              if (head) {
                head.rotation.y = lerp(head.rotation.y, mx * 0.26, 0.08)
                head.rotation.x = lerp(head.rotation.x, my * 0.14 + Math.sin(t * 0.8) * 0.02, 0.08)
                head.rotation.z = 0
              }
            } else {
              // idle：呼吸 + 缓慢扫视 + 跟随鼠标
              if (head) {
                head.rotation.y = lerp(head.rotation.y, mx * 0.34 + Math.sin(t * 0.55) * 0.10, 0.05)
                head.rotation.x = lerp(head.rotation.x, my * 0.16 + Math.sin(t * 0.8) * 0.025, 0.05)
                head.rotation.z = lerp(head.rotation.z, Math.sin(t * 0.42) * 0.02, 0.04)
              }
            }
            if (neck) neck.rotation.x = Math.sin(t * 0.7) * 0.012
            if (spine) {
              spine.rotation.x = Math.sin(t * 0.9) * 0.012
              spine.rotation.z = Math.sin(t * 0.62) * 0.012
            }

            try { vrm.update(dt) } catch (e) {}
            renderer.render(scene, camera)
            requestAnimationFrame(loop)
          }
          requestAnimationFrame(loop)
        },
        (e) => {
          if (e && e.total) fail("正在唤醒数字分身… " + Math.round((e.loaded / e.total) * 100) + "%")
        },
        () => fail("3D 形象加载失败（可换一个形象）")
      )
    } catch (e) {
      fail("3D 引擎加载失败：" + (e && e.message ? e.message : e))
    }
  })()
}
"""

_stage_component = st.components.v2.component(
    "oa_twin_stage",
    html=_HTML,
    css=_CSS,
    js=_JS,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
AVATAR_DIR = STATIC_DIR / "avatars"

# 内置形象（CC0 · PolygonalMind/100Avatars）
STAGE_AVATARS = [
    ("100Avatars_003_Jimmy.vrm", "Jimmy（默认）"),
    ("100Avatars_007_Observer.vrm", "Observer"),
    ("100Avatars_026_Udom.vrm", "Udom"),
    ("100Avatars_018_Retroman.vrm", "Retroman"),
    ("100Avatars_001_Crimsom.vrm", "Crimsom"),
]

DEFAULT_AVATAR = STAGE_AVATARS[0][0]

STATES = ("idle", "thinking", "speaking", "listening")


def available_avatars():
    """内置 + 用户上传（static/avatars/*.vrm）。返回 [(文件名, 展示名)]。"""
    seen = dict(STAGE_AVATARS)
    out = list(STAGE_AVATARS)
    try:
        # 只把「用户自己上传的」列出来，避免把素材包里的怪物形象摆进产品
        for p in sorted(AVATAR_DIR.glob("up_*.vrm")):
            if p.name not in seen:
                out.append((p.name, p.stem[3:]))
    except Exception:
        pass
    return out


def save_upload(file_bytes: bytes, filename: str) -> str:
    """把上传的 .vrm 写进 static/avatars，返回文件名。"""
    import re
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", filename or "avatar.vrm")
    if not safe.lower().endswith(".vrm"):
        safe += ".vrm"
    safe = "up_" + safe
    (AVATAR_DIR / safe).write_bytes(file_bytes)
    return safe


def stage(state: str = "idle", name: str = "数字分身", caption: str = "",
          avatar: str = DEFAULT_AVATAR, height: int = 360, key: str = "oa_twin_stage_view") -> None:
    """渲染 3D 数字人舞台。state: idle / thinking / speaking / listening。"""
    if state not in STATES:
        state = "idle"
    if not avatar or not (AVATAR_DIR / avatar).exists():
        avatar = DEFAULT_AVATAR
    _stage_component(
        key=key,
        data={"state": state, "name": name, "caption": caption, "avatar": avatar, "height": height},
        height=height,
    )
