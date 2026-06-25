package com.istudy.security;

/**
 * JWT 페이로드에서 추출한 인증 주체.
 * FastAPI auth.py 의 페이로드 구조와 1:1 대응.
 *
 * { sub, account_type("user"|"admin"), role("STUDENT"|"TEACHER"|"ADMIN"), user_id }
 */
public record AuthPrincipal(
        String subject,        // login_id 또는 admin_id
        String accountType,    // "user" | "admin"
        String role,           // "STUDENT" | "TEACHER" | "ADMIN"
        Integer userId         // 해당 테이블의 PK
) {
    public boolean isAdmin()   { return "admin".equals(accountType); }
    public boolean isUser()    { return "user".equals(accountType); }
    public boolean isStudent() { return "STUDENT".equals(role); }
    public boolean isTeacher() { return "TEACHER".equals(role); }
}
