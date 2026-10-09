package com.yujian.offeragent;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;

// 对外接口的 API Key 鉴权（放在过滤器里，不用会话/表单登录）。
//
// 三条设计取舍：
//  1. 用 API Key 而不是 JWT：调用方是"系统对系统"（别人的服务调我的接口），
//     没有用户登录态要维护，JWT 的签发/刷新/撤销机制在这里是纯负担。
//  2. 比较用 constantTimeEquals：普通 equals 会在第一个不同字符处返回，
//     攻击者能按耗时逐字节猜出 key（时序攻击）。MessageDigest.isEqual 是定长的。
//  3. 没配 key 就"拒绝服务"（fail closed）：宁可服务不可用，也不能默认放开——
//     配置漏了却继续放行，等于把接口裸奔，而且没人会立刻发现。
@Component
public class ApiKeyAuthFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(ApiKeyAuthFilter.class);
    private static final String HEADER = "X-API-Key";

    // 免鉴权路径：健康检查（部署平台探针要用）、以及 /api/health（对本服务自身的探活）
    private static final List<String> PUBLIC_PATHS = List.of("/api/health");

    private final String expectedKey;

    public ApiKeyAuthFilter(@Value("${offeragent.api-key:}") String expectedKey) {
        this.expectedKey = expectedKey == null ? "" : expectedKey.trim();
        if (this.expectedKey.isEmpty()) {
            log.error("未配置 offeragent.api-key：受保护接口将全部返回 503（fail closed）。"
                    + "本地开发请设 OFFERAGENT_API_KEY，部署请用环境变量注入。");
        }
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String path = request.getRequestURI();
        if (isPublic(path) || "OPTIONS".equalsIgnoreCase(request.getMethod())) {
            chain.doFilter(request, response);      // CORS 预检不带自定义头，必须放行
            return;
        }
        if (expectedKey.isEmpty()) {
            writeJson(response, 503, "api_key_not_configured",
                    "服务端未配置 API Key，已拒绝请求（fail closed）");
            return;
        }
        String provided = request.getHeader(HEADER);
        if (provided == null || !constantTimeEquals(provided.trim(), expectedKey)) {
            log.info("鉴权失败：path={} ip={} 是否带 key={}", path,
                    request.getRemoteAddr(), provided != null);
            writeJson(response, 401, "unauthorized", "缺少或错误的 " + HEADER);
            return;
        }
        chain.doFilter(request, response);
    }

    private static boolean isPublic(String path) {
        return PUBLIC_PATHS.stream().anyMatch(path::equals)
                || path.startsWith("/actuator/");
    }

    /** 定长比较，避免时序攻击。 */
    static boolean constantTimeEquals(String a, String b) {
        return MessageDigest.isEqual(a.getBytes(StandardCharsets.UTF_8),
                                     b.getBytes(StandardCharsets.UTF_8));
    }

    private static void writeJson(HttpServletResponse response, int status, String error, String message)
            throws IOException {
        response.setStatus(status);
        response.setContentType("application/json;charset=UTF-8");
        response.getWriter().write(String.format(
                "{\"error\":\"%s\",\"message\":\"%s\"}", error, message));
    }
}
