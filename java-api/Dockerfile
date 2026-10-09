# java-api 镜像：多阶段构建
#   本地构建（构建上下文必须是仓库根）：docker build -f java-api/Dockerfile -t offeragent-api:latest .
#   一键起全套：docker compose -f java-api/docker-compose.yml up --build

# ---------- 阶段 1：构建 ----------
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build

# 先只拷 pom 拉依赖：源码改了不会让依赖层失效，重复构建能从缓存里省掉几分钟
COPY java-api/pom.xml .
RUN mvn -B -q dependency:go-offline

COPY java-api/src ./src
RUN mvn -B -q -DskipTests package

# ---------- 阶段 2：运行 ----------
FROM eclipse-temurin:21-jre

# curl 只给 HEALTHCHECK 用；装完清 apt 缓存，别把镜像撑大
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 不以 root 跑：容器被攻破时，攻击者拿到的不是宿主机的 root 上下文
RUN useradd -r -u 10001 -m appuser
WORKDIR /app

COPY --from=build --chown=appuser:appuser /build/target/offeragent-api-*.jar /app/app.jar
USER appuser

EXPOSE 8080

# 容器感知：让 JVM 按 cgroup 限额算堆，并给 Java 21 的分代 ZGC 留个开关（默认关，压测时再开）
ENV JAVA_OPTS="-XX:+UseContainerSupport -XX:MaxRAMPercentage=70 -XX:+ExitOnOutOfMemoryError"

# 探针打 actuator：不依赖 MySQL/Redis，容器起来就能报活
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fs http://localhost:8080/actuator/health || exit 1

ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
