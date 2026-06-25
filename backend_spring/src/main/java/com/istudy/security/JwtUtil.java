package com.istudy.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.util.Date;

/**
 * JWT 발급/검증 유틸.
 *
 * FastAPI(python-jose) 와 HS256 + 동일 시크릿으로 상호 호환된다.
 * - 페이로드 클레임: sub, account_type, role, user_id, exp
 * - 시크릿은 raw UTF-8 바이트를 그대로 HMAC 키로 사용 (python-jose 와 동일)
 * - ⚠️ HS256 특성상 시크릿은 32바이트 이상이어야 함 (기본값은 44바이트)
 */
@Component
public class JwtUtil {

    private final SecretKey key;
    private final long expireMinutes;

    public JwtUtil(@Value("${app.jwt.secret}") String secret,
                   @Value("${app.jwt.expire-minutes:1440}") long expireMinutes) {
        this.key = new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
        this.expireMinutes = expireMinutes;
    }

    public String create(String subject, String accountType, String role, Integer userId) {
        Date now = new Date();
        Date exp = new Date(now.getTime() + expireMinutes * 60_000L);
        return Jwts.builder()
                .subject(subject)
                .claim("account_type", accountType)
                .claim("role", role)
                .claim("user_id", userId)
                .expiration(exp)
                .signWith(key, Jwts.SIG.HS256)
                .compact();
    }

    /** 토큰 → 인증 주체. 유효하지 않으면 예외 발생. */
    public AuthPrincipal parse(String token) {
        Claims c = Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
        Integer userId = c.get("user_id", Integer.class);
        return new AuthPrincipal(
                c.getSubject(),
                c.get("account_type", String.class),
                c.get("role", String.class),
                userId
        );
    }
}
