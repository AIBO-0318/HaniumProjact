package com.istudy.controller;

import com.istudy.entity.GazeSettings;
import com.istudy.entity.User;
import com.istudy.entity.UserRole;
import com.istudy.exception.ApiException;
import com.istudy.repository.GazeSettingsRepository;
import com.istudy.repository.UserRepository;
import com.istudy.security.AuthPrincipal;
import com.istudy.security.Accounts;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * /gaze-settings/* — 시선 임계치 설정 (데스크톱 앱이 학습 시작 시 사용)
 * 참고: GazeSettings 엔티티는 캘리브레이션과 동일 행을 공유한다.
 */
@RestController
@RequestMapping("/gaze-settings")
public class GazeSettingsController {

    private final GazeSettingsRepository repo;
    private final UserRepository userRepo;
    private final Accounts accounts;

    public GazeSettingsController(GazeSettingsRepository repo, UserRepository userRepo, Accounts accounts) {
        this.repo = repo;
        this.userRepo = userRepo;
        this.accounts = accounts;
    }

    public record SettingsBody(
            @DecimalMin("0.05") @DecimalMax("0.5")   Double ear_threshold,
            @DecimalMin("1.0")  @DecimalMax("30.0")  Double eye_closure_threshold,
            @DecimalMin("5.0")  @DecimalMax("60.0")  Double yaw_threshold,
            @DecimalMin("5.0")  @DecimalMax("60.0")  Double pitch_threshold,
            @DecimalMin("0.5")  @DecimalMax("15.0")  Double pose_lost_threshold,
            @DecimalMin("50.0") @DecimalMax("2000.0") Double daze_variance_thr,
            @DecimalMin("0.5")  @DecimalMax("15.0")  Double daze_duration_sec,
            @DecimalMin("0.0")  @DecimalMax("1.0")   Double alpha_iris
    ) {}

    private GazeSettings getOrCreate(Integer userId) {
        return repo.findByUserId(userId).orElseGet(() -> {
            GazeSettings s = new GazeSettings();
            s.setUserId(userId);
            return repo.save(s);
        });
    }

    private static Map<String, Object> toResp(GazeSettings s) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("user_id", s.getUserId());
        m.put("ear_threshold", s.getEarThreshold());
        m.put("eye_closure_threshold", s.getEyeClosureThreshold());
        m.put("yaw_threshold", s.getYawThreshold());
        m.put("pitch_threshold", s.getPitchThreshold());
        m.put("pose_lost_threshold", s.getPoseLostThreshold());
        m.put("daze_variance_thr", s.getDazeVarianceThr());
        m.put("daze_duration_sec", s.getDazeDurationSec());
        m.put("alpha_iris", s.getAlphaIris());
        return m;
    }

    @GetMapping("/me")
    public Map<String, Object> getMine(@AuthenticationPrincipal AuthPrincipal principal) {
        User u = accounts.requireUser(principal);
        return toResp(getOrCreate(u.getId()));
    }

    @PutMapping("/me")
    public Map<String, Object> updateMine(@jakarta.validation.Valid @RequestBody SettingsBody body,
                                          @AuthenticationPrincipal AuthPrincipal principal) {
        User u = accounts.requireUser(principal);
        if (u.getRole() != UserRole.STUDENT)
            throw ApiException.forbidden("시선 임계치는 학생 본인만 수정할 수 있습니다.");
        GazeSettings s = getOrCreate(u.getId());
        if (body.ear_threshold() != null) s.setEarThreshold(body.ear_threshold());
        if (body.eye_closure_threshold() != null) s.setEyeClosureThreshold(body.eye_closure_threshold());
        if (body.yaw_threshold() != null) s.setYawThreshold(body.yaw_threshold());
        if (body.pitch_threshold() != null) s.setPitchThreshold(body.pitch_threshold());
        if (body.pose_lost_threshold() != null) s.setPoseLostThreshold(body.pose_lost_threshold());
        if (body.daze_variance_thr() != null) s.setDazeVarianceThr(body.daze_variance_thr());
        if (body.daze_duration_sec() != null) s.setDazeDurationSec(body.daze_duration_sec());
        if (body.alpha_iris() != null) s.setAlphaIris(body.alpha_iris());
        return toResp(repo.save(s));
    }

    @GetMapping("/student/{studentId}")
    public Map<String, Object> getStudent(@PathVariable Integer studentId,
                                          @AuthenticationPrincipal AuthPrincipal principal) {
        User current = accounts.requireUser(principal);
        User student = userRepo.findById(studentId)
                .filter(s -> s.getRole() == UserRole.STUDENT)
                .orElseThrow(() -> ApiException.notFound("학생을 찾을 수 없습니다."));
        if (current.getRole() != UserRole.TEACHER
                || !current.getId().equals(student.getTeacherId()))
            throw ApiException.forbidden("해당 학생을 관리할 권한이 없습니다.");
        return toResp(getOrCreate(studentId));
    }
}
