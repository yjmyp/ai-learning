package com.yujian.offeragent;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;

// 基于 Redis 的固定窗口限流：每个 IP 每分钟最多 N 次。
//
// 为什么用 Redis 而不是进程内计数器：进程内计数只对单实例有效，
// 一旦水平扩成两个实例，实际放行量翻倍——限流形同没有。
// 用 Redis 的 INCR 计数，多实例共享同一个窗口。
//
// 为什么 key 里带分钟数：固定窗口实现最简单，防刷这个目标上够用；
// 令牌桶更平滑，但要额外 Lua 脚本保证原子性，等真有精度需求再换。
@Component
public class RateLimitInterceptor implements HandlerInterceptor {

    private static final Logger log = LoggerFactory.getLogger(RateLimitInterceptor.class);
    private static final String PREFIX = "oa:ratelimit:";

    private final StringRedisTemplate redis;
    private final int limitPerMinute;

    public RateLimitInterceptor(StringRedisTemplate redis,
                               @Value("${offeragent.rate-limit-per-minute:30}") int limitPerMinute) {
        this.redis = redis;
        this.limitPerMinute = limitPerMinute;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
            throws Exception {
        if (limitPerMinute <= 0) {
            return true;                       // 配 0 = 关闭限流
        }
        String ip = clientIp(request);
        long minute = Instant.now().getEpochSecond() / 60;
        String key = PREFIX + ip + ":" + minute;
        try {
            Long n = redis.opsForValue().increment(key);
            if (n != null && n == 1L) {
                redis.expire(key, Duration.ofSeconds(70));   // 比窗口略长，避免边界丢计数
            }
            long used = n == null ? 0 : n;
            response.setHeader("X-RateLimit-Limit", String.valueOf(limitPerMinute));
            response.setHeader("X-RateLimit-Remaining", String.valueOf(Math.max(limitPerMinute - used, 0)));
            if (used > limitPerMinute) {
                long retryAfter = 60 - (Instant.now().getEpochSecond() % 60);
                response.setStatus(429);
                response.setHeader("Retry-After", String.valueOf(retryAfter));
                response.setContentType("application/json;charset=UTF-8");
                String body = String.format(
                        "{\"error\":\"rate_limited\",\"message\":\"每分钟最多 %d 次，请 %d 秒后重试\"}",
                        limitPerMinute, retryAfter);
                response.getOutputStream().write(body.getBytes(StandardCharsets.UTF_8));
                log.info("限流触发：ip={} 第 {} 次", ip, used);
                return false;
            }
        } catch (Exception e) {
            // Redis 挂了不能把业务一起带崩：降级为不限流，但留下日志
            log.warn("限流计数失败（降级放行）：{}", e.getMessage());
        }
        return true;
    }

    // 取真实客户端 IP；只取 XFF 第一段作为限流维度
    static String clientIp(HttpServletRequest request) {
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            return xff.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
