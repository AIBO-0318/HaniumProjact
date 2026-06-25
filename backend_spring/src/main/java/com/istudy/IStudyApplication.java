package com.istudy;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * I-Study 백엔드 (Spring Boot)
 *
 * AI(실시간 시선추적 WebSocket /ws/gaze)를 제외한 모든 REST API + 정적 웹 서빙을 담당.
 * AI 연산은 별도 FastAPI 서비스(backend_db)가 담당한다.
 */
@SpringBootApplication
public class IStudyApplication {
    public static void main(String[] args) {
        SpringApplication.run(IStudyApplication.class, args);
    }
}
