package com.yujian.offeragent;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.cache.CacheManager;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * 启动时把岗位数据从 JSON 文件导入 MySQL（只在表为空时导）。
 *
 * 为什么保留文件作为数据源：Python 侧的 OfferAgent 仍在写这些 JSON，
 * 迁移期间两边都要能读到同一份岗位；等 Java 侧接管写入后再反转数据流向。
 * 「表非空就跳过」是为了让重启不会覆盖线上状态（比如用户改过的 status）。
 */
@Component
public class JobSeeder implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(JobSeeder.class);

    private final JobRepository fileSource;
    private final JobDbRepository db;
    private final CacheManager cacheManager;

    public JobSeeder(JobRepository fileSource, JobDbRepository db, CacheManager cacheManager) {
        this.fileSource = fileSource;
        this.db = db;
        this.cacheManager = cacheManager;
    }

    @Override
    public void run(ApplicationArguments args) {
        long n = db.count();
        if (n > 0) {
            log.info("岗位表已有 {} 行，跳过导入", n);
            return;
        }
        List<Job> jobs = fileSource.findAll();
        if (jobs.isEmpty()) {
            log.warn("岗位 JSON 目录为空，没东西可导入");
            return;
        }
        db.saveAll(jobs.stream().map(JobEntity::new).toList());
        var cache = cacheManager.getCache("jobs");
        if (cache != null) {
            cache.clear();          // 导入后清缓存，避免读到导之前的空列表
        }
        log.info("已导入岗位 {} 行（从 JSON 文件 → MySQL）", db.count());
    }
}
