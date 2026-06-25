package com.istudy.controller;

import com.istudy.entity.GazeSettings;
import com.istudy.entity.WhitelistUrl;
import com.istudy.exception.ApiException;
import com.istudy.repository.GazeSettingsRepository;
import com.istudy.repository.WhitelistUrlRepository;
import jakarta.validation.constraints.NotBlank;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * /api/* — 데스크톱 앱 호환용 레거시 (익명 접근).
 * 동일 PostgreSQL DB 를 공유한다.
 */
@RestController
@RequestMapping("/api")
public class LegacyController {

    private final WhitelistUrlRepository whitelistRepo;
    private final GazeSettingsRepository gazeRepo;

    public LegacyController(WhitelistUrlRepository whitelistRepo, GazeSettingsRepository gazeRepo) {
        this.whitelistRepo = whitelistRepo;
        this.gazeRepo = gazeRepo;
    }

    public record WhitelistCreate(@NotBlank String name, @NotBlank String url) {}

    private static Map<String, Object> wlOut(WhitelistUrl w) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", w.getId());
        m.put("name", w.getName());
        m.put("url", w.getUrl());
        return m;
    }

    @GetMapping("/whitelist")
    public List<Map<String, Object>> listDefault() {
        return whitelistRepo.findByUserIdIsNullOrderByCreatedAtDesc().stream()
                .map(LegacyController::wlOut).toList();
    }

    @PostMapping("/whitelist")
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> addDefault(@RequestBody WhitelistCreate body) {
        if (whitelistRepo.findDefaultByUrl(body.url()).isPresent())
            throw ApiException.badRequest("이미 등록된 URL입니다.");
        WhitelistUrl item = new WhitelistUrl();
        item.setName(body.name());
        item.setUrl(body.url());
        item.setUserId(null);
        return wlOut(whitelistRepo.save(item));
    }

    @DeleteMapping("/whitelist/{urlId}")
    public Map<String, Object> deleteDefault(@PathVariable Integer urlId) {
        WhitelistUrl item = whitelistRepo.findById(urlId)
                .orElseThrow(() -> ApiException.notFound("URL을 찾을 수 없습니다."));
        whitelistRepo.delete(item);
        return Map.of("status", "deleted", "id", urlId);
    }

    /** 가장 최근 보정 학생의 시야각 임계치 (데스크톱 GazeTracker.apply_calibration 형식) */
    @GetMapping("/calibration")
    public Map<String, Object> calibrationForDesktop() {
        GazeSettings row = gazeRepo.findFirstByCalibratedOrderByUpdatedAtDesc(1).orElse(null);
        Map<String, Object> m = new LinkedHashMap<>();
        if (row == null) {
            m.put("center_ratio", 0.50);
            m.put("left_threshold", 0.20);
            m.put("right_threshold", 0.80);
            m.put("up_threshold", 0.38);
            m.put("down_threshold", 0.62);
            m.put("gaze_lost_threshold", 2.0);
            m.put("eye_closure_threshold", 5.0);
            m.put("calibrated", 0);
            return m;
        }
        m.put("center_ratio", or(row.getCenterRatio(), 0.5));
        m.put("left_threshold", or(row.getHLeftThreshold(), 0.20));
        m.put("right_threshold", or(row.getHRightThreshold(), 0.80));
        m.put("up_threshold", or(row.getVUpThreshold(), 0.38));
        m.put("down_threshold", or(row.getVDownThreshold(), 0.62));
        m.put("gaze_lost_threshold", or(row.getGazeLostThreshold(), 2.0));
        m.put("eye_closure_threshold", or(row.getEyeClosureThreshold(), 5.0));
        m.put("calibrated", row.getCalibrated() != null ? row.getCalibrated() : 0);
        return m;
    }

    private static double or(Double v, double def) { return v != null ? v : def; }
}
