# -*- coding: utf-8 -*-
"""Docker 真构建验收（本机没装 Docker 时自动降级为静态校验）

为什么分两档：静态校验只能证明"配置文件写得没矛盾"，证明不了镜像真能跑起来。
真构建路径（有 Docker 的机器 / CI）会：build 两个镜像 → 起容器 → 打探针端点 → 关掉。

跑法：
    python test_docker_build.py                       # 没 Docker 就静态校验 + 跳过
    RUN_DOCKER_BUILD=1 python test_docker_build.py    # 强制真构建（约 5-15 分钟，要下 torch）

注意：CI 里默认不跑真构建（太重），由 .github/workflows/ci.yml 的 docker job 单独触发。
"""
import os
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def sh(args, **kw):
    # encoding 必须显式给 utf-8：Windows 控制台默认 GBK，docker 输出里有非 GBK 字节会直接抛
    kw.setdefault("encoding", "utf-8")
    kw.setdefault("errors", "replace")
    return subprocess.run(args, capture_output=True, text=True, **kw)


def docker_ready():
    """docker 命令存在 + 守护进程在跑，两者都满足才算可用。"""
    if not shutil.which("docker"):
        return False, "没找到 docker 命令"
    r = sh(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=60)
    if r.returncode != 0:
        return False, "docker 守护进程没起来（Docker Desktop 没开？）"
    return True, r.stdout.strip()


def http_ok(url, timeout=5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status == 200, resp.read(200).decode("utf-8", "replace")
    except Exception as e:
        return False, str(e)[:120]


def wait_http(url, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        ok, _ = http_ok(url)
        if ok:
            return True
        time.sleep(3)
    return False


def build_and_probe(name, build_args, image, run_args, probe_url):
    """构建镜像 → 起容器 → 等探针 200 → 收尾。返回 (通过?, 说明)"""
    r = sh(["docker", "build"] + build_args + ["-t", image] + [ROOT], timeout=3600)
    if r.returncode != 0:
        tail = (r.stderr or r.stdout).strip().splitlines()[-3:]
        return False, "构建失败：" + " | ".join(tail)
    up = sh(["docker", "run", "-d", "--name", image.replace(":", "-")] + run_args + [image],
            timeout=300)
    if up.returncode != 0:
        return False, "启动失败：" + up.stderr.strip()[:200]
    cid = up.stdout.strip()
    try:
        if not wait_http(probe_url):
            logs = sh(["docker", "logs", "--tail", "20", cid], timeout=60)
            return False, "探针 %s 没通；日志：%s" % (probe_url, logs.stdout.strip()[-300:])
        return True, "镜像起得来、探针 200（%s）" % probe_url
    finally:
        sh(["docker", "stop", cid], timeout=120)
        sh(["docker", "rm", cid], timeout=60)


def main():
    checks = []
    ok, info = docker_ready()

    # 无论有没有 Docker，静态校验都先跑（它挡的是"配置自相矛盾"这类错）
    r = sh([sys.executable, os.path.join(ROOT, "offeragent", "test_docker_static.py")])
    checks.append(("OfferAgent Docker 配置静态校验", r.returncode == 0))
    if r.returncode != 0:
        print(r.stdout[-1500:], r.stderr[-500:])

    if not (ok and os.environ.get("RUN_DOCKER_BUILD", "") == "1"):
        checks.append(("Docker 真构建（build+起容器+打探针）",
                       None))   # None = 跳过，不算失败
        reason = info if not ok else "未设置 RUN_DOCKER_BUILD=1（真构建太重，按需开启）"
        print("  [跳过] 真构建：%s" % reason)
    else:
        checks.append(("rag2 服务镜像真构建并打 /ready",
                       build_and_probe("rag2", ["-f", os.path.join(ROOT, "rag2", "Dockerfile")],
                                       "rag2-svc:test", ["-p", "18600:8600"],
                                       "http://127.0.0.1:18600/live")[0]))
        checks.append(("OfferAgent 镜像真构建并打 Streamlit 健康检查",
                       build_and_probe(
                           "offeragent",
                           ["-f", os.path.join(ROOT, "offeragent", "Dockerfile")],
                           "offeragent:test", ["-p", "18501:8501"],
                           "http://127.0.0.1:18501/_stcore/health")[0]))

    passed = sum(1 for _, v in checks if v is True)
    failed = [n for n, v in checks if v is False]
    skipped = [n for n, v in checks if v is None]
    for name, v in checks:
        print(("✅ " if v is True else ("❌ " if v is False else "⏭️ ")) + name)
    print("\n%d 通过 / %d 失败 / %d 跳过" % (passed, len(failed), len(skipped)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
