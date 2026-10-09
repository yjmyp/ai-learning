package com.yujian.offeragent;

import org.springframework.boot.autoconfigure.cache.RedisCacheManagerBuilderCustomizer;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;

/**
 * Redis 缓存配置。
 *
 * 为什么要设 TTL：不做过期时间的缓存等于把"数据不一致"变成一个只增不减的债。
 * 岗位数据变化慢（人工录入），60 秒过期是"足够快"和"不会读出陈旧数据"之间的折中。
 * 统计类缓存（jobStats）设得更短，因为它更容易被关注错。
 */
// @EnableCaching 不能省：Spring Boot 的 CacheManager 自动配置是"条件装配"的，
// 只有开启缓存（@EnableCaching 带来 CacheAspectSupport）它才生效。
// 漏了它，启动时会报 "required a bean of type CacheManager that could not be found"。
@Configuration
@EnableCaching
public class CacheConfig {

    @Bean
    public RedisCacheManagerBuilderCustomizer cacheTtlCustomizer() {
        // 值用 JSON 序列化，不用 JDK 序列化：
        //  1) 默认的 JDK 序列化要求对象 implements Serializable，record 会直接抛
        //     "SerializationException: Cannot serialize"（踩过，500）；
        //  2) JDK 序列化在类结构变化后反序列化会失败，而 JSON 容忍新增字段；
        //  3) JSON 在 redis-cli 里肉眼可读，排查缓存问题时省事。
        RedisCacheConfiguration base = RedisCacheConfiguration.defaultCacheConfig()
                .serializeKeysWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new GenericJackson2JsonRedisSerializer()));
        return builder -> builder
                .withCacheConfiguration("jobs", base.entryTtl(Duration.ofSeconds(60)))
                .withCacheConfiguration("jobStats", base.entryTtl(Duration.ofSeconds(15)));
    }
}
