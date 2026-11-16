# -*- coding: utf-8 -*-
"""数字分身的语音：**服务端合成 WAV + 原生播放器**，不再依赖浏览器 TTS。

为什么换掉 Web SpeechSynthesis（2026-10-20 实测无声）：
  · 浏览器语音合成在 iframe / 无用户手势 / 系统没装中文语音时会被静默拦截，
    页面上看起来"点了没反应"，而且没有任何报错可查；
  · 现在改成 Windows 自带 System.Speech 在服务端生成 WAV，再交给 <audio> 播放：
    不依赖浏览器语音引擎、能拿到真实音频时长、口型可以和播放事件严格同步；
  · 生成的 WAV 落在 static/tts/，按文本哈希缓存，同一句话只合成一次。

局限：音色是 Windows 自带中文语音（Huihui/Yaoyao/Kangkang），机械感仍在；
      要更自然需要接云端 TTS（火山/阿里/微软），这里刻意不引密钥。
"""
import hashlib
import html
import json
import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
TTS_DIR = BASE_DIR / "static" / "tts"
TTS_DIR.mkdir(parents=True, exist_ok=True)
MAX_CHARS = 4000
MAX_FILES = 40
DEFAULT_VOICE = os.environ.get("OA_TTS_VOICE", "").strip()


def _cleanup() -> None:
    """只保留最近 40 个 WAV，避免静态目录无限长大。"""
    try:
        files = sorted(TTS_DIR.glob("tts_*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
        for p in files[MAX_FILES:]:
            p.unlink(missing_ok=True)
        for p in TTS_DIR.glob("player_*.html"):
            try:
                if not (TTS_DIR / (p.stem[7:] + ".wav")).exists():
                    p.unlink(missing_ok=True)
            except Exception:
                pass
    except Exception:
        pass


@lru_cache(maxsize=1)
def voices() -> tuple:
    """列出本机可用的中文语音（SAPI）。取不到时给一个空元组。"""
    if sys.platform != "win32":
        return ()
    script = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.GetInstalledVoices() | ForEach-Object {
  if ($_.VoiceInfo.Culture.Name -like 'zh*') { $_.VoiceInfo.Name }
}
$s.Dispose()
"""
    try:
        flags = 0x08000000
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                           timeout=20, creationflags=flags, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        out = tuple(x.strip() for x in (r.stdout or "").splitlines() if x.strip())
        return out
    except Exception:
        return ()


def _hash(text: str, voice: str, rate: int) -> str:
    return hashlib.sha1(f"{voice}|{rate}|{text}".encode("utf-8")).hexdigest()[:16]


def synth(text: str, voice: str = "", rate: int = 0) -> Path | None:
    """把文本合成为 WAV，返回文件路径；失败返回 None（绝不抛异常）。"""
    if sys.platform != "win32":
        return None
    text = (text or "").strip()
    if not text:
        return None
    text = text[:MAX_CHARS]
    voice = (voice or DEFAULT_VOICE or "").strip()
    rate = max(-5, min(5, int(rate or 0)))
    out = TTS_DIR / f"tts_{_hash(text, voice, rate)}.wav"
    if out.exists() and out.stat().st_size > 1024:
        return out

    script = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
  if ($env:OA_TTS_VOICE) { $s.SelectVoice($env:OA_TTS_VOICE) }
} catch { }
$s.Rate = [int]$env:OA_TTS_RATE
$s.SetOutputToWaveFile($env:OA_TTS_OUT)
$s.Speak($env:OA_TTS_TEXT)
$s.Dispose()
"""
    env = dict(os.environ)
    env.update({"OA_TTS_TEXT": text, "OA_TTS_VOICE": voice,
                "OA_TTS_RATE": str(rate), "OA_TTS_OUT": str(out)})
    try:
        flags = 0x08000000 if sys.platform == "win32" else 0   # CREATE_NO_WINDOW
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                       env=env, timeout=45, creationflags=flags, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    try:
        if out.exists() and out.stat().st_size > 1024:
            _cleanup()
            return out
    except Exception:
        pass
    return None


def _stage_message(phase: str) -> str:
    return f'window.parent.postMessage({{__oa_tts:true, phase:"{phase}"}}, "*");'


def player(text: str, label: str = "🔊 朗读这条回答", height: int = 78,
           voice: str = "", rate: int = 0, autoplay: bool = False,
           compact: bool = False) -> None:
    """渲染一个原生音频播放器；播放/暂停/结束会同步 3D 舞台的口型状态。

    compact=True 用于窄侧栏：省略标签，按钮和播放条自动换行。
    """
    text = (text or "").strip()
    if not text:
        return
    wav = synth(text, voice=voice, rate=rate)
    if wav is None:
        st.caption("🔇 本机语音合成不可用（需要 Windows 中文语音）。不影响文字回答。")
        return
    safe_label = html.escape(label)
    page = TTS_DIR / f"player_{wav.stem}{'_auto' if autoplay else ''}{'_c' if compact else ''}.html"
    pad = "6px 8px" if compact else "9px 12px"
    gap = "6px" if compact else "12px"
    btn_pad = "6px 10px" if compact else "8px 16px"
    label_html = "" if compact else (
        f'<span style="font-size:12.5px;color:#475569;white-space:nowrap">{safe_label}</span>')
    page_text = f"""
<div id="oa-wrap" style="display:flex;align-items:center;flex-wrap:{'wrap' if compact else 'nowrap'};gap:{gap};
     font:13px/1.4 system-ui,sans-serif;color:#475569;background:#f8fafc;border:1px solid #e2e8f0;
     border-radius:12px;padding:{pad}">
  {label_html}
  <button id="oa-play" style="border:1px solid #a5b4fc;background:#6366f1;color:#fff;
          border-radius:9px;padding:{btn_pad};font-size:13px;font-weight:600;cursor:pointer;
          box-shadow:0 2px 6px rgba(99,102,241,.25);white-space:nowrap">▶ 播放</button>
  <audio id="oa-audio" controls preload="auto" src="{wav.name}"{' autoplay' if autoplay else ''}
         style="height:34px;max-width:360px;flex:1 1 140px;min-width:110px"></audio>
  <span id="oa-state" style="font-size:12px;color:#64748b;white-space:nowrap"></span>
</div>
<script>
(function() {{
  const a = document.getElementById("oa-audio");
  const btn = document.getElementById("oa-play");
  const st = document.getElementById("oa-state");
  const wrap = document.getElementById("oa-wrap");
  if (!a) return;
  a.volume = 1;
  const tell = (phase) => {{ try {{ window.parent.postMessage({{__oa_tts:true, phase:phase}}, "*"); }} catch (e) {{}} }};
  const play = () => a.play().catch(e => {{ st.textContent = "播放失败，请再点一次"; }});
  a.addEventListener("play", () => {{ st.textContent = "朗读中…"; btn.textContent = "⏸ 暂停"; tell("start"); }});
  a.addEventListener("pause", () => {{ st.textContent = ""; btn.textContent = "▶ 播放"; tell("end"); }});
  a.addEventListener("ended", () => {{ st.textContent = ""; btn.textContent = "▶ 播放"; tell("end"); }});
  a.addEventListener("error", () => {{ st.textContent = "音频加载失败"; tell("end"); }});
  if (btn) btn.addEventListener("click", () => {{ if (a.paused) play(); else a.pause(); }});
  if (wrap) wrap.addEventListener("click", (e) => {{
    if (e.target === a || a.contains(e.target) || e.target === btn) return;
    if (a.paused) play();
  }});
  if (autoplay) {{
    setTimeout(() => {{ a.play().catch(() => {{ st.textContent = "浏览器拦截了自动播放，点 ▶ 播放"; }}); }}, 150);
  }}
}})();
</script>
    """
    if not page.exists() or page.read_text(encoding="utf-8") != page_text:
        page.write_text(page_text, encoding="utf-8")
    st.iframe(f"/app/static/tts/{page.name}", height=height)


def _declare_voice_input(path: Path | None = None):
    """注册语音组件；附件缺失时只禁用语音，不让整站 import 失败。"""
    component_path = path or (BASE_DIR / "static" / "voice_input")
    if not component_path.is_dir():
        return None, f"语音组件目录不存在：{component_path}"
    try:
        component = st.components.v1.declare_component(
            "oa_voice_input", path=str(component_path)
        )
        return component, ""
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


_voice_input, _VOICE_INPUT_ERROR = _declare_voice_input()


def listen(key: str = "oa_voice_input") -> dict:
    """渲染麦克风按钮。返回 {"text", "ts"}；未说话时返回 {}。

    识别在浏览器里做（Edge/Chrome 的 Web Speech API），识别完把文本回传给
    Streamlit，页面再把它当成一次提问。不需要额外的 STT 服务/密钥。
    """
    if _voice_input is None:
        st.caption("🎙️ 语音输入组件不可用，可直接输入文字（不影响其他功能）。")
        return {}
    try:
        val = _voice_input(key=key, default=None, height=48)
        return val if isinstance(val, dict) else {}
    except Exception:
        st.caption("🎙️ 语音输入暂时不可用，可直接输入文字（不影响其他功能）。")
        return {}
