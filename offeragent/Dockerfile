# OfferAgent 容器镜像
# 注意：构建上下文必须是**仓库根目录**（应用要 import 根目录下的 offer_agent_*.py）
#   本地构建：docker build -f offeragent/Dockerfile -t offeragent:latest .
#   一键启动：docker compose -f offeragent/docker-compose.yml up --build
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY offeragent/requirements.txt /app/offeragent/requirements.txt
RUN pip install --no-cache-dir -r /app/offeragent/requirements.txt

# 整个仓库进镜像（应用依赖根目录的 agent 引擎模块）；data/ 由 volume 覆盖
COPY . /app

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
    CMD curl -fs http://localhost:8501/_stcore/health || exit 1

WORKDIR /app/offeragent
CMD ["streamlit", "run", "offer_agent_app.py", \
     "--server.headless", "true", "--server.port", "8501", \
     "--server.address", "0.0.0.0"]
