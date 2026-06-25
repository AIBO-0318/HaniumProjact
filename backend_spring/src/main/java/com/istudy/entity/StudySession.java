package com.istudy.entity;

import jakarta.persistence.*;

import java.time.LocalDateTime;

/**
 * 학습 세션 요약 (통계용). 테이블: study_sessions
 * - 웹: user_id 로 식별 / 데스크톱 앱: login_id 로 식별 (user_id NULL 가능)
 */
@Entity
@Table(name = "study_sessions")
public class StudySession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "user_id")
    private Integer userId;

    @Column(name = "login_id", length = 64)
    private String loginId;

    @Column(nullable = false, length = 10)
    private String date;            // YYYY-MM-DD

    @Column(name = "start_time")
    private LocalDateTime startTime;

    @Column(name = "end_time")
    private LocalDateTime endTime;

    @Column(name = "total_time_seconds")
    private Integer totalTimeSeconds;

    @Column(name = "focus_time_seconds")
    private Integer focusTimeSeconds;

    @Column(name = "duration_min")
    private Integer durationMin = 0;

    @Column(name = "focus_score")
    private Double focusScore = 0.0;

    @Column(name = "focused_min")
    private Integer focusedMin = 0;

    @Column(name = "dazed_min")
    private Integer dazedMin = 0;

    @Column(name = "distracted_min")
    private Integer distractedMin = 0;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @PrePersist
    void prePersist() {
        if (createdAt == null) createdAt = LocalDateTime.now();
    }

    public Integer getId() { return id; }
    public void setId(Integer id) { this.id = id; }
    public Integer getUserId() { return userId; }
    public void setUserId(Integer userId) { this.userId = userId; }
    public String getLoginId() { return loginId; }
    public void setLoginId(String loginId) { this.loginId = loginId; }
    public String getDate() { return date; }
    public void setDate(String date) { this.date = date; }
    public LocalDateTime getStartTime() { return startTime; }
    public void setStartTime(LocalDateTime startTime) { this.startTime = startTime; }
    public LocalDateTime getEndTime() { return endTime; }
    public void setEndTime(LocalDateTime endTime) { this.endTime = endTime; }
    public Integer getTotalTimeSeconds() { return totalTimeSeconds; }
    public void setTotalTimeSeconds(Integer v) { this.totalTimeSeconds = v; }
    public Integer getFocusTimeSeconds() { return focusTimeSeconds; }
    public void setFocusTimeSeconds(Integer v) { this.focusTimeSeconds = v; }
    public Integer getDurationMin() { return durationMin; }
    public void setDurationMin(Integer v) { this.durationMin = v; }
    public Double getFocusScore() { return focusScore; }
    public void setFocusScore(Double v) { this.focusScore = v; }
    public Integer getFocusedMin() { return focusedMin; }
    public void setFocusedMin(Integer v) { this.focusedMin = v; }
    public Integer getDazedMin() { return dazedMin; }
    public void setDazedMin(Integer v) { this.dazedMin = v; }
    public Integer getDistractedMin() { return distractedMin; }
    public void setDistractedMin(Integer v) { this.distractedMin = v; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime v) { this.createdAt = v; }
}
