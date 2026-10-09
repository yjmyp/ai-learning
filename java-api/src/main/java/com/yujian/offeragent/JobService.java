package com.yujian.offeragent;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;

/**
 * 岗位查询服务：走 MySQL，热点结果进 Redis 缓存（TTL 见 CacheConfig）。
 *
 * 缓存键带上查询参数（minScore:limit），否则不同条件的请求会互相污染——
 * 这是缓存最常踩的坑：key 设计不对，返回的结果张冠李戴。
 */
@Service
public class JobService {

    private static final Logger log = LoggerFactory.getLogger(JobService.class);

    private final JobDbRepository db;

    public JobService(JobDbRepository db) {
        this.db = db;
    }

    /** 按最低分过滤岗位；同样的参数第二次调用直接命中 Redis，不再打 MySQL。 */
    @Cacheable(cacheNames = "jobs", key = "#minScore + ':' + #limit")
    @Transactional(readOnly = true)
    public List<Job> list(int minScore, int limit) {
        log.info("查 MySQL：minScore={} limit={}（没走缓存）", minScore, limit);
        // 注意：这里必须回 ArrayList，不能用 .toList() / List.of()。
        // JSON 缓存序列化器会写入类型信息（["java.util.ImmutableCollections$ListN", [...]]），
        // 读回来时 JDK 不可变集合没法实例化，会抛 SerializationException —— 实测 500 过。
        return db.findByScoreGreaterThanEqualOrderByScoreDesc(minScore).stream()
                .limit(limit)
                .map(JobEntity::toJob)
                .collect(java.util.stream.Collectors.toCollection(java.util.ArrayList::new));
    }

    /** 统计信息：给 /api/health 与看板用（平均分、达标岗位数）。 */
    @Cacheable(cacheNames = "jobStats", key = "'all'")
    @Transactional(readOnly = true)
    public Map<String, Object> stats() {
        // 同理：用 HashMap 而不是 Map.of()（不可变 Map 反序列化会失败）
        Map<String, Object> m = new java.util.HashMap<>();
        m.put("total", db.count());
        m.put("avgScore", Math.round(db.averageScore() == null ? 0 : db.averageScore()));
        m.put("scoreOver80", db.countAtLeast(80));
        return m;
    }
}
