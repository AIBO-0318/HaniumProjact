package com.istudy.controller;

import com.istudy.entity.User;
import com.istudy.entity.UserRole;
import com.istudy.entity.WhitelistUrl;
import com.istudy.exception.ApiException;
import com.istudy.repository.UserRepository;
import com.istudy.repository.WhitelistUrlRepository;
import com.istudy.security.AuthPrincipal;
import com.istudy.security.Accounts;
import jakarta.validation.constraints.NotBlank;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * /whitelist/* — 화이트리스트
 * 정책: 학생=effective 조회만 / 지도자=매칭 학생 관리 / 관리자=전체
 */
@RestController
@RequestMapping("/whitelist")
public class WhitelistController {

    private final WhitelistUrlRepository repo;
    private final UserRepository userRepo;
    private final Accounts accounts;

    public WhitelistController(WhitelistUrlRepository repo, UserRepository userRepo, Accounts accounts) {
        this.repo = repo;
        this.userRepo = userRepo;
        this.accounts = accounts;
    }

    public record CreateRequest(@NotBlank String name, @NotBlank String url) {}

    private static Map<String, Object> toResp(WhitelistUrl w) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", w.getId());
        m.put("name", w.getName());
        m.put("url", w.getUrl());
        m.put("user_id", w.getUserId());
        m.put("is_default", w.getUserId() == null);
        return m;
    }

    @GetMapping("/effective")
    public List<Map<String, Object>> effective(@AuthenticationPrincipal AuthPrincipal principal) {
        User u = accounts.requireUser(principal);
        if (u.getRole() != UserRole.STUDENT)
            throw ApiException.forbidden("학생 본인 전용 엔드포인트입니다.");
        return repo.findEffectiveForUser(u.getId()).stream()
                .map(WhitelistController::toResp).toList();
    }

    @GetMapping("/student/{studentId}")
    public List<Map<String, Object>> listStudent(@PathVariable Integer studentId,
                                                 @AuthenticationPrincipal AuthPrincipal principal) {
        ensureRoleCanManage(principal, studentId);
        return repo.findByUserIdOrderByCreatedAtDesc(studentId).stream()
                .map(WhitelistController::toResp).toList();
    }

    @PostMapping("/student/{studentId}")
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> addStudent(@PathVariable Integer studentId,
                                          @RequestBody CreateRequest body,
                                          @AuthenticationPrincipal AuthPrincipal principal) {
        ensureRoleCanManage(principal, studentId);
        if (repo.findByUserIdAndUrl(studentId, body.url()).isPresent())
            throw ApiException.badRequest("이미 등록된 URL입니다.");
        WhitelistUrl item = new WhitelistUrl();
        item.setName(body.name());
        item.setUrl(body.url());
        item.setUserId(studentId);
        return toResp(repo.save(item));
    }

    @DeleteMapping("/{urlId}")
    public Map<String, Object> delete(@PathVariable Integer urlId,
                                      @AuthenticationPrincipal AuthPrincipal principal) {
        WhitelistUrl item = repo.findById(urlId)
                .orElseThrow(() -> ApiException.notFound("URL을 찾을 수 없습니다."));
        if (item.getUserId() == null) {
            if (principal == null || !principal.isAdmin())
                throw ApiException.forbidden("기본 사이트는 관리자만 삭제할 수 있습니다.");
        } else {
            ensureRoleCanManage(principal, item.getUserId());
        }
        repo.delete(item);
        return Map.of("status", "deleted", "id", urlId);
    }

    @GetMapping("/admin/all")
    public List<Map<String, Object>> listAll(@AuthenticationPrincipal AuthPrincipal principal) {
        accounts.requireAdmin(principal);
        return repo.findAllByOrderByCreatedAtDesc().stream()
                .map(WhitelistController::toResp).toList();
    }

    @PostMapping("/admin/default")
    @ResponseStatus(HttpStatus.CREATED)
    public Map<String, Object> addDefault(@RequestBody CreateRequest body,
                                          @AuthenticationPrincipal AuthPrincipal principal) {
        accounts.requireAdmin(principal);
        if (repo.findDefaultByUrl(body.url()).isPresent())
            throw ApiException.badRequest("이미 등록된 기본 URL입니다.");
        WhitelistUrl item = new WhitelistUrl();
        item.setName(body.name());
        item.setUrl(body.url());
        item.setUserId(null);
        return toResp(repo.save(item));
    }

    /** 지도자: 매칭 학생만 / 관리자: 모두 / 학생: 차단 */
    private void ensureRoleCanManage(AuthPrincipal p, Integer studentId) {
        if (p == null) throw ApiException.unauthorized("유효하지 않은 토큰입니다.");
        if (p.isAdmin()) {
            userRepo.findById(studentId)
                    .filter(s -> s.getRole() == UserRole.STUDENT)
                    .orElseThrow(() -> ApiException.notFound("학생을 찾을 수 없습니다."));
            return;
        }
        if (!p.isUser()) throw ApiException.forbidden("권한이 없습니다.");
        if (p.isStudent()) throw ApiException.forbidden("학생은 화이트리스트를 관리할 수 없습니다.");
        if (p.isTeacher()) {
            User teacher = userRepo.findById(p.userId())
                    .orElseThrow(() -> ApiException.forbidden("권한이 없습니다."));
            User student = userRepo.findById(studentId)
                    .filter(s -> s.getRole() == UserRole.STUDENT)
                    .orElseThrow(() -> ApiException.notFound("학생을 찾을 수 없습니다."));
            if (teacher.getRole() != UserRole.TEACHER
                    || !teacher.getId().equals(student.getTeacherId()))
                throw ApiException.forbidden("해당 학생을 관리할 권한이 없습니다.");
            return;
        }
        throw ApiException.forbidden("권한이 없습니다.");
    }
}
