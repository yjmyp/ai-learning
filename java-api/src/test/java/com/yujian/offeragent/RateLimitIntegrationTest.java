package com.yujian.offeragent;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.test.context.TestPropertySource;

import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

// 限流集成测试：真 Redis 计数，上限压到 2 次/分钟便于在测试里触发。
// 单独一个类是因为限流上限是启动期属性，没法在同一个 Spring 上下文里按用例改。
@TestPropertySource(properties = "offeragent.rate-limit-per-minute=2")
class RateLimitIntegrationTest extends IntegrationTestBase {

    @Autowired
    TestRestTemplate http;
    @Autowired
    StringRedisTemplate redis;

    @Test
    void 超过上限返回429且计数落在Redis里() {
        // 清掉本分钟的计数，避免与其他用例互相影响
        Set<String> keys = redis.keys("oa:ratelimit:*");
        if (keys != null && !keys.isEmpty()) {
            redis.delete(keys);
        }
        var headers = new HttpHeaders();
        headers.add("X-API-Key", TEST_API_KEY);
        var entity = new HttpEntity<Void>(null, headers);

        ResponseEntity<String> first = http.exchange("/api/jobs?limit=1", HttpMethod.GET, entity, String.class);
        ResponseEntity<String> second = http.exchange("/api/jobs?limit=1", HttpMethod.GET, entity, String.class);
        ResponseEntity<String> third = http.exchange("/api/jobs?limit=1", HttpMethod.GET, entity, String.class);

        assertThat(first.getStatusCode().value()).isEqualTo(200);
        assertThat(first.getHeaders().getFirst("X-RateLimit-Limit")).isEqualTo("2");
        assertThat(second.getStatusCode().value()).isEqualTo(200);
        assertThat(third.getStatusCode().value()).isEqualTo(429);
        assertThat(third.getHeaders().getFirst("Retry-After")).isNotNull();
        assertThat(third.getBody()).contains("rate_limited");

        // 计数确实写在 Redis（key 里是 Key 哈希 + IP，不含明文 Key）
        Set<String> after = redis.keys("oa:ratelimit:*");
        assertThat(after).isNotEmpty();
        assertThat(String.join(",", after)).doesNotContain(TEST_API_KEY);
    }
}
