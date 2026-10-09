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
| GET | `/api/health` | 本服务 + **MySQL 状态** + 岗位统计（走缓存）+ **下游 Python 服务可达性** |
| GET | `/api/jobs?minScore=80&limit=10` | 从 **MySQL** 按匹配分查岗位（JPA），结果进 **Redis 缓存**（TTL 60s） |
| POST | `/api/rag/search` | `{"q": "...", "topK": 5}` → 校验后转发给 Python 检索服务 |
| GET | `/actuator/health` | Spring Boot Actuator 标准健康端点 |

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
mvn test                                   → Tests run: 7, Failures: 0, Errors: 0
MySQL offeragent.job                       → 22 行 / avg 65 / 最高 88
GET  /api/health                           → 200 {"mysql":"ok",
                                             "jobStats":{"total":22,"avgScore":65,"scoreOver80":3},
                                             "pythonAiService":"ok(200)"}
GET  /api/jobs?minScore=80&limit=3 第 1 次   → 200，464ms（日志：查 MySQL：minScore=80 limit=3（没走缓存））
GET  /api/jobs?minScore=80&limit=3 第 2 次   → 200，51ms（无 SQL 日志 = 命中 Redis）
Redis                                      → jobs::80:3 (TTL 60) / jobStats::all (TTL 15) / oa:ratelimit:<ip>:<min>
限流（上限设 5/分钟）                        → 第 6 次 429 {"error":"rate_limited"} + Retry-After: 28
POST /api/rag/search {"q":"向量检索怎么算相似度","topK":2} → 200（2 条命中，mode=hybrid_rerank）
POST /api/rag/search {"q":"","topK":3}      → 400 bad_request（字段级说明）
POST /api/rag/search {"q":"x","topK":999}   → 400 bad_request
```

## 还没做（如实写）

- **对外鉴权还没加**：`/api/**` 目前无 API Key 校验（Python 侧有 `X-API-Key`，转发时可选透传）。
  下一步该上 Spring Security + API Key 过滤链，并把限流维度从"IP"细化成"API Key + IP"。
- **集成测试没进 CI**：`mvn test` 跑的是不依赖外部服务的单元/切片测试（7 个）；
  连真实 MySQL/Redis 的验证目前靠本地手工执行（CI runner 上没有这两个服务）。
  要补就得用 Testcontainers 或在 CI 里起 service 容器。
- **表结构靠 `ddl-auto=update`**：生产环境应换成 Flyway / Liquibase 版本化迁移。
- **没有 Docker 化**：Python 侧有 Dockerfile，Java 侧还没写。
