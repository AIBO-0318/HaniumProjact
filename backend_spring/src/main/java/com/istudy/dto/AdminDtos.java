package com.istudy.dto;

import com.istudy.entity.Admin;
import jakarta.validation.constraints.*;

import java.time.LocalDateTime;

public class AdminDtos {

    public record SignupRequest(
            @NotBlank @Size(min = 4, max = 32) @Pattern(regexp = "^[a-zA-Z0-9_]+$")
            String admin_id,
            @NotBlank @Size(min = 8, max = 64)
            String password,
            @NotBlank @Size(min = 1, max = 50)
            String name,
            @Min(1) @Max(9)
            Integer level
    ) {}

    public record LoginRequest(
            @NotBlank String admin_id,
            @NotBlank String password
    ) {}

    public record Response(
            Integer id,
            String admin_id,
            String name,
            Integer level,
            LocalDateTime created_at
    ) {
        public static Response of(Admin a) {
            return new Response(a.getId(), a.getAdminId(), a.getName(), a.getLevel(), a.getCreatedAt());
        }
    }
}
