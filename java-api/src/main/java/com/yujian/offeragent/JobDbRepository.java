package com.yujian.offeragent;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

/**
 * 岗位表的数据访问层。
 *
 * 注意这里继承 JpaRepository 就够了，不用写实现：单表条件查询交给方法名派生
 * （findByScoreGreaterThanEqualOrderByScoreDesc）比手写 SQL 更难出错，
 * 也顺带把"排序逻辑"固定在一处，不会两个地方写得不一样。
 */
public interface JobDbRepository extends JpaRepository<JobEntity, String> {

    List<JobEntity> findByScoreGreaterThanEqualOrderByScoreDesc(int minScore);

    @Query("select avg(j.score) from JobEntity j")
    Double averageScore();

    @Query("select count(j) from JobEntity j where j.score >= :min")
    long countAtLeast(@Param("min") int min);
}
