package com.istudy.dto;

import com.istudy.entity.User;
import com.istudy.entity.UserRole;
import jakarta.validation.constraints.*;

import java.time.LocalDateTime;

/** 사용자 관련 요청/응답 DTO 모음 (JSON 필드명은 기존 API 와 동일하게 snake_case 유지) */
public class UserDtos {

    public record SignupRequest(
            @NotBlank @Size(min = 4, max = 32) @Pattern(regexp = "^[a-zA-Z0-9_]+$")
            String login_id,
            @NotBlank @Size(min = 6, max = 64)
            String password,
            @NotBlank @Size(min = 1, max = 50)
            String name,
            UserRole role,
            @Pattern(regexp = "^[a-zA-Z0-9_]+$")
            String student_login_id
    ) {}

    public record LoginRequest(
            @NotBlank String login_id,
            @NotBlank String password
    ) {}

    public record Response(
            Integer id,
            String login_id,
            String name,
            UserRole role,
            Integer is_active,
            Integer teacher_id,
            LocalDateTime created_at
    ) {
        public static Response of(User u) {
            return new Response(u.getId(), u.getLoginId(), u.getName(), u.getRole(),
                    u.getIsActive(), u.getTeacherId(), u.getCreatedAt());
        }
    }
}
