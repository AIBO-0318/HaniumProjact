package com.istudy.security;

import com.istudy.entity.Admin;
import com.istudy.entity.User;
import com.istudy.exception.ApiException;
import com.istudy.repository.AdminRepository;
import com.istudy.repository.UserRepository;
import org.springframework.stereotype.Component;

/**
 * AuthPrincipal → 실제 엔티티 조회 헬퍼.
 * FastAPI auth.py 의 get_current_user / get_current_admin / get_current_user_or_admin 대응.
 */
@Component
public class Accounts {

    private final UserRepository userRepo;
    private final AdminRepository adminRepo;

    public Accounts(UserRepository userRepo, AdminRepository adminRepo) {
        this.userRepo = userRepo;
        this.adminRepo = adminRepo;
    }

    /** 일반 사용자(Student/Teacher) 인증 — 비활성/없음 시 예외 */
    public User requireUser(AuthPrincipal p) {
        if (p == null) throw ApiException.unauthorized("Not authenticated");
        if (!p.isUser()) throw ApiException.forbidden("User account required");
        User u = userRepo.findById(p.userId())
                .orElseThrow(() -> ApiException.unauthorized("User not found or inactive"));
        if (u.getIsActive() == null || u.getIsActive() == 0)
            throw ApiException.unauthorized("User not found or inactive");
        return u;
    }

    /** 관리자 인증 */
    public Admin requireAdmin(AuthPrincipal p) {
        if (p == null) throw ApiException.unauthorized("Not authenticated");
        if (!p.isAdmin()) throw ApiException.forbidden("Admin account required");
        return adminRepo.findById(p.userId())
                .orElseThrow(() -> ApiException.unauthorized("Admin not found"));
    }

    /** 관리자 등급 가드 */
    public Admin requireAdminLevel(AuthPrincipal p, int minLevel) {
        Admin a = requireAdmin(p);
        if (a.getLevel() == null || a.getLevel() < minLevel)
            throw ApiException.forbidden("Admin level >= " + minLevel + " required");
        return a;
    }

    public record AccountInfo(User user, Admin admin, String accountType) {
        public boolean isAdmin() { return "admin".equals(accountType); }
    }

    /** User 또는 Admin 모두 허용 (get_current_user_or_admin) */
    public AccountInfo requireUserOrAdmin(AuthPrincipal p) {
        if (p == null) throw ApiException.unauthorized("Not authenticated");
        if (p.isAdmin()) {
            return new AccountInfo(null, requireAdmin(p), "admin");
        } else if (p.isUser()) {
            return new AccountInfo(requireUser(p), null, "user");
        }
        throw ApiException.forbidden("Invalid account type");
    }
}
