package com.istudy.controller;

import com.istudy.dto.ScheduleDtos;
import com.istudy.entity.Schedule;
import com.istudy.entity.User;
import com.istudy.entity.UserRole;
import com.istudy.exception.ApiException;
import com.istudy.repository.ScheduleRepository;
import com.istudy.repository.UserRepository;
import com.istudy.security.AuthPrincipal;
import com.istudy.security.Accounts;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** /schedules/* — 일정 확인/추가/수정/삭제, 지도자의 학생 일정 조회 */
@RestController
@RequestMapping("/schedules")
public class ScheduleController {

    private final ScheduleRepository scheduleRepo;
    private final UserRepository userRepo;
    private final Accounts accounts;

    public ScheduleController(ScheduleRepository scheduleRepo, UserRepository userRepo, Accounts accounts) {
        this.scheduleRepo = scheduleRepo;
        this.userRepo = userRepo;
        this.accounts = accounts;
    }

    @GetMapping
    public List<ScheduleDtos.Response> list(
            @RequestParam(required = false) String date_from,
            @RequestParam(required = false) String date_to,
            @AuthenticationPrincipal AuthPrincipal principal) {
        User u = accounts.requireUser(principal);
        return scheduleRepo.findInRange(u.getId(), date_from, date_to)
                .stream().map(ScheduleDtos.Response::of).toList();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ScheduleDtos.Response add(@Valid @RequestBody ScheduleDtos.CreateRequest req,
                                     @AuthenticationPrincipal AuthPrincipal principal) {
        User u = accounts.requireUser(principal);
        if (u.getRole() != UserRole.STUDENT)
            throw ApiException.forbidden("일정은 학생 본인만 추가할 수 있습니다.");
        Schedule s = new Schedule();
        s.setUserId(u.getId());
        s.setDate(req.date());
        s.setStartTime(req.start_time());
        s.setEndTime(req.end_time());
        s.setTitle(req.title());
        s.setMemo(req.memo());
        s.setColor(req.color() != null ? req.color() : "blue");
        s.setIsDone(0);
        return ScheduleDtos.Response.of(scheduleRepo.save(s));
    }

    @PatchMapping("/{scheduleId}")
    public ScheduleDtos.Response update(@PathVariable Integer scheduleId,
                                        @Valid @RequestBody ScheduleDtos.UpdateRequest req,
                                        @AuthenticationPrincipal AuthPrincipal principal) {
        User u = accounts.requireUser(principal);
        Schedule s = scheduleRepo.findByIdAndUserId(scheduleId, u.getId())
                .orElseThrow(() -> ApiException.notFound("일정을 찾을 수 없습니다."));
        if (u.getRole() != UserRole.STUDENT)
            throw ApiException.forbidden("본인의 일정만 수정할 수 있습니다.");
        if (req.is_done() != null)
            s.setIsDone(req.is_done() != 0 ? 1 : 0);
        return ScheduleDtos.Response.of(scheduleRepo.save(s));
    }

    @DeleteMapping("/{scheduleId}")
    public Map<String, Object> delete(@PathVariable Integer scheduleId,
                                      @AuthenticationPrincipal AuthPrincipal principal) {
        User u = accounts.requireUser(principal);
        if (u.getRole() != UserRole.STUDENT)
            throw ApiException.forbidden("본인의 일정만 삭제할 수 있습니다.");
        Schedule s = scheduleRepo.findByIdAndUserId(scheduleId, u.getId())
                .orElseThrow(() -> ApiException.notFound("일정을 찾을 수 없습니다."));
        scheduleRepo.delete(s);
        return Map.of("status", "deleted", "id", scheduleId);
    }

    @GetMapping("/student/{studentId}")
    public List<ScheduleDtos.Response> listStudent(
            @PathVariable Integer studentId,
            @RequestParam(required = false) String date_from,
            @RequestParam(required = false) String date_to,
            @AuthenticationPrincipal AuthPrincipal principal) {
        Accounts.AccountInfo info = accounts.requireUserOrAdmin(principal);
        ensureCanViewStudent(info, studentId);
        return scheduleRepo.findInRange(studentId, date_from, date_to)
                .stream().map(ScheduleDtos.Response::of).toList();
    }

    /** Admin은 모든 학생, Teacher는 매칭된 학생만 조회 가능 */
    private void ensureCanViewStudent(Accounts.AccountInfo info, Integer studentId) {
        User student = userRepo.findById(studentId)
                .orElseThrow(() -> ApiException.notFound("학생을 찾을 수 없습니다."));
        if (student.getRole() != UserRole.STUDENT)
            throw ApiException.badRequest("학생 계정이 아닙니다.");
        if (info.isAdmin()) return;
        User teacher = info.user();
        if (teacher.getRole() != UserRole.TEACHER
                || !teacher.getId().equals(student.getTeacherId()))
            throw ApiException.forbidden("해당 학생을 관리할 권한이 없습니다.");
    }
}
