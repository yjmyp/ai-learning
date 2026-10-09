# -*- coding: utf-8 -*-
"""本地 → GitHub 的备用推送通道（走 api.github.com，绕开不通的 github.com:443）。

背景：这台机器上 git push（github.com:443）长期连接被重置，但 api.github.com 通。
所以用 REST API 把本地领先远端的那些提交，按文件同步上去，并逐个字节校验。

用法：
    python tools/push_to_github.py --dry-run        只看要传哪些文件
    python tools/push_to_github.py                  真推 + 推完逐字节校验
    python tools/push_to_github.py --base b633e78   指定对比的远端基点

凭据：从 Windows 凭据管理器读（git credential fill），不落盘、不打印。

代理：这台机器直连 github.com 会被重置（TCP 通、TLS 握手被掐），必须走系统代理。
脚本会自动探测常见的本地代理端口（127.0.0.1:7897/7890 等）并用它；也可以用
$env:HTTPS_PROXY 显式指定。**优先用 `git push`**（已配好仓库级 http.proxy），
本脚本留作历史分叉/单文件同步时的备用通道。
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = "yjmyp/ai-learning"
BRANCH = "master"
API = f"https://api.github.com/repos/{REPO}/contents/"


def log(*a):
    print(*a, flush=True)


def git(args, text=True):
    r = subprocess.run(["git", *args], capture_output=True)
    if r.returncode != 0:
        raise SystemExit("git 命令失败：" +
                         r.stderr.decode("utf-8", "ignore")[:200])
    return r.stdout.decode("utf-8", "ignore") if text else r.stdout


def token():
    """从 git 凭据管理器取 GitHub token（只返回，不打印）。"""
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    r = subprocess.run(["git", "credential", "fill"],
                       input=b"protocol=https\nhost=github.com\n\n",
                       capture_output=True, env=env)
    fields = {}
    for line in r.stdout.decode("utf-8", "ignore").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            fields[k] = v
    tok = fields.get("password", "")
    if not tok:
        raise SystemExit("拿不到 GitHub 凭据（git credential fill 没返回 password）")
    return tok, fields.get("username", "")


def _auto_proxy():
    """探测本地代理；直连 github 会被重置，走代理才通。

    返回 proxies dict（给 requests 用）或 None。只在没显式设置 HTTPS_PROXY 时探测。
    """
    if os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy"):
        return None
    import socket
    for port in (7897, 7890, 7891, 10809, 10808):
        s = socket.socket()
        s.settimeout(0.4)
        try:
            s.connect(("127.0.0.1", port))
            return {"http": "http://127.0.0.1:%d" % port,
                    "https": "http://127.0.0.1:%d" % port}
        except Exception:
            continue
        finally:
            s.close()
    return None


def api(method, path, tok, body=None, raw=False):
    if path.startswith("http"):
        url = path
    else:
        # 注意：?ref=master 这种查询串不能被 quote，否则会变成 %3Fref%3Dmaster 直接 404
        p, _, q = path.partition("?")
        url = API + urllib.parse.quote(p, safe="/") + (("?" + q) if q else "")
    data = json.dumps(body).encode() if body is not None else None
    # 直连被重置时自动切到本地代理（urllib 会读 *_PROXY 环境变量）
    px = _auto_proxy()
    if px:
        os.environ.setdefault("HTTPS_PROXY", px["https"])
        os.environ.setdefault("HTTP_PROXY", px["http"])
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + tok)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        if e.code == 404:
            return None, 404, detail
        raise SystemExit(f"GitHub API {method} {path} -> {e.code}\n{detail}")
    return (payload if raw else json.loads(payload or b"{}")), 200, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/master")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--branch", default=BRANCH)
    ap.add_argument("--files", default="",
                    help="只推这几个文件（逗号分隔），从工作区直接读，用于本地 refs 落后时")
    args = ap.parse_args()

    tok, user = token()
    log(f"凭据 OK（账号 {user}）")
    head = git(["rev-parse", "--short", "HEAD"]).strip()
    base_sha = git(["rev-parse", "--short", args.base]).strip()
    ref, code, _ = api("GET",
                       f"https://api.github.com/repos/{REPO}/git/ref/heads/{args.branch}", tok)
    remote_sha = ((ref or {}).get("object", {}) or {}).get("sha", "")[:7]
    log(f"本地 HEAD = {head} ｜ 远端 {args.branch} = {remote_sha} ｜ 对比基点 = {base_sha}")
    if remote_sha and remote_sha != base_sha:
        log("⚠️ 远端已经不在对比基点了，继续会把本地文件盖上去。")

    if args.files:
        changes = [("M", f.strip()) for f in args.files.split(",") if f.strip()]
    else:
        raw = git(["diff", "--name-status", "-z", "--no-renames", args.base, "HEAD"],
                  text=False)
        parts = [p for p in raw.split(b"\0") if p]
        changes = [(parts[i].decode(), parts[i + 1].decode("utf-8"))
                   for i in range(0, len(parts) - 1, 2)]
    log(f"要同步 {len(changes)} 个文件：")
    for st, path in changes:
        log(f"   {st}  {path}")
    if args.dry_run:
        return 0

    ok, failed = [], []
    for st, path in changes:
        try:
            meta, code, _ = api("GET", f"{path}?ref={args.branch}", tok)
            sha = (meta or {}).get("sha")
            if st == "D":
                if not sha:
                    log(f"⏭  {path} 远端本来没有，跳过")
                    continue
                api("DELETE", path, tok, {"message": f"delete: {path}",
                                          "sha": sha, "branch": args.branch})
                log(f"🗑  删除 {path}")
                ok.append(path)
                continue
            content = git(["show", f"HEAD:{path}"], text=False)
            body = {"message": f"sync({head}): {path}",
                    "content": base64.b64encode(content).decode(),
                    "branch": args.branch}
            if sha:
                body["sha"] = sha
            api("PUT", path, tok, body)
            back, _, _ = api("GET", f"{path}?ref={args.branch}", tok, raw=True)
            meta_back = json.loads(back)
            remote_bytes = base64.b64decode(meta_back["content"].replace("\n", ""))
            same = remote_bytes == content
            log(("✅ " if same else "❌ ") + f"{path}（{len(content)} 字节）"
                + ("" if same else " 字节不一致！"))
            (ok if same else failed).append(path)
        except SystemExit as e:
            log(f"❌ {path}：{e}")
            failed.append(path)
        time.sleep(0.2)

    log("")
    log(f"成功 {len(ok)} 个，失败 {len(failed)} 个")
    if failed:
        log("失败清单：", failed)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
