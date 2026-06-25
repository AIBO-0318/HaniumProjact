package com.istudy.controller;

import com.istudy.entity.GazeSettings;
import com.istudy.entity.User;
import com.istudy.entity.UserRole;
import com.istudy.exception.ApiException;
import com.istudy.repository.GazeSettingsRepository;
import com.istudy.security.AuthPrincipal;
import com.istudy.security.Accounts;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * /calibration/* — 시야각 초점(캘리브레이션) 값. GazeSettings 행을 공유한다.
 * 학생이 웹에서 보정 → 데스크톱 앱이 학습 시작 시 적용.
 */
@RestController
@RequestMapping("/calibration")
public class CalibrationController {

    private static final double D_CENTER = 0.50, D_LEFT = 0.20, D_RIGHT = 0.80,
            D_UP = 0.38, D_DOWN = 0.62, D_GAZE_LOST = 2.0;

    private final GazeSettingsRepository repo;
    private final Accounts accounts;

    public CalibrationController(GazeSettingsRepository repo, Accounts accounts) {
        this.repo = repo;
        this.accounts = accounts;
    }

    public record Body(
            @DecimalMin("0.0") @DecimalMax("1.0") Double center_ratio,
            @DecimalMin("0.0") @DecimalMax("1.0") Double h_left_threshold,
            @DecimalMin("0.0") @DecimalMax("1.0") Double h_right_threshold,
            @DecimalMin("0.0") @DecimalMax("1.0") Double v_up_threshold,
            @DecimalMin("0.0") @DecimalMax("1.0") Double v_down_threshold,
            @DecimalMin("0.3") @DecimalMax("15.0") Double gaze_lost_threshold
    ) {}

    private GazeSettings getOrCreate(Integer userId) {
        return repo.findByUserId(userId).orElseGet(() -> {
            GazeSettings s = new GazeSettings();
            s.setUserId(userId);
            s.setCenterRatio(D_CENTER);
            s.setHLeftThreshold(D_LEFT);
            s.setHRightThreshold(D_RIGHT);
            s.setVUpThreshold(D_UP);
            s.setVDownThreshold(D_DOWN);
            s.setGazeLostThreshold(D_GAZE_LOST);
            s.setCalibrated(0);
            return repo.save(s);
        });
    }

    private static double or(Double v, double def) { return v != null ? v : def; }

    private static Map<String, Object> toOut(GazeSettings r) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("user_id", r.getUserId());
        m.put("center_ratio", or(r.getCenterRatio(), D_CENTER));
        m.put("h_left_threshold", or(r.getHLeftThreshold(), D_LEFT));
        m.put("h_right_threshold", or(r.getHRightThreshold(), D_RIGHT));
        m.put("v_up_threshold", or(r.getVUpThreshold(), D_UP));
        m.put("v_down_threshold", or(r.getVDownThreshold(), D_DOWN));
        m.put("gaze_lost_threshold", or(r.getGazeLostThreshold(), D_GAZE_LOST));
        m.put("calibrated", r.getCalibrated() != null ? r.getCalibrated() : 0);
        return m;
    }

    @GetMapping("/me")
    public Map<String, Object> getMine(@AuthenticationPrincipal AuthPrincipal principal) {
        User u = accounts.requireUser(principal);
        if (u.getRole() != UserRole.STUDENT)
            throw ApiException.forbidden("학생 본인 전용 엔드포인트입니다.");
        return toOut(getOrCreate(u.getId()));
    }

    @PutMapping("/me")
    public Map<String, Object> updateMine(@jakarta.validation.Valid @RequestBody Body body,
                                          @AuthenticationPrincipal AuthPrincipal principal) {
        User u = accounts.requireUser(principal);
        if (u.getRole() != UserRole.STUDENT)
            throw ApiException.forbidden("학생 본인 전용 엔드포인트입니다.");
        GazeSettings r = getOrCreate(u.getId());

        double left  = or(body.h_left_threshold(),  or(r.getHLeftThreshold(), D_LEFT));
        double right = or(body.h_right_threshold(), or(r.getHRightThreshold(), D_RIGHT));
        double up    = or(body.v_up_threshold(),    or(r.getVUpThreshold(), D_UP));
        double down  = or(body.v_down_threshold(),  or(r.getVDownThreshold(), D_DOWN));
        if (left >= right) throw ApiException.badRequest("왼쪽 임계값은 오른쪽보다 작아야 합니다.");
        if (up >= down)    throw ApiException.badRequest("위쪽 임계값은 아래쪽보다 작아야 합니다.");

        if (body.center_ratio() != null) r.setCenterRatio(body.center_ratio());
        if (body.h_left_threshold() != null) r.setHLeftThreshold(body.h_left_threshold());
        if (body.h_right_threshold() != null) r.setHRightThreshold(body.h_right_threshold());
        if (body.v_up_threshold() != null) r.setVUpThreshold(body.v_up_threshold());
        if (body.v_down_threshold() != null) r.setVDownThreshold(body.v_down_threshold());
        if (body.gaze_lost_threshold() != null) r.setGazeLostThreshold(body.gaze_lost_threshold());
        r.setCalibrated(1);
        return toOut(repo.save(r));
    }

    @PostMapping("/me/reset")
    public Map<String, Object> reset(@AuthenticationPrincipal AuthPrincipal principal) {
        User u = accounts.requireUser(principal);
        if (u.getRole() != UserRole.STUDENT)
            throw ApiException.forbidden("학생 본인 전용 엔드포인트입니다.");
        GazeSettings r = getOrCreate(u.getId());
        r.setCenterRatio(D_CENTER);
        r.setHLeftThreshold(D_LEFT);
        r.setHRightThreshold(D_RIGHT);
        r.setVUpThreshold(D_UP);
        r.setVDownThreshold(D_DOWN);
        r.setGazeLostThreshold(D_GAZE_LOST);
        r.setCalibrated(0);
        return toOut(repo.save(r));
    }
}
