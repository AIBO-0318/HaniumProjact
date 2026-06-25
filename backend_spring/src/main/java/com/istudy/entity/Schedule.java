package com.istudy.entity;

import jakarta.persistence.*;

import java.time.LocalDateTime;

/** 사용자 학습 일정. 테이블: schedules */
@Entity
@Table(name = "schedules")
public class Schedule {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "user_id", nullable = false)
    private Integer userId;

    @Column(nullable = false, length = 10)
    private String date;            // YYYY-MM-DD

    @Column(name = "start_time", length = 5)
    private String startTime;       // HH:MM

    @Column(name = "end_time", length = 5)
    private String endTime;         // HH:MM

    @Column(nullable = false, length = 200)
    private String title;

    @Column(columnDefinition = "text")
    private String memo;

    @Column(length = 20)
    private String color = "blue";

    @Column(name = "is_done", nullable = false)
    private Integer isDone = 0;     // 0=미완료, 1=완료

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    void prePersist() {
        if (createdAt == null) createdAt = LocalDateTime.now();
        if (isDone == null) isDone = 0;
        if (color == null) color = "blue";
    }

    public Integer getId() { return id; }
    public void setId(Integer id) { this.id = id; }
    public Integer getUserId() { return userId; }
    public void setUserId(Integer userId) { this.userId = userId; }
    public String getDate() { return date; }
    public void setDate(String date) { this.date = date; }
    public String getStartTime() { return startTime; }
    public void setStartTime(String startTime) { this.startTime = startTime; }
    public String getEndTime() { return endTime; }
    public void setEndTime(String endTime) { this.endTime = endTime; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getMemo() { return memo; }
    public void setMemo(String memo) { this.memo = memo; }
    public String getColor() { return color; }
    public void setColor(String color) { this.color = color; }
    public Integer getIsDone() { return isDone; }
    public void setIsDone(Integer isDone) { this.isDone = isDone; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
