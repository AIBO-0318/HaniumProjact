package com.istudy.controller;

import com.istudy.dto.TokenResponse;
import com.istudy.dto.UserDtos;
import com.istudy.entity.User;
import com.istudy.entity.UserRole;
import com.istudy.exception.ApiException;
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

import java.util.List;
import java.util.Map;

/** /users/* — 회원가입 · 로그인 · 본인 정보 · Role 기반 보호 엔드포인트 */
@RestController
@RequestMapping("/users")
public class UserController {

    private final UserRepository userRepo;
    private final PasswordEncoder encoder;
    private final JwtUtil jwt;
    private final Accounts accounts;

    public UserController(UserRepository userRepo, PasswordEncoder encoder,
                          JwtUtil jwt, Accounts accounts) {
        this.userRepo = userRepo;
        this.encoder = encoder;
        this.jwt = jwt;
        this.accounts = accounts;
    }

    @PostMapping("/signup")
    @ResponseStatus(HttpStatus.CREATED)
    public UserDtos.Response signup(@Valid @RequestBody UserDtos.SignupRequest req) {
        if (userRepo.existsByLoginId(req.login_id()))
            throw ApiException.badRequest("이미 존재하는 아이디입니다.");

        UserRole role = req.role() != null ? req.role() : UserRole.STUDENT;
        User targetStudent = null;
        if (role == UserRole.TEACHER) {
            if (req.student_login_id() == null || req.student_login_id().isBlank())
                throw ApiException.badRequest("학습 지도자는 '관리할 학생 아이디'를 입력해야 합니다.");
            targetStudent = userRepo.findByLoginIdAndRole(req.student_login_id(), UserRole.STUDENT.name())
                    .orElseThrow(() -> ApiException.badRequest(
                            "학생 아이디 '" + req.student_login_id() + "' 를 찾을 수 없습니다."));
        }

        User user = new User();
        user.setLoginId(req.login_id());
        user.setPasswordHash(encoder.encode(req.password()));
        user.setName(req.name());
        user.setRole(role);
        user.setIsActive(1);
        user = userRepo.save(user);

        if (role == UserRole.TEACHER && targetStudent != null) {
            targetStudent.setTeacherId(user.getId());
            userRepo.save(targetStudent);
        }
        return UserDtos.Response.of(user);
    }

    @PostMapping(value = "/login", consumes = MediaType.APPLICATION_JSON_VALUE)
    public TokenResponse login(@Valid @RequestBody UserDtos.LoginRequest req) {
        return doLogin(req.login_id(), req.password());
    }

    /** OAuth2 form-data 호환 (데스크톱 앱 username/password) */
    @PostMapping(value = "/login", consumes = MediaType.APPLICATION_FORM_URLENCODED_VALUE)
    public TokenResponse loginForm(@RequestParam String username, @RequestParam String password) {
        return doLogin(username, password);
    }

    private TokenResponse doLogin(String loginId, String password) {
        User user = userRepo.findByLoginId(loginId)
                .filter(u -> encoder.matches(password, u.getPasswordHash()))
                .orElseThrow(() -> ApiException.unauthorized("아이디 또는 비밀번호가 올바르지 않습니다."));
        if (user.getIsActive() == null || user.getIsActive() == 0)
            throw ApiException.forbidden("관리자 승인 대기 중입니다.");

        String token = jwt.create(user.getLoginId(), "user", user.getRole().name(), user.getId());
        return new TokenResponse(token, "user", user.getRole().name(), user.getName());
    }

    @GetMapping("/me")
    public UserDtos.Response me(@AuthenticationPrincipal AuthPrincipal principal) {
        return UserDtos.Response.of(accounts.requireUser(principal));
    }

    @GetMapping("/student/sessions")
    public Map<String, Object> studentSessions(@AuthenticationPrincipal AuthPrincipal principal) {
        User u = accounts.requireUser(principal);
        if (u.getRole() != UserRole.STUDENT)
            throw ApiException.forbidden("Required role: STUDENT");
        return Map.of(
                "message", u.getName() + "님의 학습 기록",
                "student_id", u.getLoginId(),
                "sessions", List.of()
        );
    }

    @GetMapping("/teacher/students")
    public Map<String, Object> teacherStudents(@AuthenticationPrincipal AuthPrincipal principal) {
        User u = accounts.requireUser(principal);
        if (u.getRole() != UserRole.TEACHER)
            throw ApiException.forbidden("Required role: TEACHER");
        List<Map<String, Object>> students = userRepo
                .findByTeacherIdAndRole(u.getId(), UserRole.STUDENT.name()).stream()
                .map(s -> Map.<String, Object>of(
                        "id", s.getId(), "login_id", s.getLoginId(), "name", s.getName()))
                .toList();
        return Map.of("teacher", u.getName(), "students", students);
    }
}
