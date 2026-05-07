# I-Study 프로젝트 구조

## 📁 폴더 구조 (한눈에 보기)

```
d:\I-Study\
│
├── 🚀 run_desktop.py           ← 데스크톱 앱 실행 (서버 자동 시작)
├── 🚀 run_backend.py           ← 백엔드 서버만 실행
├── 📄 main.py                   ← 내부 진입점 (run_desktop.py가 호출)
├── 📄 requirements.txt          ← Python 패키지 목록
│
├── 🖥️  ui/                      ← 데스크톱 앱 UI
│   ├── app.py                   ← 메인 앱 (FocusEyePro)
│   ├── pages/                   ← 화면들 (홈 등)
│   └── dialogs/                 ← 팝업 (캘리브레이션, 알림)
│
├── 🎥 core/                     ← 얼굴/시선 추적 (데스크톱 전용)
│   ├── gaze_tracker.py          ← MediaPipe 시선 추적
│   ├── monitor.py               ← 화이트리스트 모니터링
│   └── database.py              ← PostgreSQL 직접 접근 (학습 로그)
│
├── 🔧 utils/                    ← 데스크톱 유틸리티
│   ├── api_client.py            ← 백엔드 API 호출
│   ├── helpers.py               ← 공용 헬퍼
│   └── logger_config.py         ← 로깅
│
├── 🌐 backend/                  ← FastAPI 서버
│   ├── main.py                  ← 서버 진입점
│   ├── auth.py                  ← JWT 인증
│   ├── models.py                ← DB 모델 (SQLAlchemy)
│   ├── schemas.py               ← 요청/응답 형식
│   ├── database.py              ← PostgreSQL 연결
│   └── routers/                 ← API 엔드포인트
│       ├── users.py             ← /users/signup, /users/login
│       ├── admins.py            ← /admins/*
│       ├── whitelist.py         ← /whitelist/*
│       ├── calibration.py       ← /calibration/*
│       ├── stats.py             ← /stats/*
│       ├── schedules.py         ← /schedules/*
│       ├── gaze_settings.py     ← /gaze-settings/*
│       └── legacy.py            ← 데스크톱 호환용 /api/*
│
├── 🖼️  frontend/                ← 웹사이트 (HTML/CSS/JS)
│   ├── index.html               ← 로그인
│   ├── signup.html              ← 회원가입
│   ├── main.html                ← 대시보드
│   ├── calibration.html         ← 시선 보정
│   ├── whitelist.html           ← 화이트리스트
│   ├── stats.html               ← 학습 통계
│   ├── schedule.html            ← 일정표
│   └── js/                      ← JavaScript
│       ├── auth.js              ← 로그인/로그아웃
│       ├── api.js               ← API 클라이언트
│       └── nav.js               ← 메뉴 네비게이션
│
├── 🧪 tests/                    ← 테스트 도구
│   ├── test_head_pose.py        ← 고개 방향 인식률 테스트
│   ├── detection_rate.py        ← 얼굴 감지율 테스트
│   ├── README.md                ← 테스트 사용법
│   └── face_landmarker.task     ← MediaPipe 모델
│
├── 📚 docs/                     ← 문서
│   ├── VSCODE_EXECUTION_GUIDE.md  ← VSCode 실행법
│   ├── PROJECT_STRUCTURE.md       ← 이 문서
│   └── SRS.md                     ← 요구사항
│
└── 📁 logs/                     ← 로그 파일
```

---

## 🎯 3가지 핵심 영역

### 1️⃣ 데스크톱 앱 (Desktop)
**관련 폴더**: `ui/` + `core/` + `utils/` + `main.py` + `run_desktop.py`

- 시선/얼굴 추적 (MediaPipe)
- 화이트리스트 모니터링
- 학습 타이머
- CustomTkinter UI

**실행**: `python run_desktop.py`

---

### 2️⃣ 백엔드 (Backend)
**관련 폴더**: `backend/` + `run_backend.py`

- FastAPI 서버 (포트 8000)
- JWT 인증
- PostgreSQL DB 관리
- REST API 제공

**실행**: `python run_backend.py`

---

### 3️⃣ 프론트엔드 (Frontend)
**관련 폴더**: `frontend/`

- 로그인/회원가입 페이지
- 학생/선생님 대시보드
- 시선 보정 (웹캠)
- 학습 통계 차트

**접속**: `http://127.0.0.1:8000` (백엔드가 서빙)

---

## 🔄 데이터 흐름

```
┌─────────────────┐
│  데스크톱 앱     │  ← ui/ + core/ + utils/
└────────┬────────┘
         │ HTTP API (utils/api_client.py)
         ↓
┌─────────────────┐     ┌──────────────┐
│  FastAPI 서버   │ ──→ │  PostgreSQL  │
│  (backend/)     │     │   (istudy)   │
└─────────────────┘     └──────────────┘
         ↑
         │ HTTP API (frontend/js/api.js)
┌────────┴────────┐
│   웹사이트       │  ← frontend/
└─────────────────┘
```

---

## 📦 모든 데이터는 PostgreSQL에

```
PostgreSQL (istudy DB)
├── users               ← 사용자 (학생/선생님)
├── admins              ← 관리자
├── gaze_settings       ← 시선 보정 설정
├── gaze_data           ← 실시간 시선 데이터
├── head_pose_data      ← 머리 방향 데이터
├── study_sessions      ← 학습 세션 통계
├── study_log           ← 학습 상세 로그
├── whitelist_urls      ← 학생별 화이트리스트
├── block_list          ← 차단 사이트
└── schedules           ← 일정표
```

---

## ▶️ 실행 명령어 정리

| 명령어 | 효과 |
|--------|------|
| `python run_desktop.py` | 🖥️ 데스크톱 앱 + 🌐 서버 자동 시작 |
| `python run_backend.py` | 🌐 백엔드 서버만 실행 |
| `python tests/test_head_pose.py` | 🧪 고개 인식률 테스트 |
| `python tests/detection_rate.py` | 🧪 얼굴 감지율 테스트 |
