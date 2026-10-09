package com.yujian.offeragent;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import static org.assertj.core.api.Assertions.assertThat;

// API Key 鉴权单测：覆盖放行、拒绝、fail-closed、免鉴权路径、时序安全比较。
class ApiKeyAuthFilterTest {

    private MockHttpServletResponse run(ApiKeyAuthFilter filter, String path, String key) throws Exception {
        var req = new MockHttpServletRequest("GET", path);
        if (key != null) {
            req.addHeader("X-API-Key", key);
        }
        var resp = new MockHttpServletResponse();
        filter.doFilter(req, resp, new MockFilterChain());
        return resp;
    }

    @Test
    void 正确的Key放行() throws Exception {
        var resp = run(new ApiKeyAuthFilter("secret-key"), "/api/jobs", "secret-key");
        assertThat(resp.getStatus()).isEqualTo(200);
    }

    @Test
    void 缺少Key返回401() throws Exception {
        var resp = run(new ApiKeyAuthFilter("secret-key"), "/api/jobs", null);
        assertThat(resp.getStatus()).isEqualTo(401);
        assertThat(resp.getContentAsString()).contains("unauthorized");
    }

    @Test
    void 错误的Key返回401() throws Exception {
        var resp = run(new ApiKeyAuthFilter("secret-key"), "/api/jobs", "wrong-key");
        assertThat(resp.getStatus()).isEqualTo(401);
    }

    @Test
    void 服务端没配Key时failClosed返回503() throws Exception {
        // 关键安全行为：配置漏了必须拒绝，不能默认放行
        var resp = run(new ApiKeyAuthFilter(""), "/api/jobs", "any");
        assertThat(resp.getStatus()).isEqualTo(503);
        assertThat(resp.getContentAsString()).contains("api_key_not_configured");
    }

    @Test
    void 免鉴权路径不需要Key() throws Exception {
        assertThat(run(new ApiKeyAuthFilter("secret-key"), "/api/health", null).getStatus()).isEqualTo(200);
        assertThat(run(new ApiKeyAuthFilter("secret-key"), "/actuator/health", null).getStatus()).isEqualTo(200);
    }

    @Test
    void 定长比较对不同长度与相似前缀都返回false() {
        assertThat(ApiKeyAuthFilter.constantTimeEquals("abc", "abc")).isTrue();
        assertThat(ApiKeyAuthFilter.constantTimeEquals("abc", "abd")).isFalse();
        assertThat(ApiKeyAuthFilter.constantTimeEquals("abc", "abcd")).isFalse();
        assertThat(ApiKeyAuthFilter.constantTimeEquals("", "")).isTrue();
    }
}
