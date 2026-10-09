package com.yujian.offeragent;

import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.mock;

// 限流器单测：不依赖真实 Redis，直接控制 INCR 的返回值来验证边界与响应头。
class RateLimitInterceptorTest {

    @SuppressWarnings("unchecked")
    private ValueOperations<String, String> ops(StringRedisTemplate redis, Long counterValue) {
        ValueOperations<String, String> ops = mock(ValueOperations.class);
        given(redis.opsForValue()).willReturn(ops);
        given(ops.increment(anyString())).willReturn(counterValue);
        return ops;
    }

    @Test
    void 未超限时放行并回填剩余额度头() throws Exception {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ops(redis, 3L);
        var interceptor = new RateLimitInterceptor(redis, 30);
        var req = new MockHttpServletRequest("GET", "/api/jobs");
        var resp = new MockHttpServletResponse();

        assertThat(interceptor.preHandle(req, resp, new Object())).isTrue();
        assertThat(resp.getHeader("X-RateLimit-Remaining")).isEqualTo("27");
        assertThat(resp.getStatus()).isEqualTo(200);
    }

    @Test
    void 超限时返回429并带RetryAfter() throws Exception {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        ops(redis, 31L);                       // 上限 30，第 31 次应被拦
        var interceptor = new RateLimitInterceptor(redis, 30);
        var req = new MockHttpServletRequest("GET", "/api/jobs");
        var resp = new MockHttpServletResponse();

        assertThat(interceptor.preHandle(req, resp, new Object())).isFalse();
        assertThat(resp.getStatus()).isEqualTo(429);
        assertThat(resp.getHeader("Retry-After")).isNotNull();
        assertThat(resp.getContentAsString()).contains("rate_limited");
    }

    @Test
    void Redis不可用时降级放行而不是把业务带崩() throws Exception {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        given(redis.opsForValue()).willThrow(new RuntimeException("connection refused"));
        var interceptor = new RateLimitInterceptor(redis, 30);
        var req = new MockHttpServletRequest("GET", "/api/jobs");
        var resp = new MockHttpServletResponse();

        assertThat(interceptor.preHandle(req, resp, new Object())).isTrue();
    }

    @Test
    void 限流维度取XForwardedFor的第一段() {
        var req = new MockHttpServletRequest("GET", "/api/jobs");
        req.addHeader("X-Forwarded-For", "203.0.113.9, 10.0.0.1");
        assertThat(RateLimitInterceptor.clientIp(req)).isEqualTo("203.0.113.9");
    }
}
