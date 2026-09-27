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
import subprocess
import sys
import time
from pathlib import Path

import requests
import websocket  # websocket-client

HERE = Path(__file__).parent
PROFILE_DIR = HERE / "data" / "edge_profile"
DEBUG_PORT = 9333

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def edge_path() -> str:
    for p in EDGE_CANDIDATES:
        if Path(p).exists():
            return p
    raise RuntimeError("没找到 Edge，请确认安装路径")


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
