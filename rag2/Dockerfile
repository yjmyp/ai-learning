# RAG v3 服务镜像：docker compose up --build 即可起一个能被调用的检索服务
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

# 系统依赖：chroma 需要 sqlite3，sentence-transformers 需要 libgomp
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-service.txt .
# CPU 版 torch：镜像体积从 ~2.5G 降到 ~1G，本地服务用不到 GPU
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements-service.txt

COPY . .

EXPOSE 8600
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD curl -fs http://localhost:8600/health || exit 1

# --workers 1：向量模型在进程内，起多 worker 会翻倍占内存（要扩就上 gunicorn+uvicorn worker）
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8600", "--workers", "1"]
