# 05 · Java 对外 API 层深挖（java-api：SpringBoot 3 + MySQL + Redis + Docker）

> 用途：面试官顺着简历那条「对外 API 层（Java/SpringBoot 3 + JDK 21 + MySQL + Redis）」往下问时用。
> 所有数字都能在仓库里复现（`java-api/README.md` 有命令）。**没做的一律不吹**。

## 一、30 秒版本

> "我原来的 AI 能力都是 Python 写的，但投递面上一半以上的岗位要 Java 后端。所以我没有从零做云盘，而是在已有项目前面加了一层 Java 服务：业务型接口——岗位查询、统计——用 SpringBoot 3 + JDK 21 提供，数据从 JSON 迁到 MySQL（JPA + HikariCP），热点查询走 Redis 缓存，同一请求从 464 毫秒降到 51 毫秒；再用 Redis 计数器做每调用方每分钟限流，超限返回 429。AI 相关的请求不重写，转发给原来的 Python 检索服务。这样一套下来，Java 那一侧的接口设计、持久化、缓存、限流、容器化都有了真实实现，Python 那侧的模型能力一点没浪费。"

## 二、90 秒版本（加上取舍与踩坑）

在 30 秒基础上补三点：

1. **为什么拆两个进程**：Java 侧扛并发连接和业务事务，Python 侧吃 CPU 做向量推理与模型调用，两者的扩容策略、发布节奏、资源曲线都不一样；混在一个进程里，任何一侧的负载都会拖死另一侧。代价是要处理跨服务超时与错误语义——这块我踩过坑（见 STORY 1）。
2. **为什么用 API Key 不用 JWT**：调用方是"系统对系统"，没有用户登录态要维护；JWT 的签发/刷新/撤销在这个场景是纯负担。所以用 API Key + 定长比较（防时序攻击），并且**没配 Key 就 fail closed 返回 503**——配置漏了却继续放行等于接口裸奔。
3. **数据流**：岗位数据先由 Python 侧写进 JSON，Java 启动时幂等导入 MySQL（岗位名做主键）；以后再反转数据流向，让 Java 侧接管写入。**过渡期两边读同一份数据是刻意的，避免"两套数据各写一份"。**

## 三、架构与数据流

```
调用方 ── X-API-Key ──▶ java-api (:8080)
                          ├─ ApiKeyAuthFilter（401 / fail-closed 503）
                          ├─ RateLimitInterceptor（Redis INCR，429 + Retry-After）
                          ├─ GET /api/jobs  ──▶ JobService ──▶ Redis 缓存（TTL 60s）
                          │                                    └─未命中─▶ JPA ──▶ MySQL offeragent.job
                          ├─ GET /api/health（免鉴权，含 MySQL/统计/下游可达性）
                          └─ POST /api/rag/search ──▶ Python RAG 服务 (:8600，SSE/JSON)
```

## 四、面试 STORY（现象 → 定位 → 根因 → 修复 → 防回归）

### STORY 1｜客户端错误被我说成服务端故障（422 → 502）

- **现象**：手测时 `POST /api/rag/search {"q":"","topK":3}` 返回 **502**，日志里只有一句"下游不可用"。
- **定位**：断点/日志看下来，下游 Python 服务其实返回了 **422**（它自己的入参校验），是**我的 catch 把它统一包成了 502**。
- **根因**：用一个大 `catch (Exception)` 兜住所有异常，丢掉了"错误归属"这个信息。502 的语义是"网关/上游坏了"，422 是"调用方参数不对"——两者根因相反，调用方会顺着 502 去查我们的服务，方向全错。
- **修复**：按异常类型分流——`RestClientResponseException`（下游 4xx/5xx）**透传原状态码**；只有 `ResourceAccessException`（连不上）才 502；其余 500。
- **防回归**：加了断言状态码的用例（空 q → **400**、topK 越界 → **400**），并在 README 里写成"状态码语义不能糊"。

### STORY 2｜缓存序列化两连坑（这个我最想讲）

- **现象**：第一次请求 `GET /api/jobs` 返回 200（日志"查 MySQL … 没走缓存"），**第二次相同请求直接 500**，栈里是 `SerializationException: Cannot serialize`。
- **定位**：第二次是"读缓存"的路径，说明写进去的值读不回来。
- **根因（两层）**：
  1. 第一层：Redis 缓存默认用 **JDK 序列化**，要求对象 `implements Serializable`；我的 `Job` 是 record，不可序列化 → 换 **JSON 序列化**。
  2. 第二层（换完还炸）：JSON 序列化器会写入类型信息，而我返回值用的是 `Map.of()` / `.toList()` 这类 **JDK 不可变集合**——它们在 Redis 里被记成 `java.util.ImmutableCollections$MapN`，反序列化时**没法实例化** → 改回标准 `HashMap` / `ArrayList`。
- **修复**：value 用 `GenericJackson2JsonRedisSerializer`，key 用 `StringRedisSerializer`，缓存方法一律返回可变集合。
- **防回归**：把两条结论写进代码注释与 README（"缓存值不能用 JDK 序列化""不要用 Map.of()/toList() 做缓存返回值"），并且**本地和 CI 都验证过"第二次请求不出现 SQL 日志"**。
- **可延伸的加分点**：JSON 序列化还有个好处——**redis-cli 里肉眼可读**，排查缓存问题不用先反序列化；而且类结构变化（加字段）不会像 JDK 序列化那样直接反序列化失败。

### STORY 3｜`@EnableCaching` 不是可选项

- **现象**：加完缓存依赖，应用启动直接失败：`required a bean of type 'CacheManager' that could not be found`。
- **根因**：Spring Boot 的 `CacheManager` 自动配置是**条件装配**的，条件之一是 `CacheAspectSupport` 存在——而它由 `@EnableCaching` 引入。光加 `spring-boot-starter-cache` 不够。
- **修复**：在 `CacheConfig` 上加 `@EnableCaching`。
- **一句话总结**："自动配置不是无条件的，条件不满足它就不生效，报错信息只会告诉你缺 bean，不会告诉你缺注解。"

### STORY 4｜限流的降级与维度

- **现象/设计**：限流计数放 Redis；但 Redis 一旦不可用，`INCR` 会抛异常。
- **决策**：**降级为放行 + 打警告日志**，而不是让整个接口 500。理由：限流是"保护性"功能，它的失败不应该比业务本身更严重；但必须留日志，否则被刷了都不知道。
- **维度选择**：一开始只按 IP 限流 → 同一出口 NAT 的多个调用方共享额度，一家刷爆全家 429。改成 **API Key 哈希 + IP**，配额按调用方算；**Key 存哈希不存明文**，因为 Redis key 运维、监控、备份都能看到。
- **可延伸**：固定窗口实现简单但有边界突刺（窗口交界处可能通过 2N 次）；要更平滑换令牌桶/滑动窗口，代价是需要 Lua 脚本保证原子性。**"够用 + 能说清代价"比"上了复杂方案但说不清"更好。**

### STORY 5｜YAML 重复键把配置静默吃掉

- **现象**：写 `docker-compose.yml` 时 `java-api` 服务下写了两个 `environment:` 块（一个放数据源，一个放岗位目录）。
- **根因**：YAML 对同一 mapping 的重复键是"后者覆盖前者"且**不报错**；数据源配置被静默丢掉，容器起来连不上库。
- **修复 + 防回归**：合并成一个 `environment`；并写了一个**严格 YAML 加载器**（自定义 constructor，遇重复键抛错）放进 `test_docker_static.py`，本地没 Docker 也能拦住这类错误。我还专门用一段"故意重复"的 YAML 验证过这个检查真的会失败（不能失败的检查等于没有）。

## 五、高频追问与参考答案

| 追问 | 怎么答 |
|---|---|
| 缓存和数据库怎么保证一致？ | 现状是"60 秒 TTL + 导入后清缓存"的**最终一致**，因为这个场景里岗位数据是人工录入、变化很慢，读旧 60 秒的代价可以接受。要强一致就得在写路径上做"先更新库再删缓存"（Cache-Aside），并接受并发下仍可能短暂不一致。 |
| 为什么不用 Redis 存岗位数据当数据库？ | 岗位数据要按分数过滤、排序、统计（avg/max），这些是关系库擅长的；Redis 做这些要么全量拉到内存排序，要么维护额外索引结构。缓存只放"热点查询结果"，定位清楚。 |
| 连接池大小怎么定？ | 现在是 HikariCP 默认上限 10、连接超时 3 秒。经验起点是"CPU 核数 × 2~4"，但真正的上限来自数据库能扛多少并发连接和 SQL 的单次耗时；要压测后才能定，我没压到那一步，**不编数字**。 |
| 为什么 `ddl-auto=update` 不能上生产？ | 它只会"加表加列"，不会安全地改类型/删列，也没有版本记录和回滚。生产应该用 Flyway/Liquibase 把建表变成可评审、可回滚的迁移脚本。 |
| 为什么限流不用 Nginx/网关做？ | 网关层也能做（更好），但本项目的接口是直接暴露给调用方的；在应用内做的好处是**能和业务身份（API Key）绑定**，也能复用同一套错误格式。真实生产我会两层都做：网关挡住粗粒度洪水，应用内做细粒度配额。 |
| API Key 怎么轮换？ | 现在只支持单 Key（配置注入）。要轮换就得支持"多 Key + 有效期 + 灰度切换"，把 Key 从配置挪到表里，并记录最后使用时间。这是下一步。 |
| 容器为什么多阶段构建？ | 构建镜像要 JDK + Maven（几百 MB），运行只要 JRE。多阶段让最终镜像只带 JRE 和应用 jar；另外先 `COPY pom.xml` 拉依赖，**源码改动不会让依赖层失效**，重复构建省几分钟。 |
| 为什么容器里不用 root？ | 容器逃逸/被攻破时，进程权限越低越好；配合 `-XX:+ExitOnOutOfMemoryError` 让 OOM 时容器退出被重启，而不是半死不活。 |
| `depends_on` 为什么不写 `condition: service_healthy`？ | **恰恰要写**。只写 `depends_on` 只保证容器"起来了"，不保证 MySQL 能连——首次初始化要十几秒，不等健康检查 java-api 会直接启动失败。 |
| 这套东西上线还差什么？ | ①集成测试进 CI（Testcontainers 或 service 容器）②`ddl-auto` 换 Flyway ③多 Key 轮换 + 审计 ④指标与链路追踪（现在只有 Actuator 健康检查）⑤限流与缓存的容量压测。 |

## 六、和其他项目的呼应（面试官常问"这几个项目什么关系"）

- **Python 侧（OfferAgent / RAG）**：AI 能力与业务闭环，负责"把事做成"。
- **Java 侧（java-api）**：对外契约与数据一致性，负责"让别人的系统能稳定调用"。
- **两边的连接点**：`POST /api/rag/search` 是唯一跨语言调用入口，超时策略（连接 3s / 读 60s）和错误语义都在这一层收口。
- **一条真实的数据流**：岗位 JSON（Python 写）→ MySQL（Java 导入）→ Redis（Java 缓存）→ 调用方；将来反转写入方向时，**只有 JobSeeder 和写入接口要改，读路径不动**——这就是当初把它们分层的好处。

## 七、数字速查（都能复现）

| 项 | 值 |
|---|---|
| 单元/切片测试 | `mvn test` → 14 个（3 控制器 + 6 鉴权过滤器 + 5 限流器） |
| 缓存效果 | 同一请求 464ms → **51ms**（第 2 次无 SQL 日志） |
| 缓存 TTL | 岗位 60s / 统计 15s |
| 限流 | 上限 5/分钟时第 6 次 → **429 + Retry-After: 28** |
| 鉴权 | 无/错 Key → **401**；未配置 Key → **503（fail closed）**；`/api/health`、`/actuator/**` 免鉴权 |
| MySQL | 22 行岗位，avg 65，最高 88 |
| Docker 静态校验 | `java-api/test_docker_static.py` → **22/22** |
