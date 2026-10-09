package com.yujian.offeragent;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * java-api 启动类。
 *
 * 这一层只做三件事：提供业务接口、校验入参、把 AI 请求转发给 Python 服务。
 * 把"业务接口"和"模型调用"拆成两个进程，是为了让模型那侧能独立扩缩容
 * （Python 侧吃 CPU/GPU，Java 侧吃并发连接，两者的扩容策略不一样）。
 */
@SpringBootApplication
public class ApiApplication {

    public static void main(String[] args) {
        SpringApplication.run(ApiApplication.class, args);
    }
}
