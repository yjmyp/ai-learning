package com.yujian.offeragent;

/**
 * 岗位视图对象（record：Java 16+ 的不可变数据载体，省掉一堆 getter/setter）。
 *
 * @param score 匹配分（结构化打分结果，来自 Python 侧算好的值）
 */
public record Job(
        String name,
        String title,
        String company,
        String city,
        String salary,
        int score,
        String status,
        String sourceUrl) {
}
