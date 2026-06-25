package com.istudy.config;

import com.istudy.security.JwtAuthenticationFilter;
import com.istudy.security.JwtUtil;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.List;

@Configuration
public class SecurityConfig {

    /** 정적 HTML 페이지 라우트 (인증 불필요로 노출 — 데이터는 토큰으로 별도 fetch) */
    private static final String[] PAGE_ROUTES = {
            "/", "/index.html", "/signup", "/main", "/calibration", "/whitelist",
            "/stats", "/schedule", "/mypage", "/dashboard", "/gaze-settings",
            "/teacher-whitelist", "/auto-login", "/admin-users", "/admin-stats",
            "/focus-mode", "/teacher-schedule"
    };

    private final JwtUtil jwtUtil;

    public SecurityConfig(JwtUtil jwtUtil) {
        this.jwtUtil = jwtUtil;
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        // Python bcrypt($2b$) 해시와 호환
        return new BCryptPasswordEncoder();
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .cors(c -> c.configurationSource(corsSource()))
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                // 인증/가입 (공개)
                .requestMatchers(HttpMethod.POST,
                        "/users/login", "/users/signup",
                        "/admins/login", "/admins/signup").permitAll()
                // 데스크톱 레거시 (익명)
                .requestMatchers("/api/**", "/headpose").permitAll()
                // 정적 리소스
                .requestMatchers("/static/**", "/favicon.ico", "/error").permitAll()
                // 정적 HTML 페이지
                .requestMatchers(HttpMethod.GET, PAGE_ROUTES).permitAll()
                // 그 외 모든 REST API → 인증 필요
                .anyRequest().authenticated()
            )
            .exceptionHandling(e -> e
                .authenticationEntryPoint((req, res, ex) -> writeJson(res, 401, "Not authenticated"))
                .accessDeniedHandler((req, res, ex) -> writeJson(res, 403, "Forbidden"))
            )
            .addFilterBefore(new JwtAuthenticationFilter(jwtUtil),
                    UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    private static void writeJson(jakarta.servlet.http.HttpServletResponse res,
                                  int status, String detail) throws java.io.IOException {
        res.setStatus(status);
        res.setContentType("application/json;charset=UTF-8");
        res.getWriter().write("{\"detail\":\"" + detail + "\"}");
    }

    private CorsConfigurationSource corsSource() {
        CorsConfiguration cfg = new CorsConfiguration();
        cfg.setAllowedOriginPatterns(List.of("*"));
        cfg.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        cfg.setAllowedHeaders(List.of("*"));
        UrlBasedCorsConfigurationSource src = new UrlBasedCorsConfigurationSource();
        src.registerCorsConfiguration("/**", cfg);
        return src;
    }
}
