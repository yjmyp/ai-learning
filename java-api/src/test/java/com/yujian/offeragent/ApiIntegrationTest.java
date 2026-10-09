package com.yujian.offeragent;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.mock.mockito.SpyBean;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

// 真 MySQL + 真 Redis 的集成测试：验证"启动导入 → 缓存命中 → 鉴权"这条完整链路。
class ApiIntegrationTest extends IntegrationTestBase {

    @Autowired
    JobService jobService;
    @Autowired
    JdbcTemplate jdbc;
    @Autowired
    StringRedisTemplate redis;
    @Autowired
    TestRestTemplate http;

    // 用 Spy 统计"真正打到数据库"的次数：缓存命中时不应该再查库
    @SpyBean
    JobDbRepository repository;

    @Test
    void 启动时把夹具岗位导入MySQL() {
        Integer rows = jdbc.queryForObject("select count(*) from job", Integer.class);
        assertThat(rows).isEqualTo(2);
        List<Job> all = jobService.list(0, 10);
        assertThat(all).extracting(Job::name).containsExactly("job-high", "job-low");   // 按分数倒序
    }

    @Test
    void 相同参数第二次查走Redis不再打MySQL() {
        redis.delete("jobs::70:5");
        verify(repository, times(0)).findByScoreGreaterThanEqualOrderByScoreDesc(70);

        List<Job> first = jobService.list(70, 5);      // 未命中 → 查库 → 写缓存
        assertThat(first).hasSize(1);
        assertThat(redis.hasKey("jobs::70:5")).isTrue();

        List<Job> second = jobService.list(70, 5);     // 命中缓存
        assertThat(second).isEqualTo(first);
        verify(repository, times(1)).findByScoreGreaterThanEqualOrderByScoreDesc(70);
    }

    @Test
    void 接口层鉴权_无Key401_带Key200() {
        var noKey = http.getForEntity("/api/jobs", String.class);
        assertThat(noKey.getStatusCode().value()).isEqualTo(401);

        var headers = new org.springframework.http.HttpHeaders();
        headers.add("X-API-Key", TEST_API_KEY);
        var withKey = http.exchange("/api/jobs", org.springframework.http.HttpMethod.GET,
                new org.springframework.http.HttpEntity<Void>(null, headers), String.class);
        assertThat(withKey.getStatusCode().value()).isEqualTo(200);
        assertThat(withKey.getBody()).contains("job-high");
    }

    @Test
    void 健康检查与Prometheus指标可用() {
        var health = http.getForEntity("/api/health", String.class);
        assertThat(health.getStatusCode().value()).isEqualTo(200);
        assertThat(health.getBody()).contains("\"mysql\":\"ok\"");

        jobService.list(0, 1);      // 制造一次未命中
        jobService.list(0, 1);      // 制造一次命中

        var prom = http.getForEntity("/actuator/prometheus", String.class);
        assertThat(prom.getStatusCode().value()).isEqualTo(200);
        assertThat(prom.getBody())
                .contains("oa_cache_hits_total")     // 缓存命中计数
                .contains("oa_cache_misses_total")   // 缓存未命中计数
                .contains("oa_db_query_seconds_count");   // 数据库查询耗时
    }
}
