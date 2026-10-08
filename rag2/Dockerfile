# RAG v3 服务镜像：docker compose up --build 即可起一个能被调用的检索服务
# 注意：构建上下文是仓库根目录（与 offeragent/Dockerfile 约定一致），
#   COPY 源路径必须带 rag2/ 前缀，否则 docker build 会去找根目录下不存在的文件。
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false \
    SERVICE_WARMUP=1

WORKDIR /app

# 系统依赖：chroma 需要 sqlite3，sentence-transformers 需要 libgomp
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY rag2/requirements-service.txt /app/requirements-service.txt
# CPU 版 torch：镜像体积从 ~2.5G 降到 ~1G，本地服务用不到 GPU
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
        -r /app/requirements-service.txt

COPY rag2/ /app

EXPOSE 8600
# 探针分工：这里查 /live（存活，秒回、不碰模型）。
# 排到 K8s/Nginx 时，就绪探针请用 /ready（索引为空会返回 503，网关先别转流量）。
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s \
    CMD curl -fs http://localhost:8600/live || exit 1

# 启动预热：把模型加载 + BM25 建索引提前做掉（实测能让首请求从 15.3s 降到 ~0.07s）。
# --workers 1：向量模型在进程内，起多 worker 会翻倍占内存；要扩容改 WEB_CONCURRENCY
# 并在压测下确认内存（见 eval/loadtest_report.md 的扩容路径）。
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8600", "--workers", "1"]
