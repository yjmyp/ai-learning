package com.yujian.offeragent;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Repository;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.stream.Stream;

/**
 * 岗位库读取：直接读 OfferAgent 的岗位元数据（offeragent/data/jds/*.meta.json）。
 *
 * 为什么用 Java 读同一份数据：Python 侧（Streamlit 工作台）和 Java 侧（对外 API）
 * 面向的调用方不同——前者是本人使用，后者是别的系统要按条件查岗位。
 * 两边读同一份文件，是为了避免"两套数据各写一份"的经典事故。
 */
@Repository
public class JobRepository {

    private static final Logger log = LoggerFactory.getLogger(JobRepository.class);
    private static final String META_SUFFIX = ".meta.json";

    private final Path jdsDir;
    private final ObjectMapper mapper = new ObjectMapper();

    public JobRepository(@Value("${offeragent.jds-dir:../offeragent/data/jds}") String dir) {
        this.jdsDir = Path.of(dir).toAbsolutePath().normalize();
        log.info("岗位库目录：{}（存在={}）", this.jdsDir, Files.isDirectory(this.jdsDir));
    }

    /** 读取全部岗位；目录不存在时返回空列表而不是抛异常（服务不该因为数据目录缺失就起不来）。 */
    public List<Job> findAll() {
        if (!Files.isDirectory(jdsDir)) {
            return List.of();
        }
        List<Job> jobs = new ArrayList<>();
        try (Stream<Path> files = Files.list(jdsDir)) {
            files.filter(p -> p.getFileName().toString().endsWith(META_SUFFIX))
                 .forEach(p -> {
                     Job job = readOne(p);
                     if (job != null) {
                         jobs.add(job);
                     }
                 });
        } catch (IOException e) {
            log.warn("读取岗位目录失败：{}", e.getMessage());
        }
        jobs.sort(Comparator.comparingInt(Job::score).reversed());
        return jobs;
    }

    private Job readOne(Path file) {
        try {
            JsonNode n = mapper.readTree(Files.readString(file));
            return new Job(
                    text(n, "name"),
                    text(n, "title_raw"),
                    text(n, "company"),
                    text(n, "city"),
                    text(n, "salary"),
                    n.path("match_score").asInt(0),
                    text(n, "status"),
                    text(n, "source_url"));
        } catch (Exception e) {
            log.warn("跳过无法解析的岗位文件 {}：{}", file.getFileName(), e.getMessage());
            return null;
        }
    }

    private static String text(JsonNode n, String field) {
        JsonNode v = n.get(field);
        return (v == null || v.isNull()) ? "" : v.asText("");
    }
}
