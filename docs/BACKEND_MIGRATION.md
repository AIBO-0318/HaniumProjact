# 백엔드 마이그레이션 & 백업 가이드 (FastAPI → Spring Boot)

> 목적: REST/웹 백엔드를 **FastAPI → Java Spring Boot** 로 이전.
> **AI(실시간 시선추적 `/ws/gaze`)만 FastAPI 유지.**
> 만약 롤백이 필요할 경우를 대비해 원본 보존 및 복구 절차를 기록한다.

---

## 1. 변경 요약

| 항목 | 이전 | 이후 |
|------|------|------|
| REST API (users/admins/schedules/stats/whitelist/gaze-settings/calibration/legacy/headpose) | FastAPI `backend_db` | **Spring Boot `backend_spring` (8000)** |
| 정적 웹 서빙 (`ui_ux/web`) | FastAPI `backend_db/main.py` | **Spring Boot `WebPageController`/`WebConfig` (8000)** |
| 실시간 시선추적 WebSocket `/ws/gaze` | FastAPI `backend_db/api/gaze_ws.py` | **FastAPI 유지 `backend_db/ai_server.py` (8001)** |
| DB | PostgreSQL `istudy` | **동일 DB 공유 (변경 없음)** |

---

## 2. 원본(백업) 보존 현황

마이그레이션 과정에서 **기존 FastAPI 코드는 삭제하지 않고 그대로 보존**했다.
따라서 아래 파일들이 "백업본"이자 "롤백 소스" 역할을 한다.

```
backend_db/
├─ main.py                 ← (구) 전체 FastAPI 앱 (모든 라우터 + 웹 서빙) — 보존됨
├─ ai_server.py            ← (신) AI 전용 FastAPI 앱 (/ws/gaze 만)
├─ auth.py                 ← JWT/bcrypt (FastAPI용, 보존)
├─ models.py / schemas.py / database.py   ← (보존)
└─ api/
   ├─ users.py  admins.py  schedules.py  stats.py
   ├─ whitelist.py  gaze_settings.py  calibration.py  legacy.py
   │   └─ 위 8개 = Spring Boot 로 이전됨. FastAPI 버전은 백업으로 보존.
   └─ gaze_ws.py           ← 현재도 사용(AI). ai_server.py 가 이것을 마운트.
```

> 즉, `backend_db` 폴더 전체가 그대로 백업이다. 별도 압축 백업이 필요하면
> `backend_db` 와 `shared/`, `.env` 를 함께 보관하면 구 버전을 100% 복원할 수 있다.

권장 백업 명령(선택):
```powershell
# 구 백엔드 스냅샷 zip 보관
Compress-Archive -Path backend_db, shared, .env.example -DestinationPath backup_fastapi_backend.zip
```

---

## 3. 평상시 실행 (이전 후 정상 구성)

두 서비스를 동시에 띄운다.

```powershell
# 터미널 1 — Spring Boot (REST + 웹, 8000)
cd d:\I-Study\backend_spring
.\gradlew.bat bootRun        # 최초엔 'gradle wrapper' 로 wrapper 생성 필요

# 터미널 2 — FastAPI AI (시선추적 WS, 8001)
cd d:\I-Study
python run_ai_server.py
```

- 웹/REST: http://127.0.0.1:8000
- AI WS: ws://127.0.0.1:8001/ws/gaze

데스크톱 앱/웹의 서버 URL 기본값(`API_SERVER_URL=http://127.0.0.1:8000`)은
그대로 Spring Boot 를 가리키므로 수정할 필요가 없다.

---

## 4. 롤백 절차 (다시 FastAPI 전체로 되돌리기)

Spring Boot 에 문제가 생기면 아래로 구 FastAPI 단일 백엔드로 즉시 복귀할 수 있다.

```powershell
# Spring Boot 중지 후
cd d:\I-Study
python run_backend.py        # backend_db/main.py (모든 라우터 + 웹 + /ws/gaze) on 8000
```

- `backend_db/main.py` 는 손대지 않았으므로 구 버전 그대로 전체 기능(8000)을 제공한다.
- 이 경우 `run_ai_server.py`(8001)는 띄우지 않아도 된다 (`main.py` 가 `/ws/gaze` 포함).
- DB 스키마는 동일하므로 데이터 마이그레이션 없이 즉시 동작한다.

---

## 5. 호환성 검증 체크리스트

이전 후 다음을 확인하면 정상 동작을 보장할 수 있다.

- [ ] 기존 계정으로 `POST /users/login` 로그인 성공 (bcrypt 해시 호환)
- [ ] 발급된 토큰으로 `GET /users/me` 200 응답
- [ ] 같은 토큰으로 FastAPI `ws://127.0.0.1:8001/ws/gaze` 연결 성공 (JWT_SECRET 동일 확인)
- [ ] `GET /stats/daily?days=7` 기존과 동일 형식 JSON
- [ ] 관리자 로그인 → `GET /admins/users` 목록 조회
- [ ] 웹 페이지 `/main`, `/stats` 등 정상 렌더링 (정적 서빙)
- [ ] 데스크톱 앱 로그인 / 세션 저장(`POST /stats/sessions`) 동작

---

## 6. 주의 사항

1. **JWT_SECRET 동일**: Spring Boot 와 FastAPI 의 `JWT_SECRET` 이 다르면
   `/ws/gaze` 토큰 검증이 실패한다. `.env` 또는 환경변수로 같은 값을 주입할 것.
2. **포트 충돌**: Spring(8000)과 FastAPI(8001)는 서로 다른 포트를 쓴다.
   롤백 시 `main.py`(8000)만 단독 실행한다.
3. **DB 스키마 변경 금지**: Spring 은 `ddl-auto: none` 으로 스키마를 건드리지 않는다.
   스키마 변경이 필요하면 `schema.sql` / 마이그레이션 스크립트로 명시적으로 수행.
4. **user_role enum**: PostgreSQL 사용자 정의 enum 이므로 JPA 엔티티는
   `@ColumnTransformer(write = "?::user_role")` 로 캐스팅 처리되어 있다.
