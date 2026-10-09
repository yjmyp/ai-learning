package com.yujian.offeragent;

import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cache.Cache;
import org.springframework.cache.CacheManager;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

/**
 * 岗位查询服务：走 MySQL，热点结果进 Redis 缓存（TTL 见 CacheConfig）。
 *
 * 缓存键带上查询参数（minScore:limit），否则不同条件的请求会互相污染——
 * 这是缓存最常踩的坑：key 设计不对，返回的结果张冠李戴。
 *
 * 为什么不用 @Cacheable 而手写 cache-aside：
 *  1. @Cacheable 命中时**根本不进方法体**，缓存命中/未命中就无从埋点，
 *     而"缓存命中率"恰恰是缓存最该看的指标；
 *  2. 手写之后读写路径都看得见，出问题时不用猜框架在背后做了什么。
 * 代价是多几行代码——我认为值。
 */
@Service
public class JobService {

    private static final Logger log = LoggerFactory.getLogger(JobService.class);
    private static final String CACHE_JOBS = "jobs";
    private static final String CACHE_STATS = "jobStats";

    private final JobDbRepository db;
    private final CacheManager cacheManager;
    private final MeterRegistry registry;

    public JobService(JobDbRepository db, CacheManager cacheManager, MeterRegistry registry) {
        this.db = db;
        this.cacheManager = cacheManager;
        this.registry = registry;
    }

    /** 按最低分过滤岗位；同样参数第二次调用直接命中 Redis，不再打 MySQL。 */
    @Transactional(readOnly = true)
    public List<Job> list(int minScore, int limit) {
        return readThrough(CACHE_JOBS, minScore + ":" + limit, () -> {
            log.info("查 MySQL：minScore={} limit={}（没走缓存）", minScore, limit);
            // 注意：这里必须回 ArrayList，不能用 .toList() / List.of()。
            // JSON 缓存序列化器会写入类型信息（["java.util.ImmutableCollections$ListN", [...]]），
            // 读回来时 JDK 不可变集合没法实例化，会抛 SerializationException —— 实测 500 过。
            return db.findByScoreGreaterThanEqualOrderByScoreDesc(minScore).stream()
                    .limit(limit)
                    .map(JobEntity::toJob)
                    .collect(java.util.stream.Collectors.toCollection(ArrayList::new));
        });
    }

    /** 统计信息：给 /api/health 与看板用（平均分、达标岗位数）。 */
    @Transactional(readOnly = true)
    public Map<String, Object> stats() {
        return readThrough(CACHE_STATS, "all", () -> {
            // 同理：用 HashMap 而不是 Map.of()（不可变 Map 反序列化会失败）
            Map<String, Object> m = new HashMap<>();
            m.put("total", db.count());
            m.put("avgScore", Math.round(db.averageScore() == null ? 0 : db.averageScore()));
            m.put("scoreOver80", db.countAtLeast(80));
            return m;
        });
    }

    /**
     * 统一的 cache-aside 读路径，并埋三个指标：
     *   oa.cache.hits / oa.cache.misses（带 cache 标签）→ 命中率
     *   oa.db.query（Timer）→ 真正打到数据库的耗时
     */
    @SuppressWarnings("unchecked")
    private <T> T readThrough(String cacheName, String key, Supplier<T> loader) {
        Cache cache = cacheManager.getCache(cacheName);
        if (cache != null) {
            Cache.ValueWrapper wrapper = cache.get(key);
            if (wrapper != null && wrapper.get() != null) {
                registry.counter("oa.cache.hits", "cache", cacheName).increment();
                return (T) wrapper.get();
            }
        }
        registry.counter("oa.cache.misses", "cache", cacheName).increment();
        T value = Timer.builder("oa.db.query").tag("query", cacheName).register(registry)
                .record(loader);
        if (cache != null) {
            cache.put(key, value);
        }
        return value;
    }
}
