# I-Study Backend (Spring Boot)

AI(실시간 시선추적)를 제외한 **모든 REST API + 정적 웹 서빙**을 담당하는 Spring Boot 백엔드.
기존 FastAPI(`backend_db`)에서 이전되었으며, AI 연산은 FastAPI가 계속 담당한다.

---

## 1. 아키텍처 (이전 후)

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│  Spring Boot (이 프로젝트)   │        │  FastAPI (backend_db)         │
│  포트 8000                   │        │  포트 8001                    │
│                              │        │                               │
│  - /users, /admins           │        │  - /ws/gaze (시선추적 AI)     │
│  - /schedules, /stats        │        │  - /health                    │
│  - /whitelist                │        │                               │
│  - /gaze-settings, /calibration       │  ※ AI 연산만 담당             │
│  - /api/* (데스크톱 레거시)  │        │                               │
│  - /headpose                 │        └──────────────────────────────┘
│  - 정적 웹(ui_ux/web) 서빙   │
└─────────────────────────────┘
            │  공유
            ▼
   PostgreSQL (istudy)  ← 두 서비스가 같은 DB/테이블 공유
```

- **REST + 웹**: Spring Boot (8000)
- **시선추적 WebSocket**: FastAPI (8001) — `backend_db/ai_server.py`
- **DB**: PostgreSQL `istudy` 한 개를 두 서비스가 공유
- **JWT**: Spring Boot 가 발급, FastAPI `/ws/gaze` 가 검증 → **시크릿/알고리즘 동일(HS256)**

---

## 2. 사전 준비물

| 항목 | 버전 | 비고 |
|------|------|------|
| JDK | 17 이상 | `java -version` 확인 |
| Gradle | 8.x (선택) | 없으면 아래 Wrapper 생성 단계 참고 |
| PostgreSQL | 14 이상 | DB명 `istudy` |
| Python | 3.10+ | FastAPI AI 서비스용 |

> 현재 개발 PC에 JDK/Gradle 미설치 상태입니다. 먼저 **JDK 17** 을 설치하세요.
> (예: Temurin 17 — https://adoptium.net)

---

## 3. 환경 변수 (`.env` 또는 OS 환경변수)

`shared/env_config.py` 와 동일한 값을 사용합니다.

```
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=aisw2026
DB_NAME=istudy

# ⚠️ FastAPI(/ws/gaze)와 반드시 동일하게!
JWT_SECRET=i-study-beta-change-this-in-production-please
```

application.yml 은 위 환경변수를 읽으며, 없으면 기본값을 사용합니다.

> **JWT_SECRET 주의**: HS256 특성상 시크릿은 **32바이트 이상**이어야 합니다.
> 기본값(44바이트)은 충족하지만, 짧은 값으로 바꾸면 부팅 시 오류가 납니다.

---

## 4. 빌드 & 실행

### 4-1. Gradle Wrapper 생성 (최초 1회)
이 저장소에는 wrapper 바이너리(`gradle-wrapper.jar`)가 포함되어 있지 않습니다.
JDK 설치 후, Gradle 이 설치되어 있다면:

```powershell
cd d:\I-Study\backend_spring
gradle wrapper --gradle-version 8.10
```

> Gradle 이 없다면 IntelliJ IDEA / Spring Tool Suite 로 `backend_spring` 폴더를 열면
> IDE 가 자동으로 의존성을 받아 빌드/실행할 수 있습니다.

### 4-2. 실행
```powershell
cd d:\I-Study\backend_spring
# wrapper 생성 후
.\gradlew.bat bootRun
# 또는 gradle 직접
gradle bootRun
```

### 4-3. 빌드 (배포용 JAR)
```powershell
.\gradlew.bat clean bootJar
java -jar build\libs\istudy-backend-1.0.0.jar
```

서버 접속:
- 웹: http://127.0.0.1:8000
- 로그인 API: `POST http://127.0.0.1:8000/users/login`

### 4-4. AI 서비스(FastAPI) 실행
```powershell
cd d:\I-Study
python run_ai_server.py    # http://127.0.0.1:8001 , ws://.../ws/gaze
```

---

## 5. DB 준비

기존 시스템을 쓰던 DB라면 테이블이 이미 존재하므로 추가 작업 불필요
(`application.yml` 의 `ddl-auto: none`).

**신규 DB** 를 처음 구성하는 경우에만 스키마를 수동 생성:
```powershell
psql -U postgres -d istudy -f src\main\resources\schema.sql
```

> `gaze_settings.role` 등 PostgreSQL `user_role` enum 타입을 사용하므로
> Hibernate 자동 DDL 대신 위 스키마 스크립트 사용을 권장합니다.

---

## 6. 엔드포인트 매핑 (FastAPI → Spring Boot)

| 구분 | 경로 | 이전 위치(FastAPI) | 현재 위치(Spring) |
|------|------|--------------------|-------------------|
| 사용자 | `/users/**` | `api/users.py` | `UserController` |
| 관리자 | `/admins/**` | `api/admins.py` | `AdminController` |
| 일정 | `/schedules/**` | `api/schedules.py` | `ScheduleController` |
| 통계 | `/stats/**` | `api/stats.py` | `StatsController` |
| 화이트리스트 | `/whitelist/**` | `api/whitelist.py` | `WhitelistController` |
| 시선 설정 | `/gaze-settings/**` | `api/gaze_settings.py` | `GazeSettingsController` |
| 캘리브레이션 | `/calibration/**` | `api/calibration.py` | `CalibrationController` |
| 레거시(데스크톱) | `/api/**` | `api/legacy.py` | `LegacyController` |
| 머리좌표 | `/headpose` | `main.py` | `HeadPoseController` |
| 정적 웹/페이지 | `/`, `/main` 등 | `main.py` | `WebPageController` + `WebConfig` |
| **시선추적 WS** | `/ws/gaze` | `api/gaze_ws.py` | **FastAPI 유지** |

응답/요청 JSON 필드명, HTTP 상태코드, 에러 형식(`{"detail": "..."}`)은 기존과 동일하게 유지했습니다.

---

## 7. 호환성 핵심 포인트

- **비밀번호**: Spring `BCryptPasswordEncoder` ↔ Python `bcrypt`($2b$) 해시 호환 → 기존 계정 그대로 로그인 가능.
- **JWT**: `sub / account_type / role / user_id / exp` 클레임 구조 동일, HS256 + 동일 시크릿 → Spring 발급 토큰을 FastAPI 가 검증.
- **DB**: 동일 테이블 공유. Spring 은 스키마를 변경하지 않음(`ddl-auto: none`).
- **포트**: 데스크톱 앱/웹의 `API_SERVER_URL` 기본값(8000)은 이제 Spring Boot 를 가리킴 → 변경 불필요.

---

## 8. 프로젝트 구조

```
backend_spring/
├─ build.gradle / settings.gradle
└─ src/main/
   ├─ java/com/istudy/
   │  ├─ IStudyApplication.java
   │  ├─ config/        SecurityConfig, WebConfig
   │  ├─ security/      JwtUtil, JwtAuthenticationFilter, AuthPrincipal, Accounts
   │  ├─ entity/        User, Admin, WhitelistUrl, Schedule, GazeSettings, StudySession, HeadPoseData, UserRole
   │  ├─ repository/    *Repository (Spring Data JPA)
   │  ├─ dto/           요청/응답 레코드
   │  ├─ controller/    각 도메인 컨트롤러
   │  └─ exception/     ApiException, GlobalExceptionHandler
   └─ resources/
      ├─ application.yml
      └─ schema.sql     (신규 DB 구성용, 수동 실행)
```

자세한 마이그레이션/백업/롤백 절차는 [`docs/BACKEND_MIGRATION.md`](../docs/BACKEND_MIGRATION.md) 참고.
