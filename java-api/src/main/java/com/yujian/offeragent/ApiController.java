package com.yujian.offeragent;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestClient;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

/**
 * 对外接口。
 *
 * 三条设计原则：
 *  1. 业务查询（岗位库）在 Java 侧做——调用方要的是稳定接口和分页/过滤，不是模型能力；
 *  2. AI 能力转发给 Python 服务——不重写模型链路，只做协议转换与超时控制；
 *  3. 入参在边界处校验（q 长度、topK 范围），别让脏参数传到下游模型服务。
 */
@RestController
@RequestMapping("/api")
public class ApiController {

    private static final Logger log = LoggerFactory.getLogger(ApiController.class);

    private final JobRepository jobs;
    private final RestClient rag;
    private final String ragApiKey;

    public ApiController(JobRepository jobs,
                         @Value("${rag.base-url:http://127.0.0.1:8600}") String ragBaseUrl,
                         @Value("${rag.api-key:}") String ragApiKey) {
        this.jobs = jobs;
        this.ragApiKey = ragApiKey;
        // 统一在这里配超时：下游是模型服务，慢是常态，但不能一直挂着
        var factory = new org.springframework.http.client.SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(3000);
        factory.setReadTimeout(60000);
        this.rag = RestClient.builder()
                .baseUrl(ragBaseUrl)
                .requestFactory(factory)
                .build();
    }

    /** 健康检查：报告本服务与下游 Python 服务的可达性。 */
    @GetMapping("/health")
    public Map<String, Object> health() {
        String downstream = "unreachable";
        try {
            ResponseEntity<Map> r = rag.get().uri("/live")
                    .retrieve().toEntity(Map.class);
            downstream = "ok(" + r.getStatusCode().value() + ")";
        } catch (Exception e) {
            downstream = "down:" + e.getClass().getSimpleName();
        }
        return Map.of(
                "service", "offeragent-api",
                "status", "up",
                "javaVersion", System.getProperty("java.version"),
                "pythonAiService", downstream,
                "time", OffsetDateTime.now().toString());
    }

    /** 查询岗位库，可按最低匹配分过滤（业务接口，不碰模型）。 */
    @GetMapping("/jobs")
    public Map<String, Object> listJobs(
            @RequestParam(name = "minScore", defaultValue = "0") int minScore,
            @RequestParam(name = "limit", defaultValue = "20") @Min(1) @Max(100) int limit) {
        List<Job> all = jobs.findAll();
        List<Job> filtered = all.stream()
                .filter(j -> j.score() >= minScore)
                .limit(limit)
                .toList();
        return Map.of("total", all.size(), "returned", filtered.size(), "jobs", filtered);
    }

    /** RAG 检索：校验入参后转发给 Python 服务（AI 能力不在 Java 侧重写）。 */
    @PostMapping(value = "/rag/search", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<?> ragSearch(@Valid @RequestBody RagQuery query) {
        var body = Map.of("q", query.q().trim(), "top_k", query.topK());
        try {
            var spec = rag.post().uri("/search").contentType(MediaType.APPLICATION_JSON).body(body);
            Map<?, ?> result = (ragApiKey == null || ragApiKey.isBlank())
                    ? spec.retrieve().body(Map.class)
                    : spec.header("X-API-Key", ragApiKey).retrieve().body(Map.class);
            return ResponseEntity.ok(result);
        } catch (org.springframework.web.client.RestClientResponseException e) {
            // 下游返回 4xx/5xx：这是调用方的问题或下游的业务错误，原样透传状态码，
            // 不能统一报成 502——踩过：空 q 被下游判 422，我这边包装成 502，
            // 结果调用方以为是我挂了，去查错方向。
            log.info("下游返回 {}：{}", e.getStatusCode(), e.getResponseBodyAsString());
            return ResponseEntity.status(e.getStatusCode()).body(Map.of(
                    "error", "upstream_rejected",
                    "status", e.getStatusCode().value(),
                    "detail", e.getResponseBodyAsString()));
        } catch (org.springframework.web.client.ResourceAccessException e) {
            log.warn("连不上下游：{}", e.getMessage());
            return ResponseEntity.status(502).body(Map.of(
                    "error", "upstream_unavailable",
                    "message", "Python 检索服务不可用：" + e.getMessage()));
        } catch (Exception e) {
            log.warn("转发检索失败：{}", e.getMessage());
            return ResponseEntity.status(500).body(Map.of(
                    "error", "internal_error",
                    "message", e.getMessage()));
        }
    }

    /** 参数校验失败统一返回 400 + 字段级说明（而不是 500/502 或一坨堆栈）。 */
    @ExceptionHandler(org.springframework.web.bind.MethodArgumentNotValidException.class)
    public ResponseEntity<?> onInvalid(org.springframework.web.bind.MethodArgumentNotValidException e) {
        var fields = e.getBindingResult().getFieldErrors().stream()
                .map(f -> f.getField() + ": " + f.getDefaultMessage())
                .toList();
        return ResponseEntity.badRequest().body(Map.of(
                "error", "bad_request", "fields", fields));
    }

    @ExceptionHandler({IllegalArgumentException.class,
                       org.springframework.http.converter.HttpMessageNotReadableException.class})
    public ResponseEntity<?> onBadInput(Exception e) {
        return ResponseEntity.badRequest().body(Map.of(
                "error", "bad_request", "message", String.valueOf(e.getMessage())));
    }

    /** 检索入参：在边界处就把长度和范围卡住。 */
    public record RagQuery(
            @NotBlank(message = "q 不能为空") String q,
            @Min(value = 1, message = "topK 最小 1")
            @Max(value = 50, message = "topK 最大 50") int topK) {

        public RagQuery {
            if (q != null && q.length() > 2000) {
                throw new IllegalArgumentException("q 长度不能超过 2000");
            }
            if (topK == 0) {
                topK = 5;      // 不传时给默认值，避免使用方必须知道我们的默认参数
            }
        }
    }
}
