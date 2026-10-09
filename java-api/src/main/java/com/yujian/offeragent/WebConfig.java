package com.yujian.offeragent;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

// 把限流拦截器挂到 /api/** 上：健康检查也限流（防止有人拿它当免费探活刷），
// 但 Actuator 的 /actuator/** 不限，方便部署平台的探针使用。
@Configuration
public class WebConfig implements WebMvcConfigurer {

    private final RateLimitInterceptor rateLimit;

    public WebConfig(RateLimitInterceptor rateLimit) {
        this.rateLimit = rateLimit;
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(rateLimit).addPathPatterns("/api/**");
    }
}
