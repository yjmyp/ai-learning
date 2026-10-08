# -*- coding: utf-8 -*-
"""服务"生产化"验收：鉴权 / 限流 / 结构化错误 / 请求 ID

单独用 8601 端口起一个**带密钥和限流**的实例，然后逐条打：
  /live 存活探针秒回且不加载模型
  /ready 就绪探针（索引非空 → 200）
  /health 公开可用且有 X-Request-ID
  /search 无 key → 401；有 key → 200
  /search 非法 mode → 422 且错误结构里有 code=bad_mode
  超过限额 → 429 且带 Retry-After
  /stats 无 key → 401（内部指标不裸奔）

跑法：python test_service_prod.py（在 rag2 目录下）
"""
import os
import subprocess
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PORT = 8601
BASE = "http://127.0.0.1:%d" % PORT
KEY = "test-key-123"
HERE = os.path.dirname(os.path.abspath(__file__))


def wait_up(timeout=300):
    """等服务就绪：开了预热时 /ready 会先返回 503（warming_up），要等它变 200。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            if requests.get(BASE + "/ready", timeout=10).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def main():
    env = dict(os.environ)
    # 额度算清楚：带 key 的请求依次是 正常/非法mode/超长q/top_k越界（4 次），
    # 所以上限给 6，留出余量后再用循环把额度打爆触发 429（避免测试和限流互相打架）
    env.update({"SERVICE_API_KEY": KEY, "SERVICE_RATE_LIMIT": "6",
                "SERVICE_RATE_WINDOW": "60", "SERVICE_WARMUP": "1"})
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "service:app", "--port", str(PORT)],
        cwd=HERE, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    checks = []
    try:
        if not wait_up():
            raise SystemExit("服务没起来")

        h = requests.get(BASE + "/health", timeout=60)   # /health 会加载引擎，给足时间
        checks.append(("健康检查公开可用且带 X-Request-ID",
                       h.status_code == 200 and "X-Request-ID" in h.headers))
        checks.append(("健康检查返回服务版本", "version" in h.json()))

        v = requests.get(BASE + "/version", timeout=10).json()
        checks.append(("版本端点显示已开启鉴权", v.get("auth_required") is True))
        checks.append(("启动预热已完成（/version.warmup.warmed）",
                       bool((v.get("warmup") or {}).get("warmed"))))

        # 探针分工：/live 必须秒回（不能等模型加载，否则 K8s 会把活着的进程杀掉）
        t0 = time.time()
        lv = requests.get(BASE + "/live", timeout=5)
        live_ms = (time.time() - t0) * 1000
        checks.append(("存活探针 /live 秒回（<500ms）且不加载模型",
                       lv.status_code == 200 and live_ms < 500
                       and "uptime_s" in lv.json()))
        rd = requests.get(BASE + "/ready", timeout=60)
        checks.append(("就绪探针 /ready 索引非空返回 200",
                       rd.status_code == 200 and rd.json().get("index_chunks", 0) > 100))

        no_key = requests.post(BASE + "/search", json={"q": "RAG"}, timeout=30)
        checks.append(("无 key 调 /search 被拒（401）", no_key.status_code == 401))

        ok_key = requests.post(BASE + "/search", json={"q": "RAG", "top_k": 1},
                               headers={"X-API-Key": KEY}, timeout=180)
        checks.append(("带 key 调 /search 正常（200）", ok_key.status_code == 200))
        checks.append(("响应带剩余额度头 X-RateLimit-Remaining",
                       "X-RateLimit-Remaining" in ok_key.headers))

        bad = requests.post(BASE + "/search", json={"q": "RAG", "mode": "no_such_mode"},
                            headers={"X-API-Key": KEY}, timeout=30)
        code = (bad.json().get("detail") or {}).get("code") if bad.headers.get(
            "content-type", "").startswith("application/json") else None
        checks.append(("非法 mode 返回 422 + 结构化错误码",
                       bad.status_code == 422 and code == "bad_mode"))

        # 输入校验：超长问题 / top_k 越界，都必须在进模型之前就被挡掉
        long_q = requests.post(BASE + "/search", json={"q": "问" * 3000},
                               headers={"X-API-Key": KEY}, timeout=30)
        checks.append(("超长问题被输入校验挡下（422）", long_q.status_code == 422))
        big_k = requests.post(BASE + "/search", json={"q": "RAG", "top_k": 999},
                              headers={"X-API-Key": KEY}, timeout=30)
        checks.append(("top_k 越界被挡下（422）", big_k.status_code == 422))

        stats_no_key = requests.get(BASE + "/stats", timeout=30)
        checks.append(("内部指标 /stats 要鉴权（401）", stats_no_key.status_code == 401))

        # 探针（/health /version）不占额度：连打 5 次仍应 200，且额度不被消耗
        probes_ok = all(requests.get(BASE + p, timeout=10).status_code == 200
                        for p in ["/health", "/health", "/version", "/health"])
        checks.append(("探针端点不占限流额度（连打 4 次仍 200）", probes_ok))

        # 把该 key 的额度打到超限（最多试 12 次，避免死循环）
        limited = None
        for _ in range(12):
            r = requests.post(BASE + "/search", json={"q": "RAG", "top_k": 1},
                              headers={"X-API-Key": KEY}, timeout=30)
            if r.status_code == 429:
                limited = r
                break
        checks.append(("超限返回 429 且带 Retry-After",
                       limited is not None and "Retry-After" in limited.headers))
        if limited is not None:
            checks.append(("429 响应体是结构化错误",
                           limited.json().get("error", {}).get("code") == "rate_limited"))
        else:
            checks.append(("429 响应体是结构化错误", False))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except Exception:
            proc.kill()

    ok = 0
    for name, good in checks:
        print(("✅ " if good else "❌ ") + name)
        ok += 1 if good else 0
    print("\n%d/%d 通过" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
