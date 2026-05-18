# 📘 I-Study — 소프트웨어 요구사항 명세서 (SRS)

> **문서 버전**: v0.3.0 | **최종 수정**: 2026-05-10  
> AI 시선 추적 기반 스마트 학습 집중도 관리 시스템

---

## 1. 개요

### 1.1 목적
I-Study는 학생의 학습 집중도를 실시간으로 측정·기록하고, 학습지도자와 관리자가 이를 관리할 수 있는 통합 학습 관리 플랫폼입니다.

### 1.2 범위
| 구성 요소 | 설명 |
|-----------|------|
| **데스크톱 앱** | 시선 추적 + 집중도 모니터링 (학생 전용) |
| **웹 대시보드** | 일정 관리, 학습 통계 조회, 화이트리스트 설정 |
| **백엔드 API** | 인증, 데이터 저장, 통계 제공 |

### 1.3 사용자 역할
| 역할 | 설명 | 주요 기능 |
|------|------|-----------|
| **학생 (STUDENT)** | 학습 당사자 | 집중 모드, 일정, 통계, 화이트리스트 조회 |
| **학습지도자 (TEACHER)** | 학생 관리자 | 학생 일정·화이트리스트 관리 |
| **관리자 (ADMIN)** | 시스템 관리자 | 전체 사용자 승인·관리 |

---

## 2. 기능 요구사항

### 2.1 데스크톱 앱 (학생 전용)
| ID | 기능 | 설명 | 우선순위 |
|----|------|------|----------|
| DA-01 | 로그인 연동 | 앱 시작 시 웹 계정으로 로그인, 오프라인 모드 지원 | 高 |
| DA-02 | 시선 추적 | MediaPipe로 머리 방향·눈 감음 실시간 감지 | 高 |
| DA-03 | 집중도 분석 | Focused / Dazed / Distracted 3단계 상태 판정 | 高 |
| DA-04 | 이탈 경고 | 시선 이탈·눈 감음 감지 시 팝업 경고 | 高 |
| DA-05 | 학습 기록 저장 | 세션 종료 시 `study_sessions` 테이블에 기록 | 高 |
| DA-06 | 시야각 보정 | 9점 캘리브레이션으로 사용자별 시선 범위 보정 | 中 |

> **제거된 기능**: 화이트리스트 관리, 학습 통계 → 웹으로 이전

### 2.2 웹 대시보드
| ID | 기능 | 접근 권한 | 우선순위 |
|----|------|-----------|----------|
| WB-01 | 로그인/회원가입 | 비로그인 | 高 |
| WB-02 | 메인 대시보드 | 전체 | 高 |
| WB-03 | 학습 통계 조회 | 학생 | 高 |
| WB-04 | 학습 일정 관리 | 학생 | 高 |
| WB-05 | 화이트리스트 조회 | 학생 | 中 |
| WB-06 | 화이트리스트 수정 | **지도자/관리자만** | 高 |
| WB-07 | 학생 일정 조회 | 지도자 | 中 |
| WB-08 | 사용자 승인 | 관리자 | 高 |
| WB-09 | 시선 보정/설정 | 학생 | 中 |

### 2.3 백엔드 API
| ID | 엔드포인트 | 기능 |
|----|------------|------|
| BE-01 | `POST /users/login` | JWT 발급 |
| BE-02 | `GET /stats/daily` | 일별 학습 통계 |
| BE-03 | `GET /stats/weekly` | 주별 학습 통계 |
| BE-04 | `POST /stats/sessions` | 학습 세션 저장 |
| BE-05 | `GET /schedules` | 일정 조회 |
| BE-06 | `GET /whitelist` | 화이트리스트 조회 |
| BE-07 | `POST /whitelist/{student_id}` | 화이트리스트 추가 (지도자/관리자) |

---

## 3. 데이터베이스 구조

### 3.1 현행 테이블 (7개)

| 테이블 | 주요 컬럼 | 설명 |
|--------|-----------|------|
| `users` | id, login_id, role, teacher_id | 학생/지도자 |
| `admins` | id, admin_id, level | 관리자 |
| `study_sessions` | user_id, login_id, date, focus_score | **웹·앱 통합** 학습 기록 |
| `schedules` | user_id, date, title, is_done | 학습 일정 |
| `gaze_settings` | user_id, ear_threshold, yaw_threshold | 사용자별 시선 설정 |
| `whitelist_urls` | user_id, name, url | 허용 URL (NULL=공용) |
| `head_pose_data` | student_id, x, y | 시선 좌표 로그 |

### 3.2 웹·앱 데이터 연동 방식
```
데스크톱 앱 (login_id='alice')
    ↓ save_study_log(login_id='alice', ...)
study_sessions.login_id = 'alice'
    ↓
웹 통계 API (GET /stats/daily)
    → WHERE user_id = current.id OR login_id = current.login_id
```

---

## 4. 비기능 요구사항

| 항목 | 요구사항 |
|------|----------|
| **응답 시간** | 시선 추적 30fps 이상 유지 |
| **보안** | JWT 24시간 만료, bcrypt 비밀번호 해싱 |
| **호환성** | Windows 10/11 64-bit |
| **오프라인** | 백엔드 미연결 시 앱 단독 실행 가능 |

---

## 5. 시스템 요구사항

| 항목 | 최소 | 권장 |
|------|------|------|
| OS | Windows 10 (64-bit) | Windows 11 |
| CPU | Intel i3 / Ryzen 3 | Intel i5 / Ryzen 5 |
| RAM | 4GB | 8GB |
| Python | 3.10 | 3.10+ |
| 웹캠 | 480p 30fps | 720p 30fps |
| DB | PostgreSQL 14+ | PostgreSQL 16 |

---

## 6. 기술 스택

| 분류 | 기술 |
|------|------|
| **AI/영상** | MediaPipe 0.10+, OpenCV 4.8+, NumPy |
| **백엔드** | FastAPI, SQLAlchemy 2.0, PostgreSQL |
| **인증** | JWT (python-jose), bcrypt |
| **데스크톱 UI** | CustomTkinter 5.2+, Matplotlib |
| **웹 프론트** | HTML/CSS/JS (Toss-style 디자인) |
| **시스템** | pyautogui, psutil, pygetwindow |

---

## 7. 프로젝트 구조

```
I-Study/
├── main.py                 # 진입점 (서버 + 데스크톱 앱 동시 실행)
├── run_desktop.py          # 데스크톱 앱 런처
├── run_backend.py          # 백엔드 서버만 실행
├── requirements.txt
├── CHANGELOG.md            # 버전별 변경사항 기록
│
├── ai_core/                # AI/Core 팀
│   ├── gaze_tracker.py     #   시선 추적 엔진
│   ├── monitor.py          #   화이트리스트 URL 모니터링
│   └── database.py         #   PostgreSQL DB 연결
│
├── backend_db/             # Backend/DB 팀
│   ├── main.py             #   FastAPI 앱 + 정적 파일 서빙
│   ├── models.py           #   DB ORM 모델
│   ├── auth.py             #   JWT 인증
│   └── api/                #   라우터 (users, admins, stats, schedules, whitelist, ...)
│
├── ui_ux/                  # UI/UX 팀
│   ├── desktop/            #   데스크톱 앱 (CustomTkinter)
│   │   ├── app.py          #     메인 앱 (홈만 표시)
│   │   ├── pages/home_page.py
│   │   └── dialogs/        #     로그인, 캘리브레이션, 팝업
│   └── web/                #   웹 프론트엔드
│       ├── pages/          #     HTML 12개
│       ├── scripts/        #     api.js, auth.js, nav.js
│       └── styles/style.css#     Toss-style CSS v3
│
└── shared/                 # 공용 유틸
    ├── config.py
    └── api_client.py
```

---

## 8. 실행 방법

> 사용 목적에 따라 세 가지 방법 중 하나를 선택하세요.

---

### ✅ 방법 A — 웹 브라우저로 접속 (가장 간단)

배포된 서버 URL을 브라우저에 입력하면 바로 사용 가능합니다.  
PostgreSQL, Python 설치 **불필요**.

```
https://haniumproject.onrender.com   ← 실제 배포 URL
```

1. 위 URL 접속
2. **회원가입** → 관리자 승인 대기
3. 승인 후 로그인 → 사용 시작

> ⚠️ 무료 서버는 15분 미사용 시 슬립 상태가 됩니다. 첫 접속이 느릴 수 있습니다 (약 30초).

---

### ✅ 방법 B — 데스크톱 앱 다운로드 (EXE)

PC에 설치 없이 실행 파일만 다운받아 사용합니다.  
PostgreSQL, Python 설치 **불필요**.

1. [GitHub Releases](https://github.com/AIBO-0318/HaniumProjact/releases) 접속
2. 최신 버전의 `I-Study-Windows.zip` 다운로드
3. 압축 해제 → `I-Study.exe` 실행
4. 로그인 (방법 A에서 만든 계정 사용)

> **시스템 요구사항**: Windows 10/11 64-bit, 웹캠

---

### ✅ 방법 C — 개발자 로컬 실행

소스 코드를 직접 수정하거나 개발하는 경우.

#### 사전 요구사항
- Python 3.10+
- PostgreSQL 14+
- 웹캠

#### 설치

```bash
# 1. 저장소 클론
git clone https://github.com/AIBO-0318/HaniumProjact.git
cd HaniumProjact

# 2. 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate

# 3. 패키지 설치
pip install -r requirements.txt

# 4. 환경변수 설정
copy .env.example .env
# .env 파일을 열어 PostgreSQL 비밀번호 입력
```

#### 실행

```bash
# 데스크톱 앱 + 웹 서버 동시 실행
python run_desktop.py

# 웹 서버만 실행 (브라우저로 접속)
python run_backend.py
```

| 명령 | 접속 방법 |
|------|-----------|
| `python run_desktop.py` | 앱 창 자동 실행 + http://localhost:8000 |
| `python run_backend.py` | http://localhost:8000 |

#### 초기 관리자 계정 생성

서버 실행 후 http://localhost:8000/docs 에서 `POST /admins/signup` 호출:

```json
{
  "admin_id": "admin",
  "password": "비밀번호",
  "name": "관리자",
  "level": 9
}
```

이후 http://localhost:8000 에서 일반 회원가입 → 관리자 로그인 후 사용자 승인.

---

### 🔧 서버 배포 (개발자용)

#### 1. Neon에서 PostgreSQL 생성
1. [neon.tech](https://neon.tech) → GitHub 로그인
2. **Create Project** → 프로젝트 생성
3. 연결 문자열 복사: `postgresql://user:pass@ep-xxx.neon.tech/neondb`

#### 2. Render에서 웹 서버 배포
1. [render.com](https://render.com) → GitHub 로그인
2. **New → Web Service** → 이 저장소 선택
3. 설정:
   - **Root Directory**: `backend_db`
   - **Build Command**: `pip install -r ../requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Environment Variables** 추가:
   ```
   DATABASE_URL = (Neon에서 복사한 연결 문자열)
   JWT_SECRET   = (랜덤 문자열)
   ```
5. **Create Web Service** → 배포 완료 후 URL 확인

#### 3. EXE 빌드 (배포 URL 포함)

```bash
python build_exe.py
# 프롬프트에 Render URL 입력
# → dist/I-Study/ 폴더를 ZIP으로 압축 → GitHub Releases에 업로드
```

---

## 9. 웹 페이지 목록

| 경로 | 페이지 | 접근 권한 |
|------|--------|-----------|
| `/` | 로그인 | 비로그인 |
| `/signup` | 회원가입 | 비로그인 |
| `/main` | 메인 대시보드 | 로그인 |
| `/schedule` | 학습 일정 | 학생 |
| `/stats` | 학습 통계 | 학생 |
| `/calibration` | 시선 보정 | 학생 |
| `/whitelist` | 화이트리스트 조회 | 학생 |
| `/mypage` | 마이페이지 | 전체 |
| `/teacher-schedule` | 학생 일정 조회 | 지도자/관리자 |
| `/teacher-whitelist` | 화이트리스트 수정 | 지도자/관리자 |
| `/admin-users` | 사용자 관리 | 관리자 |
| `/admin-stats` | 학생 통계 조회 | 관리자 |

---

## 10. 변경 이력

변경사항은 [CHANGELOG.md](./CHANGELOG.md) 에서 관리합니다.  
롤백이 필요한 경우 해당 버전의 변경 내용을 참고하세요.

---

**I-Study Development Team** | 2026

