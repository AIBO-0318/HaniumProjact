# I-Study Changelog

모든 주요 변경사항을 기록합니다.  
형식: `[날짜] 버전 — 변경 내용`

---

## [2026-05-11] v0.3.1 — 방향 인식률 테스트 모듈 추가 & 앱 메뉴 정리

### 데스크톱 앱 (`ui_ux/desktop/app.py`)
- **제거**: 사이드바에서 화이트리스트·학습통계 메뉴 제거 (홈만 유지)
  - 학습통계 → 웹 `/stats` 페이지로 이전
  - 화이트리스트 수정 → 웹에서 지도자/관리자만 가능
- **버그수정**: 로그인 다이얼로그 `finally` 블록에서 destroy 후 버튼 접근 시 TclError 수정
- **개선**: `withdraw/deiconify` 제거 → `lift + focus_force`로 로그인 창 항상 최상단 표시

### 신규 모듈 (`model_test/`) — 기존 프로젝트와 완전 독립
- `collect_data.py` — 웹캠으로 방향별(정면/좌/우/위/아래) 이미지 수집
- `train.py` — MediaPipe 랜드마크 기반 RandomForest/SVM/MLP 비교 학습
- `evaluate.py` — 실시간 ML 모델 vs 임계값 방식 인식률 비교
- `requirements.txt` — scikit-learn만 추가 필요

### 문서
- `README.md` → SRS 형식으로 재작성 (10개 섹션)
- `CHANGELOG.md` → 신규 생성 (v0.1~v0.3 이력)
- HTML 캐시 버스팅: `style.css?v=4` 적용 (12개 파일)

---

## [2026-05-10] v0.3.0 — 앱·웹 DB 통합 및 UI 개편

### 데이터베이스
- **삭제**: `gaze_calibration`, `gaze_data`, `block_list`, `headpose_data` (중복·미사용 테이블)
- **통합**: `study_log` (데스크톱 전용) → `study_sessions` (웹·앱 공용)으로 마이그레이션 (22건 이전)
- **확장**: `study_sessions`에 `login_id`, `start_time`, `end_time`, `total_time_seconds`, `focus_time_seconds` 컬럼 추가
- **변경**: `study_sessions.user_id` NOT NULL → nullable (앱은 login_id로 식별)

### 백엔드 (`backend_db/`)
- `models.py`: `StudySession` 모델 컬럼 동기화
- `api/stats.py`: 통계 쿼리를 `user_id OR login_id` 기반으로 변경 → 앱 데이터도 웹 통계에 반영

### 데스크톱 앱 (`ui_ux/desktop/`)
- **신규**: `dialogs/login.py` — 앱 시작 시 로그인 다이얼로그 (웹 백엔드 인증, 오프라인 모드 지원)
- `app.py`: 로그인 후 `login_id` 저장, `save_study_log()` 호출 시 `login_id` 전달
- `app.py`: **사이드바에서 화이트리스트·학습통계 메뉴 제거** (홈만 유지)
  - 학습통계 → 웹 대시보드에서 확인
  - 화이트리스트 → 웹에서 지도자/관리자만 수정 가능

### AI 코어 (`ai_core/database.py`)
- `_create_tables()`: `study_log` 대신 `study_sessions` 테이블 생성
- `save_study_log()`: `study_sessions`에 저장, `login_id` / `focus_score` / `focused_min` 등 추가 파라미터 지원
- `get_study_logs()`: `login_id` 필터 파라미터 추가
- `get_today_total_focus_time()`: `login_id` 필터 파라미터 추가

### UI/CSS (`ui_ux/web/styles/style.css`)
- Toss-style 디자인 시스템 v3 적용
  - 배경: 소프트 라벤더-블루 방사형 그라데이션
  - 카드: Glassmorphism (`backdrop-filter: blur`)
  - 버튼: 알약형(`border-radius: 50px`) + 파란 그라데이션 + 글로우 그림자
  - 색상 스와치: 단일색 → 영롱한 파스텔 그라데이션 + 색상별 글로우
  - 입력 필드: 연한 라벤더 배경 + 포커스 시 블루 링
- 모든 HTML에 `?v=4` 캐시 버스팅 적용

---

## [2026-05-09] v0.2.0 — Toss-style UI 리팩토링

### UI/CSS
- `style.css` 전면 재작성: Toss 디자인 시스템 적용
  - CSS 변수로 색상/그림자/반경 토큰 정의
  - Topbar: `nav.js` 생성 구조(`topbar`, `topbar-left`, `topbar-nav`, `topbar-right`)에 맞게 수정
  - 대시보드 요약 3칸 (`stat-row`): 대형 숫자 + 단위
  - 메뉴 타일 그리드 3×2 (`tile-grid`)
- 마이페이지 CSS 추가: `.profile`, `.avatar`, `.info-row`, `.ok`, `.pending`
- 일정표 CSS 추가: `.schedule-grid`, `.schedule-item`, `.color-picker`, `.swatch`

### 백엔드
- `backend_db/main.py`: 정적 파일 마운트 경로 `/static/styles` → `/static/css` 수정

---

## [2026-05-08] v0.1.0 — 초기 구조

### 백엔드
- FastAPI 기반 REST API 구현
- JWT 인증 (사용자/관리자 분리)
- PostgreSQL 연동 (SQLAlchemy ORM)
- 웹 정적 파일 서빙

### 웹 프론트엔드
- 로그인/회원가입 페이지
- 메인 대시보드
- 일정표, 마이페이지, 화이트리스트, 통계 페이지

### 데스크톱 앱
- CustomTkinter 기반 UI
- MediaPipe 시선 추적
- 집중도 분석 (Focused / Dazed / Distracted)
- 학습 세션 기록

---

> **롤백 방법**: 특정 버전으로 되돌리려면 git 또는 이 파일의 변경 내용을 참고해 해당 파일을 수동 복원하세요.
