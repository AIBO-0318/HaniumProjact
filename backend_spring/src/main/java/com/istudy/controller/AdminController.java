package com.istudy.controller;

import com.istudy.dto.AdminDtos;
import com.istudy.dto.TokenResponse;
import com.istudy.entity.Admin;
import com.istudy.entity.User;
import com.istudy.entity.UserRole;
import com.istudy.exception.ApiException;
import com.istudy.repository.AdminRepository;
import com.istudy.repository.UserRepository;
import com.istudy.security.AuthPrincipal;
import com.istudy.security.Accounts;
import com.istudy.security.JwtUtil;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** /admins/* — 관리자 가입/로그인/사용자관리/통계 */
@RestController
@RequestMapping("/admins")
public class AdminController {

    private final AdminRepository adminRepo;
    private final UserRepository userRepo;
    private final PasswordEncoder encoder;
    private final JwtUtil jwt;
    private final Accounts accounts;

    public AdminController(AdminRepository adminRepo, UserRepository userRepo,
                           PasswordEncoder encoder, JwtUtil jwt, Accounts accounts) {
        this.adminRepo = adminRepo;
        this.userRepo = userRepo;
        this.encoder = encoder;
        this.jwt = jwt;
        this.accounts = accounts;
    }

    @PostMapping("/signup")
    @ResponseStatus(HttpStatus.CREATED)
    public AdminDtos.Response signup(@Valid @RequestBody AdminDtos.SignupRequest req) {
        if (adminRepo.existsByAdminId(req.admin_id()))
            throw ApiException.badRequest("이미 존재하는 관리자 아이디입니다.");
        Admin admin = new Admin();
        admin.setAdminId(req.admin_id());
        admin.setPasswordHash(encoder.encode(req.password()));
        admin.setName(req.name());
        admin.setLevel(req.level() != null ? req.level() : 1);
        return AdminDtos.Response.of(adminRepo.save(admin));
    }

    @PostMapping(value = "/login", consumes = MediaType.APPLICATION_JSON_VALUE)
    public TokenResponse login(@Valid @RequestBody AdminDtos.LoginRequest req) {
        return doLogin(req.admin_id(), req.password());
    }

    /** OAuth2 form-data 호환 (데스크톱 앱 username/password) */
    @PostMapping(value = "/login", consumes = MediaType.APPLICATION_FORM_URLENCODED_VALUE)
    public TokenResponse loginForm(@RequestParam String username, @RequestParam String password) {
        return doLogin(username, password);
    }

    private TokenResponse doLogin(String adminId, String password) {
        Admin admin = adminRepo.findByAdminId(adminId)
                .filter(a -> encoder.matches(password, a.getPasswordHash()))
                .orElseThrow(() -> ApiException.unauthorized("아이디 또는 비밀번호가 올바르지 않습니다."));
        String token = jwt.create(admin.getAdminId(), "admin", "ADMIN", admin.getId());
        return new TokenResponse(token, "admin", "ADMIN", admin.getName());
    }

    @GetMapping("/me")
    public AdminDtos.Response me(@AuthenticationPrincipal AuthPrincipal principal) {
        return AdminDtos.Response.of(accounts.requireAdmin(principal));
    }

    @GetMapping("/users")
    public List<Map<String, Object>> listUsers(@AuthenticationPrincipal AuthPrincipal principal) {
        accounts.requireAdmin(principal);
        List<User> users = userRepo.findAllByOrderByCreatedAtDesc();
        Map<Integer, User> byId = new HashMap<>();
        for (User u : users) byId.put(u.getId(), u);

        Map<Integer, List<Map<String, Object>>> studentsOf = new HashMap<>();
        for (User u : users) {
            if (u.getRole() == UserRole.STUDENT && u.getTeacherId() != null) {
                studentsOf.computeIfAbsent(u.getTeacherId(), k -> new ArrayList<>())
                        .add(Map.of("id", u.getId(), "login_id", u.getLoginId(), "name", u.getName()));
            }
        }

        List<Map<String, Object>> result = new ArrayList<>();
        for (User u : users) {
            Map<String, Object> item = new HashMap<>();
            item.put("id", u.getId());
            item.put("login_id", u.getLoginId());
            item.put("name", u.getName());
            item.put("role", u.getRole().name());
            item.put("is_active", u.getIsActive());
            item.put("teacher_id", u.getTeacherId());
            item.put("created_at", u.getCreatedAt() != null ? u.getCreatedAt().toString() : null);
            item.put("teacher_login_id", null);
            item.put("teacher_name", null);
            item.put("students", List.of());
            if (u.getRole() == UserRole.STUDENT && u.getTeacherId() != null && byId.containsKey(u.getTeacherId())) {
                User t = byId.get(u.getTeacherId());
                item.put("teacher_login_id", t.getLoginId());
                item.put("teacher_name", t.getName());
            } else if (u.getRole() == UserRole.TEACHER) {
                item.put("students", studentsOf.getOrDefault(u.getId(), List.of()));
            }
            result.add(item);
        }
        return result;
    }

    @PostMapping("/users/{userId}/approve")
    public Map<String, Object> approve(@PathVariable Integer userId,
                                       @AuthenticationPrincipal AuthPrincipal principal) {
        accounts.requireAdminLevel(principal, 1);
        User u = userRepo.findById(userId).orElseThrow(() -> ApiException.notFound("User not found"));
        u.setIsActive(1);
        userRepo.save(u);
        return Map.of("status", "approved", "user_id", userId);
    }

    @PostMapping("/users/{userId}/reject")
    public Map<String, Object> reject(@PathVariable Integer userId,
                                      @AuthenticationPrincipal AuthPrincipal principal) {
        accounts.requireAdminLevel(principal, 1);
        User u = userRepo.findById(userId).orElseThrow(() -> ApiException.notFound("User not found"));
        u.setIsActive(0);
        userRepo.save(u);
        return Map.of("status", "rejected", "user_id", userId);
    }

    @DeleteMapping("/users/{userId}")
    public Map<String, Object> delete(@PathVariable Integer userId,
                                      @AuthenticationPrincipal AuthPrincipal principal) {
        accounts.requireAdminLevel(principal, 9);
        User u = userRepo.findById(userId).orElseThrow(() -> ApiException.notFound("User not found"));
        userRepo.delete(u);
        return Map.of("status", "deleted", "user_id", userId);
    }

    @GetMapping("/stats")
    public Map<String, Object> systemStats(@AuthenticationPrincipal AuthPrincipal principal) {
        accounts.requireAdmin(principal);
        return Map.of(
                "total_users", userRepo.count(),
                "students", userRepo.countByRole(UserRole.STUDENT.name()),
                "teachers", userRepo.countByRole(UserRole.TEACHER.name()),
                "pending", userRepo.countByIsActive(0)
        );
    }
}
