package com.istudy.controller;

import com.istudy.entity.StudySession;
import com.istudy.entity.User;
import com.istudy.entity.UserRole;
import com.istudy.exception.ApiException;
import com.istudy.repository.StudySessionRepository;
import com.istudy.repository.UserRepository;
import com.istudy.security.AuthPrincipal;
import com.istudy.security.Accounts;
import org.springframework.data.domain.PageRequest;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/** /stats/* — 일별/시간별/주별/월별 통계 + 세션 저장/조회 */
@RestController
@RequestMapping("/stats")
public class StatsController {

    private final StudySessionRepository repo;
    private final UserRepository userRepo;
    private final Accounts accounts;

    public StatsController(StudySessionRepository repo, UserRepository userRepo, Accounts accounts) {
        this.repo = repo;
        this.userRepo = userRepo;
        this.accounts = accounts;
    }

    private record Target(Integer uid, String lid) {}

    /** 권한에 따라 조회 대상 (user_id, login_id) 결정 */
    private Target resolveTarget(Accounts.AccountInfo info, Integer studentId) {
        if (info.isAdmin()) {
            if (studentId == null) return new Target(null, null);
            User t = userRepo.findById(studentId)
                    .orElseThrow(() -> ApiException.notFound("학생을 찾을 수 없습니다."));
            return new Target(t.getId(), t.getLoginId());
        }
        User account = info.user();
        if (studentId != null && account.getRole() == UserRole.TEACHER) {
            User t = userRepo.findById(studentId)
                    .filter(s -> account.getId().equals(s.getTeacherId()))
                    .orElseThrow(() -> ApiException.forbidden("해당 학생을 관리할 권한이 없습니다."));
            return new Target(t.getId(), t.getLoginId());
        }
        return new Target(account.getId(), account.getLoginId());
    }

    private static double round1(double v) { return Math.round(v * 10.0) / 10.0; }

    private static int sumInt(Integer v) { return v != null ? v : 0; }

    // ─── 일별 ───
    @GetMapping("/daily")
    public Map<String, Object> daily(
            @RequestParam(defaultValue = "7") int days,
            @RequestParam(required = false, name = "student_id") Integer studentId,
            @AuthenticationPrincipal AuthPrincipal principal) {
        Target t = resolveTarget(accounts.requireUserOrAdmin(principal), studentId);
        LocalDate today = LocalDate.now();
        LocalDate start = today.minusDays(days - 1L);
        List<StudySession> rows = repo.findInRange(start.toString(), today.toString(), t.uid(), t.lid());

        Map<String, List<StudySession>> byDate = new HashMap<>();
        for (StudySession s : rows) byDate.computeIfAbsent(s.getDate(), k -> new ArrayList<>()).add(s);

        List<Map<String, Object>> items = new ArrayList<>();
        for (int i = 0; i < days; i++) {
            String d = start.plusDays(i).toString();
            List<StudySession> ss = byDate.get(d);
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("date", d);
            if (ss == null || ss.isEmpty()) {
                m.put("duration_min", 0);
                m.put("focus_score", 0.0);
                m.put("focused_min", 0);
                m.put("dazed_min", 0);
                m.put("distracted_min", 0);
            } else {
                int dur = 0, foc = 0, daz = 0, dis = 0;
                double scoreSum = 0;
                for (StudySession s : ss) {
                    dur += sumInt(s.getDurationMin());
                    foc += sumInt(s.getFocusedMin());
                    daz += sumInt(s.getDazedMin());
                    dis += sumInt(s.getDistractedMin());
                    scoreSum += s.getFocusScore() != null ? s.getFocusScore() : 0;
                }
                m.put("duration_min", dur);
                m.put("focus_score", round1(scoreSum / ss.size()));
                m.put("focused_min", foc);
                m.put("dazed_min", daz);
                m.put("distracted_min", dis);
            }
            items.add(m);
        }
        return Map.of("days", days, "items", items);
    }

    // ─── 시간별 ───
    @GetMapping("/hourly")
    public Map<String, Object> hourly(
            @RequestParam String date,
            @RequestParam(required = false, name = "student_id") Integer studentId,
            @AuthenticationPrincipal AuthPrincipal principal) {
        Target t = resolveTarget(accounts.requireUserOrAdmin(principal), studentId);
        List<StudySession> rows = repo.findByDate(date, t.uid(), t.lid());

        double[] scoreSum = new double[24];
        int[] count = new int[24];
        int[] duration = new int[24];
        for (StudySession s : rows) {
            int hour = s.getStartTime() != null ? s.getStartTime().getHour() : 0;
            scoreSum[hour] += s.getFocusScore() != null ? s.getFocusScore() : 0;
            count[hour] += 1;
            duration[hour] += sumInt(s.getDurationMin());
        }

        List<Map<String, Object>> items = new ArrayList<>();
        for (int h = 0; h < 24; h++) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("hour", h);
            m.put("focus_score", count[h] > 0 ? round1(scoreSum[h] / count[h]) : 0.0);
            m.put("duration_min", duration[h]);
            m.put("has_data", count[h] > 0);
            items.add(m);
        }
        return Map.of("date", date, "items", items);
    }

    // ─── 주 단위 일별 (선택 주의 월~일) ───
    @GetMapping("/week-days")
    public Map<String, Object> weekDays(
            @RequestParam String date,
            @RequestParam(required = false, name = "student_id") Integer studentId,
            @AuthenticationPrincipal AuthPrincipal principal) {
        Target t = resolveTarget(accounts.requireUserOrAdmin(principal), studentId);
        LocalDate target = LocalDate.parse(date);
        LocalDate monday = target.minusDays(target.getDayOfWeek().getValue() - 1L);
        LocalDate sunday = monday.plusDays(6);
        List<StudySession> rows = repo.findInRange(monday.toString(), sunday.toString(), t.uid(), t.lid());

        Map<String, List<StudySession>> byDate = new HashMap<>();
        for (StudySession s : rows) byDate.computeIfAbsent(s.getDate(), k -> new ArrayList<>()).add(s);

        List<Map<String, Object>> items = new ArrayList<>();
        for (int i = 0; i < 7; i++) {
            String d = monday.plusDays(i).toString();
            List<StudySession> ss = byDate.get(d);
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("date", d);
            if (ss == null || ss.isEmpty()) {
                m.put("duration_min", 0);
                m.put("focused_min", 0);
                m.put("focus_score", 0.0);
            } else {
                int dur = 0, foc = 0;
                double scoreSum = 0;
                for (StudySession s : ss) {
                    dur += sumInt(s.getDurationMin());
                    foc += sumInt(s.getFocusedMin());
                    scoreSum += s.getFocusScore() != null ? s.getFocusScore() : 0;
                }
                m.put("duration_min", dur);
                m.put("focused_min", foc);
                m.put("focus_score", round1(scoreSum / ss.size()));
            }
            items.add(m);
        }
        return Map.of("week_start", monday.toString(), "week_end", sunday.toString(), "items", items);
    }

    // ─── 주별 ───
    @GetMapping("/weekly")
    public Map<String, Object> weekly(
            @RequestParam(defaultValue = "4") int weeks,
            @RequestParam(required = false, name = "student_id") Integer studentId,
            @AuthenticationPrincipal AuthPrincipal principal) {
        Target t = resolveTarget(accounts.requireUserOrAdmin(principal), studentId);
        LocalDate today = LocalDate.now();
        LocalDate monday = today.minusDays(today.getDayOfWeek().getValue() - 1L);
        LocalDate start = monday.minusWeeks(weeks - 1L);
        List<StudySession> rows = repo.findInRange(start.toString(), today.toString(), t.uid(), t.lid());

        // 주별 버킷 (week_start ISO 키)
        Map<String, int[]> dur = new LinkedHashMap<>();
        Map<String, double[]> score = new LinkedHashMap<>();
        Map<String, String> weekEnd = new LinkedHashMap<>();
        List<String> order = new ArrayList<>();
        for (int i = 0; i < weeks; i++) {
            LocalDate ws = start.plusWeeks(i);
            String key = ws.toString();
            order.add(key);
            dur.put(key, new int[]{0});
            score.put(key, new double[]{0.0, 0.0}); // sum, count
            weekEnd.put(key, ws.plusDays(6).toString());
        }
        for (StudySession s : rows) {
            LocalDate d = LocalDate.parse(s.getDate());
            LocalDate ws = d.minusDays(d.getDayOfWeek().getValue() - 1L);
            String key = ws.toString();
            if (dur.containsKey(key)) {
                dur.get(key)[0] += sumInt(s.getDurationMin());
                score.get(key)[0] += s.getFocusScore() != null ? s.getFocusScore() : 0;
                score.get(key)[1] += 1;
            }
        }
        List<Map<String, Object>> items = new ArrayList<>();
        for (String key : order) {
            double[] sc = score.get(key);
            double avg = sc[1] > 0 ? sc[0] / sc[1] : 0.0;
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("week_start", key);
            m.put("week_end", weekEnd.get(key));
            m.put("duration_min", dur.get(key)[0]);
            m.put("focus_score", round1(avg));
            items.add(m);
        }
        return Map.of("weeks", weeks, "items", items);
    }

    // ─── 월별 ───
    @GetMapping("/monthly")
    public Map<String, Object> monthly(
            @RequestParam(defaultValue = "6") int months,
            @RequestParam(required = false, name = "student_id") Integer studentId,
            @AuthenticationPrincipal AuthPrincipal principal) {
        Target t = resolveTarget(accounts.requireUserOrAdmin(principal), studentId);
        LocalDate today = LocalDate.now();
        LocalDate start = today.withDayOfMonth(1).minusMonths(months - 1L);
        List<StudySession> rows = repo.findInRange(start.toString(), today.toString(), t.uid(), t.lid());

        DateTimeFormatter ym = DateTimeFormatter.ofPattern("yyyy-MM");
        Map<String, int[]> dur = new LinkedHashMap<>();
        Map<String, double[]> score = new LinkedHashMap<>();
        Map<String, String[]> bounds = new LinkedHashMap<>();
        List<String> order = new ArrayList<>();
        LocalDate cur = start;
        while (!cur.isAfter(today)) {
            String key = cur.format(ym);
            order.add(key);
            dur.put(key, new int[]{0});
            score.put(key, new double[]{0.0, 0.0});
            LocalDate mStart = cur.withDayOfMonth(1);
            LocalDate mEnd = cur.withDayOfMonth(cur.lengthOfMonth());
            bounds.put(key, new String[]{mStart.toString(), mEnd.toString()});
            cur = cur.plusMonths(1).withDayOfMonth(1);
        }
        for (StudySession s : rows) {
            String key = LocalDate.parse(s.getDate()).format(ym);
            if (dur.containsKey(key)) {
                dur.get(key)[0] += sumInt(s.getDurationMin());
                score.get(key)[0] += s.getFocusScore() != null ? s.getFocusScore() : 0;
                score.get(key)[1] += 1;
            }
        }
        List<Map<String, Object>> items = new ArrayList<>();
        for (String key : order) {
            double[] sc = score.get(key);
            double avg = sc[1] > 0 ? sc[0] / sc[1] : 0.0;
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("month", key);
            m.put("month_start", bounds.get(key)[0]);
            m.put("month_end", bounds.get(key)[1]);
            m.put("duration_min", dur.get(key)[0]);
            m.put("focus_score", round1(avg));
            items.add(m);
        }
        return Map.of("months", months, "items", items);
    }

    // ─── 세션 저장 (데스크톱 앱) ───
    @PostMapping("/sessions")
    public Map<String, Object> saveSession(@RequestBody Map<String, Object> payload,
                                           @AuthenticationPrincipal AuthPrincipal principal) {
        Accounts.AccountInfo info = accounts.requireUserOrAdmin(principal);
        if (info.isAdmin())
            throw ApiException.forbidden("관리자는 세션을 직접 저장할 수 없습니다.");
        User account = info.user();
        StudySession s = new StudySession();
        s.setUserId(account.getId());
        s.setLoginId(account.getLoginId());
        s.setDate(str(payload.get("date"), LocalDate.now().toString()));
        s.setStartTime(parseDt(payload.get("start_time")));
        s.setEndTime(parseDt(payload.get("end_time")));
        s.setTotalTimeSeconds(intOf(payload.get("total_time_seconds")));
        s.setFocusTimeSeconds(intOf(payload.get("focus_time_seconds")));
        s.setDurationMin(intOf(payload.get("duration_min")));
        s.setFocusScore(dblOf(payload.get("focus_score")));
        s.setFocusedMin(intOf(payload.get("focused_min")));
        s.setDazedMin(intOf(payload.get("dazed_min")));
        s.setDistractedMin(intOf(payload.get("distracted_min")));
        s = repo.save(s);
        return Map.of("status", "ok", "id", s.getId());
    }

    // ─── 원시 세션 기록 ───
    @GetMapping("/logs")
    public Map<String, Object> logs(@RequestParam(defaultValue = "30") int limit,
                                    @AuthenticationPrincipal AuthPrincipal principal) {
        Accounts.AccountInfo info = accounts.requireUserOrAdmin(principal);
        if (info.isAdmin()) return Map.of("items", List.of());
        User account = info.user();
        List<StudySession> rows = repo.findOwnRecent(account.getId(), account.getLoginId(),
                PageRequest.of(0, Math.min(Math.max(limit, 1), 200)));
        List<Map<String, Object>> items = new ArrayList<>();
        for (StudySession r : rows) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", r.getId());
            m.put("study_date", r.getDate());
            m.put("start_time", r.getStartTime() != null ? r.getStartTime().toString() : null);
            m.put("end_time", r.getEndTime() != null ? r.getEndTime().toString() : null);
            m.put("total_time_seconds", sumInt(r.getTotalTimeSeconds()));
            m.put("focus_time_seconds", sumInt(r.getFocusTimeSeconds()));
            m.put("duration_min", sumInt(r.getDurationMin()));
            m.put("focus_score", r.getFocusScore() != null ? r.getFocusScore() : 0.0);
            m.put("created_at", r.getCreatedAt() != null ? r.getCreatedAt().toString() : null);
            items.add(m);
        }
        return Map.of("items", items);
    }

    // ─── 오늘 집중 시간 ───
    @GetMapping("/today")
    public Map<String, Object> today(@AuthenticationPrincipal AuthPrincipal principal) {
        Accounts.AccountInfo info = accounts.requireUserOrAdmin(principal);
        if (info.isAdmin()) return Map.of("focus_time_seconds", 0);
        User account = info.user();
        Long total = repo.sumFocusTimeToday(LocalDate.now().toString(),
                account.getId(), account.getLoginId());
        return Map.of("focus_time_seconds", total != null ? total.intValue() : 0);
    }

    // ─── 헬퍼 ───
    private static String str(Object v, String def) { return v != null ? v.toString() : def; }

    private static int intOf(Object v) {
        if (v == null) return 0;
        if (v instanceof Number n) return n.intValue();
        try { return (int) Double.parseDouble(v.toString()); } catch (Exception e) { return 0; }
    }

    private static double dblOf(Object v) {
        if (v == null) return 0.0;
        if (v instanceof Number n) return n.doubleValue();
        try { return Double.parseDouble(v.toString()); } catch (Exception e) { return 0.0; }
    }

    private static LocalDateTime parseDt(Object v) {
        if (v == null) return null;
        try { return LocalDateTime.parse(v.toString()); } catch (Exception e) { return null; }
    }
}
