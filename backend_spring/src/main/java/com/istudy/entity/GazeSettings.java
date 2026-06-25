package com.istudy.entity;

import jakarta.persistence.*;

import java.time.LocalDateTime;

/**
 * 사용자별 시선/집중도 임계치 + 시야각 캘리브레이션. 테이블: gaze_settings (user_id UNIQUE)
 * 데스크톱 앱이 학습 시작 시 이 값을 불러와 적용.
 */
@Entity
@Table(name = "gaze_settings")
public class GazeSettings {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Integer id;

    @Column(name = "user_id", nullable = false, unique = true)
    private Integer userId;

    // 눈 감음
    @Column(name = "ear_threshold")
    private Double earThreshold = 0.18;
    @Column(name = "eye_closure_threshold")
    private Double eyeClosureThreshold = 5.0;

    // Head Pose 이탈
    @Column(name = "yaw_threshold")
    private Double yawThreshold = 20.0;
    @Column(name = "pitch_threshold")
    private Double pitchThreshold = 15.0;
    @Column(name = "pose_lost_threshold")
    private Double poseLostThreshold = 3.0;

    // 멍때리기
    @Column(name = "daze_variance_thr")
    private Double dazeVarianceThr = 300.0;
    @Column(name = "daze_duration_sec")
    private Double dazeDurationSec = 2.0;

    // 가중치
    @Column(name = "alpha_iris")
    private Double alphaIris = 0.85;

    // 시야각 캘리브레이션 (시선 초점 잡기)
    @Column(name = "center_ratio")
    private Double centerRatio = 0.50;
    @Column(name = "h_left_threshold")
    private Double hLeftThreshold = 0.20;
    @Column(name = "h_right_threshold")
    private Double hRightThreshold = 0.80;
    @Column(name = "v_up_threshold")
    private Double vUpThreshold = 0.38;
    @Column(name = "v_down_threshold")
    private Double vDownThreshold = 0.62;
    @Column(name = "gaze_lost_threshold")
    private Double gazeLostThreshold = 2.0;
    @Column(name = "calibrated")
    private Integer calibrated = 0;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @PrePersist
    @PreUpdate
    void touch() {
        updatedAt = LocalDateTime.now();
    }

    public Integer getId() { return id; }
    public void setId(Integer id) { this.id = id; }
    public Integer getUserId() { return userId; }
    public void setUserId(Integer userId) { this.userId = userId; }
    public Double getEarThreshold() { return earThreshold; }
    public void setEarThreshold(Double v) { this.earThreshold = v; }
    public Double getEyeClosureThreshold() { return eyeClosureThreshold; }
    public void setEyeClosureThreshold(Double v) { this.eyeClosureThreshold = v; }
    public Double getYawThreshold() { return yawThreshold; }
    public void setYawThreshold(Double v) { this.yawThreshold = v; }
    public Double getPitchThreshold() { return pitchThreshold; }
    public void setPitchThreshold(Double v) { this.pitchThreshold = v; }
    public Double getPoseLostThreshold() { return poseLostThreshold; }
    public void setPoseLostThreshold(Double v) { this.poseLostThreshold = v; }
    public Double getDazeVarianceThr() { return dazeVarianceThr; }
    public void setDazeVarianceThr(Double v) { this.dazeVarianceThr = v; }
    public Double getDazeDurationSec() { return dazeDurationSec; }
    public void setDazeDurationSec(Double v) { this.dazeDurationSec = v; }
    public Double getAlphaIris() { return alphaIris; }
    public void setAlphaIris(Double v) { this.alphaIris = v; }
    public Double getCenterRatio() { return centerRatio; }
    public void setCenterRatio(Double v) { this.centerRatio = v; }
    public Double getHLeftThreshold() { return hLeftThreshold; }
    public void setHLeftThreshold(Double v) { this.hLeftThreshold = v; }
    public Double getHRightThreshold() { return hRightThreshold; }
    public void setHRightThreshold(Double v) { this.hRightThreshold = v; }
    public Double getVUpThreshold() { return vUpThreshold; }
    public void setVUpThreshold(Double v) { this.vUpThreshold = v; }
    public Double getVDownThreshold() { return vDownThreshold; }
    public void setVDownThreshold(Double v) { this.vDownThreshold = v; }
    public Double getGazeLostThreshold() { return gazeLostThreshold; }
    public void setGazeLostThreshold(Double v) { this.gazeLostThreshold = v; }
    public Integer getCalibrated() { return calibrated; }
    public void setCalibrated(Integer v) { this.calibrated = v; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime v) { this.updatedAt = v; }
}
