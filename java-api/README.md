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
| GET | `/api/health` | 本服务状态 + **下游 Python 服务可达性**（`ok(200)` / `down:连接异常类型`） |
| GET | `/api/jobs?minScore=80&limit=10` | 读岗位库（`offeragent/data/jds/*.meta.json`），按匹配分过滤，返回总数与清单 |
| POST | `/api/rag/search` | `{"q": "...", "topK": 5}` → 校验后转发给 Python 检索服务 |
| GET | `/actuator/health` | Spring Boot Actuator 标准健康端点 |

## 边界处理（这几条是踩过才写的）

1. **入参在边界校验**：`q` 非空且 ≤2000 字、`topK` 1~50、不传 `topK` 默认 5；违规返回
   `400 {"error":"bad_request","fields":["topK: topK 最大 50"]}`。
2. **状态码语义不能糊**：下游返回 4xx/5xx 时**透传原状态码**，只有连不上才报 502。
   之前把下游 422 包装成 502，调用方会去查"我们服务挂了"，方向全错。
3. **超时分开配**：连接 3s、读 60s —— 模型侧慢是常态，但不能无限等。
4. **数据目录缺失不致命**：岗位目录不存在时返回空列表，服务照常启动。

## 已验证

```
mvn test                          → Tests run: 3, Failures: 0, Errors: 0
GET  /api/health                  → 200 {"status":"up","javaVersion":"21.0.12.1","pythonAiService":"ok(200)"}
GET  /api/jobs?minScore=85&limit=5 → 200 {"total":22,"returned":2,...}
POST /api/rag/search {"q":"向量检索怎么算相似度","topK":2} → 200（2 条命中，mode=hybrid_rerank）
POST /api/rag/search {"q":"","topK":3}   → 400 bad_request（字段级说明）
POST /api/rag/search {"q":"x","topK":999} → 400 bad_request
```

## 还没做（如实写）

- **没有 MySQL / Redis**：岗位数据直接读 JSON 文件，没接关系库与缓存。要补的是：JDBC + 连接池、
  表结构设计、Redis 缓存岗位列表与限流计数。—— 本机也还没装 MySQL/Redis。
- 没有鉴权：对外接口目前无 API Key 校验（Python 侧已有 `X-API-Key`，转发时是可选透传）。
- 没有 Docker 化：Python 侧有 Dockerfile，Java 侧还没写。
