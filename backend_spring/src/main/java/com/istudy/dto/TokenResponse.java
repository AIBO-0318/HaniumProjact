package com.istudy.dto;

/** JWT 토큰 응답 (FastAPI Token 스키마와 동일) */
public record TokenResponse(
        String access_token,
        String token_type,
        String account_type,
        String role,
        String name
) {
    public TokenResponse(String accessToken, String accountType, String role, String name) {
        this(accessToken, "bearer", accountType, role, name);
    }
}
