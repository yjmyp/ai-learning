package com.yujian.offeragent;

import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.MySQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

// 集成测试基类：真起 MySQL + Redis 容器
//
// 为什么要有集成测试：单元测试里 MySQL 和 Redis 都是 mock，只能证明"代码逻辑对"，
// 证明不了"接上真库真缓存能跑"——缓存序列化、事务、连接池这类问题只在真环境暴露。
// 这正是我本地踩坑的过程：单元测试全绿，一接真 Redis 就 500。
//
// 两个关键处理：
//  1. disabledWithoutDocker = true：本机没 Docker 时**自动跳过**而不是失败，
//     否则本地 mvn test 会因为环境缺失而报红；CI runner 上有 Docker，会真跑。
//  2. 岗位数据自带夹具：offeragent/data/ 是 gitignore 的（隐私数据不入库），
//     CI 上并不存在，所以这里临时生成两份 meta.json 并指过去——测试不依赖本地数据。
// management.prometheus.metrics.export.enabled=true 不能省：
// Spring Boot 的测试上下文默认**关闭指标导出**（条件评估里写的是
// "management.defaults.metrics.export.enabled is considered false"），
// 于是 PrometheusMeterRegistry 根本不创建，/actuator/prometheus 直接 404。
// 这个坑只在测试里出现（本地跑 jar 是 3 个端点、prometheus 200），
// CI 上集成测试第一次跑就撞到了。显式打开导出后测试上下文与生产行为一致。
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "management.prometheus.metrics.export.enabled=true")
@Testcontainers(disabledWithoutDocker = true)
public abstract class IntegrationTestBase {

    @Container
    @ServiceConnection
    static final MySQLContainer<?> MYSQL = new MySQLContainer<>("mysql:8.0")
            .withDatabaseName("offeragent")
            .withUsername("offeragent")
            .withPassword("offeragent123");

    @Container
    @ServiceConnection
    static final GenericContainer<?> REDIS =
            new GenericContainer<>("redis:7-alpine").withExposedPorts(6379);

    static final String TEST_API_KEY = "integration-test-key";

    private static Path fixtureDir;

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry registry) {
        registry.add("offeragent.jds-dir", IntegrationTestBase::jobFixtureDir);
        registry.add("offeragent.api-key", () -> TEST_API_KEY);
    }

    // 生成岗位夹具（只在第一次调用时写盘）
    static synchronized String jobFixtureDir() {
        if (fixtureDir != null) {
            return fixtureDir.toString();
        }
        try {
            Path dir = Files.createTempDirectory("oa-jobs-fixture");
            Files.writeString(dir.resolve("job-high.meta.json"),
                    "{\"name\":\"job-high\",\"title_raw\":\"Agent 开发实习生\",\"company\":\"甲科技\","
                            + "\"city\":\"南京\",\"salary\":\"300/天\",\"match_score\":88,\"status\":\"待投\","
                            + "\"source_url\":\"https://example.com/high\"}");
            Files.writeString(dir.resolve("job-low.meta.json"),
                    "{\"name\":\"job-low\",\"title_raw\":\"后端实习生\",\"company\":\"乙信息\","
                            + "\"city\":\"上海\",\"salary\":\"200/天\",\"match_score\":40,\"status\":\"待投\","
                            + "\"source_url\":\"https://example.com/low\"}");
            fixtureDir = dir;
            return dir.toString();
        } catch (IOException e) {
            throw new IllegalStateException("生成岗位夹具失败", e);
        }
    }
}
