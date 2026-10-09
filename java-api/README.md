# java-api · 对外 API 层（SpringBoot 3 + Java 21）

**定位**：不改 Python 的 AI 能力，在它前面加一层 Java 服务。业务型接口（岗位查询）由 Java 提供，
AI 请求（检索/问答）转发给已有的 Python RAG 服务。这就是「Java 壳 + Python 脑」的最小可用版。

**为什么要分两层**（面试会问）：Java 侧扛并发连接和业务事务，Python 侧吃 CPU 做向量推理与模型调用，
两者的扩容策略、发布节奏、资源曲线都不同；混在一个进程里，任何一侧的负载都会拖死另一侧。

## 环境要求

- JDK 21（本机：`C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot`）
- Maven 3.9+（本机：`C:\Users\29947\tools\apache-maven-3.9.16`）
- 可选：Python RAG 服务（`rag2`，默认 `http://127.0.0.1:8600`）；不启动也能跑，只是 `/api/rag/search` 会报 502

> 新终端里 `java -version` / `mvn -v` 都能直接用（JAVA_HOME 与 PATH 已写入用户环境变量）。

## 构建与运行

```powershell
cd java-api
mvn -B test                  # 3 个接口测试（岗位过滤 + 两个参数校验用例）
mvn -B -DskipTests package   # 产出 target/offeragent-api-0.1.0.jar
java -jar target\offeragent-api-0.1.0.jar
```

启动后监听 `8080`。若要同时验证 AI 转发，另开一个终端起 Python 侧：

```powershell
cd rag2
$env:SERVICE_WARMUP="1"; python -m uvicorn service:app --port 8600
```

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/health` | 免鉴权。本服务 + **MySQL 状态** + 岗位统计（走缓存）+ **下游 Python 可达性** |
| GET | `/api/jobs?minScore=80&limit=10` | 需 `X-API-Key`。从 **MySQL** 按匹配分查岗位（JPA），结果进 **Redis 缓存**（TTL 60s） |
| POST | `/api/rag/search` | 需 `X-API-Key`。`{"q": "...", "topK": 5}` → 校验后转发给 Python 检索服务 |
| GET | `/actuator/health` | 免鉴权（给部署平台探针）。Actuator 标准健康端点 |

## 鉴权（2026-10-09 加）

```powershell
curl.exe http://127.0.0.1:8080/api/jobs                      # → 401 {"error":"unauthorized"}
curl.exe -H "X-API-Key: oa-demo-key-001" http://127.0.0.1:8080/api/jobs   # → 200
```

- **为什么用 API Key 不用 JWT**：调用方是系统对系统，没有用户登录态要维护，JWT 的签发/刷新/撤销是纯负担
- **定长比较**（`MessageDigest.isEqual`）：普通 `equals` 会在第一个不同字符处返回，能被按时序逐字节猜 Key
- **fail closed**：没配 `OFFERAGENT_API_KEY` 时受保护接口返回 **503** 而不是放行——配置漏了却继续放行等于接口裸奔
- **免鉴权路径**：`/api/health`、`/actuator/**`（探针要用）；`OPTIONS` 预检也放行
- 鉴权只在这一个过滤器里做（`SecurityConfig` 里 `anyRequest().permitAll()`），避免规则分散在两处

## Docker（2026-10-09 加）

```bash
# 一键起 MySQL + Redis + java-api（java-api 等前两个健康后再起）
export OFFERAGENT_API_KEY=你的key
docker compose -f java-api/docker-compose.yml up --build

# 需要 Python AI 服务时（要装 CPU 版 torch，镜像大、构建慢）
docker compose -f java-api/docker-compose.yml --profile full up --build

# 只构建镜像
docker build -f java-api/Dockerfile -t offeragent-api:latest .
```

- **多阶段构建**：构建阶段用 `maven:3.9-eclipse-temurin-21`，运行阶段只留 `eclipse-temurin:21-jre`；先 `COPY pom.xml` 拉依赖，源码改动不会让依赖层失效
- **非 root 运行**（`useradd appuser`）+ `-XX:+UseContainerSupport`、`-XX:+ExitOnOutOfMemoryError`
- **`depends_on: condition: service_healthy`**：只写 `depends_on` 只保证容器起来了，MySQL 首次初始化要十几秒，不等健康检查 java-api 会启动失败
- **静态校验**（没 Docker 也能跑）：`python java-api/test_docker_static.py` → **22/22**，其中包含"严格 YAML 加载器查重复键"

## 数据与缓存层（2026-10-09 接入 MySQL + Redis）

```
JSON 文件（Python 侧仍在写）
      │ 启动时 JobSeeder 导入（表为空才导，岗位名做主键 → 幂等）
      ▼
   MySQL 8.0.29  offeragent.job                                  ← 本机 C:\tools\mysql-8.0.29-winx64 / 端口 3306
      ▲
      │ 未命中时用 JPA 查（只读事务）
   JobService ──命中直接返回──▶ Redis  jobs::<minScore>:<limit>（TTL 60s）
                              └▶ jobStats::all（TTL 15s）        ← 本机 C:\tools\redis-server.exe / 端口 6379

   每个 IP 每分钟 30 次 ──▶ Redis INCR  oa:ratelimit:<ip>:<分钟> ──超限──▶ 429 + Retry-After
```

- **缓存键必须带查询参数**（`jobs::80:3` 而不是 `jobs`），否则不同过滤条件互相污染
- **限流计数放 Redis**：进程内计数在多实例下会翻倍放行；停 Redis 时降级放行但打日志

## 边界处理（这几条是踩过才写的）

## 指标与观测（2026-10-09 加 Micrometer + Prometheus）

```bash
curl.exe http://127.0.0.1:8080/actuator/prometheus | findstr oa_
```

自研指标（都带 `application="offeragent-api"` 标签）：

| 指标 | 含义 |
|---|---|
| `oa_cache_hits_total{cache}` / `oa_cache_misses_total{cache}` | 缓存命中/未命中，用来算命中率 |
| `oa_db_query_seconds{query}` | 真正打到数据库的耗时（Timer，含 count/sum/max） |
| `oa_ratelimit_blocked_total` | 被限流拦下的次数 |
| 框架自带：`http_server_requests_seconds`、`hikaricp_connections_*`、`jvm_*` | 请求延迟、连接池、JVM |

**为什么不用 `@Cacheable` 而是手写 cache-aside**：`@Cacheable` 命中时**根本不进方法体**，
命中/未命中就无从埋点——而"缓存命中率"恰恰是缓存最该看的指标。手写之后读写路径都看得见。

实测（本机真 MySQL + Redis，3 次查询 + 1 次超限）：

```
oa_cache_hits_total{cache="jobs"} 2.0        # 命中 2 次
oa_cache_misses_total{cache="jobs"} 1.0      # 只查了一次库
oa_db_query_seconds_count{query="jobs"} 1
oa_ratelimit_blocked_total 1.0
http_server_requests_seconds_count{status="429",uri="/api/jobs"} 1
hikaricp_connections_active{pool="HikariPool-1"} 0.0
```

### 接 Grafana（3 步）

1. **Prometheus 抓取**（`prometheus.yml`）：

```yaml
scrape_configs:
  - job_name: offeragent-api
    metrics_path: /actuator/prometheus
    static_configs:
      - targets: ["host.docker.internal:8080"]   # 容器里抓宿主机；同 compose 网络里写服务名 java-api:8080
```

2. **Grafana 加数据源**：Configuration → Data Sources → Prometheus → URL 填 `http://prometheus:9090` → Save & Test。

3. **常用面板 PromQL**：

```promql
# 缓存命中率（5 分钟）
sum(rate(oa_cache_hits_total[5m])) by (cache)
  / (sum(rate(oa_cache_hits_total[5m])) by (cache) + sum(rate(oa_cache_misses_total[5m])) by (cache))

# 数据库查询 P95
histogram_quantile(0.95, sum(rate(oa_db_query_seconds_bucket[5m])) by (le))

# 限流触发速率（每分钟）
sum(increase(oa_ratelimit_blocked_total[1m]))

# 接口延迟 P95 与 5xx 比例
histogram_quantile(0.95, sum(rate(http_server_requests_seconds_bucket{uri="/api/jobs"}[5m])) by (le))
sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m])) / sum(rate(http_server_requests_seconds_count[5m]))
```

> 注意：`/actuator/prometheus` 目前是免鉴权暴露的（本地开发方便）。**生产环境要收口**——
> 要么只在内网暴露，要么在 Security 里给它加权限，避免把 JVM/连接池/接口维度信息白送出去。

1. **入参在边界校验**：`q` 非空且 ≤2000 字、`topK` 1~50、不传 `topK` 默认 5；违规返回
   `400 {"error":"bad_request","fields":["topK: topK 最大 50"]}`。
2. **状态码语义不能糊**：下游返回 4xx/5xx 时**透传原状态码**，只有连不上才报 502。
   之前把下游 422 包装成 502，调用方会去查"我们服务挂了"，方向全错。
3. **超时分开配**：连接 3s、读 60s —— 模型侧慢是常态，但不能无限等。
4. **数据目录缺失不致命**：岗位目录不存在时返回空列表，服务照常启动。
5. **缓存值不能用 JDK 序列化**：默认序列化器要求 `implements Serializable`；更坑的是
   **写进 Redis 的类型信息遇到 `Map.of()` / `.toList()` 这类 JDK 不可变集合，读回来会抛
   `SerializationException`（实测 500）**。改成 JSON 序列化 + 返回标准 `HashMap` / `ArrayList`。
6. **`@EnableCaching` 不能省**：Spring Boot 的 CacheManager 是条件装配的，漏了它启动直接报
   `required a bean of type CacheManager that could not be found`。
7. **关掉 `spring.data.redis.repositories`**：否则 Spring Data Redis 会去扫 JPA 接口并刷告警。

## 已验证

```
mvn test                                   → Tests run: 19, Failures: 0, Errors: 0, Skipped: 5
                                             本地无 Docker：14 个单元/切片用例通过，5 个集成用例自动跳过
                                             CI（有 Docker）：19 个全跑，真起 MySQL/Redis 容器
python java-api/test_docker_static.py       → 22/22（含重复键检测；已用故意重复的 YAML 验证过它会失败）
MySQL offeragent.job                       → 22 行 / avg 65 / 最高 88
鉴权                                       → 无/错 Key 401；未配 Key 503（fail closed）；/api/health、/actuator/** 免鉴权
GET  /api/health                           → 200 {"mysql":"ok",
                                             "jobStats":{"total":22,"avgScore":65,"scoreOver80":3},
                                             "pythonAiService":"ok(200)"}
GET  /api/jobs?minScore=80&limit=3 第 1 次   → 200，464ms（日志：查 MySQL：minScore=80 limit=3（没走缓存））
GET  /api/jobs?minScore=80&limit=3 第 2 次   → 200，51ms（无 SQL 日志 = 命中 Redis）
Redis                                      → jobs::80:3 (TTL 60) / jobStats::all (TTL 15) / oa:ratelimit:<key哈希@ip>:<分钟>
限流（上限设 5/分钟）                        → 第 6 次 429 {"error":"rate_limited"} + Retry-After: 28（维度 = API Key 哈希 + IP）
POST /api/rag/search {"q":"向量检索怎么算相似度","topK":2} → 200（2 条命中，mode=hybrid_rerank）
POST /api/rag/search {"q":"","topK":3}      → 400 bad_request（字段级说明）
POST /api/rag/search {"q":"x","topK":999}   → 400 bad_request
```

## 还没做（如实写）

- **只支持单 Key**：轮换要支持"多 Key + 有效期 + 灰度切换"，把 Key 从配置挪到表里并记录最后使用时间。
- **集成测试已进 CI**（Testcontainers 真起 MySQL/Redis 容器）：本地没 Docker 时
  `@Testcontainers(disabledWithoutDocker = true)` 会自动跳过，CI runner 上有 Docker 会真跑；
  岗位数据用临时夹具生成，**不依赖本地 `offeragent/data/`**（那是 gitignore 的隐私数据）。
- **表结构靠 `ddl-auto=update`**：生产环境应换成 Flyway / Liquibase 版本化迁移。
- **缺链路追踪**：指标有了（Micrometer + Prometheus），但跨 Java ↔ Python 的 trace 还没串起来。
- **Prometheus 端点没收口**：现在免鉴权暴露，生产要限内网或加权限。
- **限流/缓存没压测**：容量数据是空的（Python 侧有压测脚本可参考）。
