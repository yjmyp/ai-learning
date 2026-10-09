package com.yujian.offeragent;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/**
 * 岗位表。
 *
 * 为什么用岗位名当主键（而不是自增 id）：岗位名是天然唯一键（`Agent开发（实习）-457029`），
 * 用它做 PK 让"重新导入"变成幂等操作——同一份 JSON 导十次，结果还是那些行，
 * 不需要额外写去重逻辑。自增 id 反而要再加唯一索引才能达到同样效果。
 */
@Entity
@Table(name = "job")
public class JobEntity {

    @Id
    @Column(length = 80, nullable = false)
    private String name;

    @Column(length = 120)
    private String title;

    @Column(length = 120)
    private String company;

    @Column(length = 60)
    private String city;

    @Column(length = 60)
    private String salary;

    @Column(nullable = false)
    private int score;

    @Column(length = 30)
    private String status;

    @Column(name = "source_url", length = 512)
    private String sourceUrl;

    protected JobEntity() {
        // JPA 需要无参构造
    }

    public JobEntity(Job job) {
        this.name = job.name();
        this.title = job.title();
        this.company = job.company();
        this.city = job.city();
        this.salary = job.salary();
        this.score = job.score();
        this.status = job.status();
        this.sourceUrl = job.sourceUrl();
    }

    public Job toJob() {
        return new Job(name, title, company, city, salary, score, status, sourceUrl);
    }

    public String getName() {
        return name;
    }

    public int getScore() {
        return score;
    }

    public void setScore(int score) {
        this.score = score;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
