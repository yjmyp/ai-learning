# -*- coding: utf-8 -*-
"""
browser_fetch · 用真实浏览器抓页面（Chrome DevTools Protocol）
==============================================================
为什么需要它：BOSS 直聘、部分招聘站是强反爬 + 需要登录。
直接 requests 抓只能拿到 9KB 的拦截页。

做法：启动一个**独立的 Edge 窗口**（带调试端口、独立用户目录），
用它当"浏览器替身"：你在这个窗口里登录一次，之后程序就能复用登录态读页面。

  python -m browser_fetch --setup      # 第一次：打开窗口让你登录
  from browser_fetch import fetch_html # 程序里用：打开 URL 拿渲染后的 HTML

不绕过验证码、不做指纹伪装、不做多账号。只是复用你自己已经登录的浏览器。
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests
import websocket  # websocket-client

try:
    import winreg          # 只有 Windows 有；用来读 Edge 的安装路径
except ImportError:        # pragma: no cover
    winreg = None

HERE = Path(__file__).parent
PROFILE_DIR = HERE / "data" / "edge_profile"
DEBUG_PORT = 9333

# 允许用环境变量直接指定浏览器（装在不常见位置时的兜底）
BROWSER_ENV = ("EDGE_PATH", "BROWSER_PATH", "CHROME_PATH")


def edge_candidates() -> list:
    """按可靠性排序列出可能的浏览器路径：环境变量 → 注册表 → 常见安装位置 → PATH。"""
    out = []
    for env in BROWSER_ENV:
        v = os.environ.get(env)
        if v:
            out.append(v)
    out += [
        # Edge 正式版（三处常见位置）
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe",
        # Edge 预览通道
        r"C:\Program Files (x86)\Microsoft\Edge Beta\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge Dev\Application\msedge.exe",
        # Chrome 兜底（同样是 Chromium，CDP 一样能用）
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe",
        # macOS
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for name in ("msedge", "msedge.exe", "google-chrome", "chromium",
                 "chromium-browser", "chrome"):
        p = shutil.which(name)
        if p:
            out.append(p)
    return [os.path.expandvars(p) for p in out]


def _registry_edge():
    """从注册表读 Edge 安装路径——装在非默认盘时，这里通常也能找到。"""
    if winreg is None:
        return None
    sub = (r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
           r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe")
    for key in sub:
        for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(hive, key) as k:
                    val = winreg.QueryValue(k, None)
                if val and Path(str(val)).exists():
                    return str(val)
            except OSError:
                continue
    return None


def no_browser_message() -> str:
    checked = "\n".join(f"  · {p}" for p in edge_candidates()[:10])
    return ("没找到 Edge / Chrome。BOSS 直聘是强反爬站，只能借用你本机已经登录的浏览器，"
            "所以这一步必须有一个桌面浏览器。\n已找过这些位置：\n"
            + checked +
            "\n办法：① 装一个 Edge（或 Chrome）后重试；"
            "② 或者设环境变量 EDGE_PATH=浏览器 exe 的完整路径；"
            "③ 只想搜岗位的话，把来源换成「牛客」或「实习僧」——它们不需要浏览器。")


def edge_path() -> str:
    """返回可用的 Chromium 系浏览器路径（Edge 优先，找不到退到 Chrome）。"""
    for env in BROWSER_ENV:                  # 环境变量优先级最高
        v = os.environ.get(env)
        if v:
            try:
                if Path(v).exists():
                    return v
            except Exception:
                continue
    reg = _registry_edge()
    if reg:
        return reg
    for p in edge_candidates():
        try:
            if p and Path(p).exists():
                return p
        except Exception:
            continue
    raise RuntimeError(no_browser_message())


def desktop_available() -> tuple:
    """返回 (能不能抓,BOSS 的理由)。

    云端（Linux 容器）根本没有桌面浏览器，所以这里先给一个说人话的理由，
    而不是让用户对着「没找到 Edge」发呆。
    """
    if sys.platform not in ("win32", "darwin"):
        return False, ("BOSS 抓取只在你自己的电脑上可用（云端没有浏览器，"
                       "抓不了需要登录态的 BOSS）。云端请用「牛客」或「实习僧」。")
    try:
        edge_path()
        return True, ""
    except RuntimeError as e:
        return False, str(e)


def is_running() -> bool:
    try:
        r = requests.get(f"http://127.0.0.1:{DEBUG_PORT}/json/version", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def launch(headless: bool = False) -> bool:
    """启动带调试端口的 Edge（独立 profile，不影响你日常用的 Edge）。"""
    if is_running():
        return True
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    args = [
        edge_path(),
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
    ]
    if headless:
        args.insert(1, "--headless=new")
    subprocess.Popen(args, close_fds=True)
    for _ in range(20):
        time.sleep(0.6)
        if is_running():
            return True
    return False


def _new_tab(url: str) -> str:
    """新建标签页，返回它的 webSocketDebuggerUrl。"""
    r = requests.put(f"http://127.0.0.1:{DEBUG_PORT}/json/new?{url}", timeout=10)
    if r.status_code != 200:
        r = requests.get(f"http://127.0.0.1:{DEBUG_PORT}/json/new?{url}", timeout=10)
    return r.json()["webSocketDebuggerUrl"]


class _CDP:
    """极简 CDP 客户端：发一条命令，等它自己的响应。"""

    def __init__(self, ws_url: str):
        self.ws = websocket.create_connection(ws_url, timeout=30,
                                              suppress_origin=True)
        self._id = 0

    def call(self, method: str, params: dict = None, timeout: float = 30):
        self._id += 1
        msg_id = self._id
        self.ws.send(json.dumps({"id": msg_id, "method": method,
                                 "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            raw = self.ws.recv()
            if not raw:
                continue
            data = json.loads(raw)
            if data.get("id") == msg_id:
                return data.get("result", {})
        raise TimeoutError(f"CDP 调用超时：{method}")

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def fetch_html(url: str, wait: float = 4.0, keep_open: bool = False) -> str:
    """打开 URL，等页面渲染完，返回 HTML。"""
    if not launch():
        raise RuntimeError("Edge 启动失败（调试端口没起来）")
    ws_url = _new_tab(url)
    cdp = _CDP(ws_url)
    try:
        cdp.call("Page.enable")
        time.sleep(wait)  # 等前端渲染
        res = cdp.call("Runtime.evaluate", {
            "expression": "document.documentElement.outerHTML",
            "returnByValue": True,
        }, timeout=40)
        return res.get("result", {}).get("value", "")
    finally:
        cdp.close()


def run_js(url: str, expression: str, wait: float = 4.0):
    """打开 URL，在页面上下文里跑一段 JS，返回结果（用于直接调站内接口）。"""
    if not launch():
        raise RuntimeError("Edge 启动失败")
    ws_url = _new_tab(url)
    cdp = _CDP(ws_url)
    try:
        cdp.call("Page.enable")
        time.sleep(wait)
        res = cdp.call("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        }, timeout=60)
        return res.get("result", {}).get("value")
    finally:
        cdp.close()


def screenshot(url: str, out_path: str, wait: float = 6.0,
               width: int = 1440, height: int = 900,
               full_page: bool = True) -> str:
    """打开页面并截图，存成 PNG。返回文件路径。"""
    import base64
    if not launch(headless=True):
        raise RuntimeError("Edge 启动失败")
    ws_url = _new_tab(url)
    cdp = _CDP(ws_url)
    try:
        cdp.call("Page.enable")
        cdp.call("Emulation.setDeviceMetricsOverride", {
            "width": width, "height": height,
            "deviceScaleFactor": 1, "mobile": False,
        })
        time.sleep(wait)
        res = cdp.call("Page.captureScreenshot", {
            "format": "png", "captureBeyondViewport": full_page,
        }, timeout=60)
        data = res.get("data", "")
        Path(out_path).write_bytes(base64.b64decode(data))
        return out_path
    finally:
        cdp.close()


if __name__ == "__main__":
    if "--setup" in sys.argv:
        ok = launch()
        print("调试窗口已启动" if ok else "启动失败")
        print(f"请在这个新开的 Edge 窗口里登录：BOSS直聘 / 实习僧 / 牛客（各登一次）")
        print(f"登录态保存在：{PROFILE_DIR}")
        print(f"注意：这个窗口不要关，程序抓取时要用它。")
    else:
        print(__doc__)
