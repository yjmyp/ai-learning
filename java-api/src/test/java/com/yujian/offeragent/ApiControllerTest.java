package com.yujian.offeragent;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * 接口层测试：覆盖"业务查询可用"和"参数校验返回 400"这两类边界。
 *
 * 为什么专门测 400：写完之后手测发现空 q 曾被我包成 502（下游 422 被当成服务端故障），
 * 这类"状态码语义错"的 bug 只有断言状态码才能守住。
 */
@WebMvcTest(ApiController.class)
@Import(ApiController.class)
class ApiControllerTest {

    @Autowired
    private MockMvc mvc;

    @MockBean
    private JobRepository jobs;

    @Test
    void 岗位查询按分数过滤并返回总数() throws Exception {
        given(jobs.findAll()).willReturn(List.of(
                new Job("job-a", "Agent 开发", "某公司", "南京", "300/天", 88, "待投", "https://example.com/a"),
                new Job("job-b", "AI 应用", "另一家公司", "南京", "", 50, "待投", "")));

        mvc.perform(get("/api/jobs").param("minScore", "80").param("limit", "10"))
           .andExpect(status().isOk())
           .andExpect(jsonPath("$.total").value(2))
           .andExpect(jsonPath("$.returned").value(1))
           .andExpect(jsonPath("$.jobs[0].score").value(88));
    }

    @Test
    void 空问题返回400而不是502() throws Exception {
        mvc.perform(post("/api/rag/search")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"q\":\"\",\"topK\":3}"))
           .andExpect(status().isBadRequest())
           .andExpect(jsonPath("$.error").value("bad_request"));
    }

    @Test
    void topK超范围返回400() throws Exception {
        mvc.perform(post("/api/rag/search")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"q\":\"RAG 是什么\",\"topK\":999}"))
           .andExpect(status().isBadRequest())
           .andExpect(jsonPath("$.error").value("bad_request"));
    }
}
