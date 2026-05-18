# I-Study 환경 구축 가이드

> 다른 PC에서 프로젝트, 데이터베이스, 서버를 처음부터 설정하는 방법입니다.

---

## 목차

1. [사전 준비](#1-사전-준비)
2. [프로젝트 설치](#2-프로젝트-설치)
3. [PostgreSQL 설치 및 DB 생성](#3-postgresql-설치-및-db-생성)
4. [FastAPI 서버 실행](#4-fastapi-서버-실행)
5. [데스크톱 앱 실행](#5-데스크톱-앱-실행)
6. [정상 동작 확인](#6-정상-동작-확인)
7. [서버 주소 변경 (원격 접속)](#7-서버-주소-변경-원격-접속)
8. [로그 파일 관리](#8-로그-파일-관리)
9. [문제 해결](#9-문제-해결)

---

## 1. 사전 준비

### 필수 소프트웨어

| 소프트웨어 | 버전 | 다운로드 |
|-----------|------|----------|
| Python | 3.10 이상 | https://www.python.org/downloads/ |
| PostgreSQL | 15 이상 | https://www.postgresql.org/download/windows/ |
| Git | 최신 | https://git-scm.com/download/win |
| 웹캠 | - | 내장 또는 USB 카메라 |

### Python 설치 시 주의사항

- 설치 화면에서 **"Add Python to PATH"** 체크 필수
- 설치 완료 후 터미널에서 확인:

```powershell
python --version
pip --version
```

---

## 2. 프로젝트 설치

### 2-1. 소스 코드 가져오기

```powershell
git clone <저장소 URL> D:\I-Study
cd D:\I-Study
```

또는 프로젝트 폴더를 직접 복사합니다.

### 2-2. 가상환경 생성 (권장)

시스템 Python과 패키지 충돌을 방지하기 위해 가상환경을 사용합니다.

```powershell
cd D:\I-Study
python -m venv venv
venv\Scripts\Activate.ps1
```

> 이후 모든 `pip install`과 `python` 명령은 가상환경이 활성화된 상태에서 실행합니다.  
> 터미널 프롬프트 앞에 `(venv)`가 표시되면 활성화된 상태입니다.  
> PowerShell 실행 정책 오류 시: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`  
> VS Code 사용 시 인터프리터를 `D:\I-Study\venv\Scripts\python.exe`로 설정하세요.

### 2-3. 데스크톱 앱 패키지 설치

```powershell
cd D:\I-Study
pip install -r requirements.txt
```

설치되는 주요 패키지:
- `mediapipe` — AI 머리 방향 추적
- `opencv-python` — 카메라 제어
- `customtkinter` — GUI 프레임워크
- `requests` — 서버 API 통신
- `matplotlib` — 통계 그래프

### 2-4. 서버 패키지 설치

```powershell
cd D:\I-Study\server
pip install -r requirements.txt
```

설치되는 패키지:
- `fastapi` — 웹 프레임워크
- `uvicorn` — ASGI 서버
- `sqlalchemy` — ORM
- `psycopg2-binary` — PostgreSQL 드라이버

### 2-5. MediaPipe AI 모델 (자동 다운로드)

머리 방향 추적에 필요한 `face_landmarker.task` 모델 파일은 **앱 첫 실행 시 자동 다운로드**됩니다.

- 다운로드 경로: `models/face_landmarker.task` (약 10MB)
- 다운로드 URL: `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`
- **첫 실행 시 인터넷 연결이 반드시 필요합니다**
- 이후에는 오프라인에서도 동작합니다

> 인터넷이 안 되는 환경이라면, 다른 PC에서 위 URL의 파일을 다운로드하여 `models/` 폴더에 직접 복사하세요.

### 2-6. matplotlib 한글 폰트 설정

통계 그래프에서 한글이 깨지지 않도록 `config/settings.py`에 폰트 설정이 포함되어 있습니다.
Windows의 경우 `맑은 고딕(Malgun Gothic)` 폰트를 자동으로 사용합니다.

만약 한글이 깨진다면:

```python
# config/settings.py 에서 확인
import matplotlib
matplotlib.rcParams['font.family'] = 'Malgun Gothic'
matplotlib.rcParams['axes.unicode_minus'] = False
```

---

## 3. PostgreSQL 설치 및 DB 생성

### 3-1. PostgreSQL 설치

1. https://www.postgresql.org/download/windows/ 에서 설치 파일 다운로드
2. 설치 진행 시 설정:
   - **포트**: `5432` (기본값)
   - **슈퍼유저 비밀번호**: `aisw2026`
   - **로케일**: Korean, Korea 또는 기본값
3. 설치 완료 후 서비스가 자동 시작됩니다.

### 3-2. PostgreSQL 실행 확인

```powershell
& "C:\Program Files\PostgreSQL\<버전>\bin\pg_isready" -h localhost -p 5432
```

정상 출력:
```
localhost:5432 - 접속을 받아드리는 중
```

> `<버전>`은 설치된 PostgreSQL 버전 번호(예: 15, 16, 17, 18)로 바꾸세요.

### 3-3. 데이터베이스 생성 (자동)

앱과 서버 모두 `_ensure_database_exists()` 함수가 내장되어 있어,  
**`istudy` 데이터베이스가 없으면 자동으로 생성됩니다.**

수동 생성이 필요한 경우:

```powershell
$env:PGPASSWORD='aisw2026'
& "C:\Program Files\PostgreSQL\<버전>\bin\psql" -h localhost -U postgres -c "CREATE DATABASE istudy;"
```

### 3-4. DB 접속 정보 확인

`server/database.py` 파일의 접속 정보가 환경과 일치하는지 확인합니다:

```python
DATABASE_URL = "postgresql://postgres:aisw2026@localhost:5432/istudy"
```

| 항목 | 기본값 | 설명 |
|------|--------|------|
| 사용자 | `postgres` | PostgreSQL 슈퍼유저 |
| 비밀번호 | `aisw2026` | 설치 시 설정한 비밀번호 |
| 호스트 | `localhost` | 로컬 실행 |
| 포트 | `5432` | PostgreSQL 기본 포트 |
| DB 이름 | `istudy` | 위에서 생성한 DB |

> 비밀번호나 포트가 다른 경우 `server/database.py`의 `DATABASE_URL`을 수정하세요.

---

## 4. FastAPI 서버 (자동 시작)

### 4-1. 서버 자동 시작 (기본)

`main.py`를 실행하면 **FastAPI 서버가 자동으로 백그라운드 프로세스로 시작**됩니다.  
앱 종료 시 서버도 자동 종료됩니다.

### 4-2. 서버 수동 시작 (개발/테스트용)

서버만 단독 실행하고 싶을 때:

```powershell
cd D:\I-Study\server
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

정상 출력:
```
DB 테이블 생성 완료
기본 화이트리스트 7건 등록
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

서버가 처음 시작되면 자동으로:
- `istudy` 데이터베이스 생성 (없는 경우)
- `headpose_data`, `whitelist_urls` 테이블 생성
- 기본 7개 화이트리스트 사이트 등록

### 4-3. 서버 동작 확인

브라우저에서 접속:
- **Swagger UI (API 문서)**: http://localhost:8000/docs
- **화이트리스트 조회**: http://localhost:8000/whitelist
- **루트**: http://localhost:8000/ → 자동으로 `/docs`로 리다이렉트

### 4-4. 서버 종료

- 수동 실행 시: 터미널에서 `Ctrl+C`
- 앱 자동 시작 시: 앱 종료와 함께 자동 종료

---

## 5. 데스크톱 앱 실행

### 5-1. 앱 시작

```powershell
cd D:\I-Study
python main.py
```

`main.py`가 자동으로:
1. FastAPI 서버 백그라운드 시작 (포트 8000)
2. 서버 준비 대기 (최대 10초)
3. UI 앱 (FocusEyePro) 실행
4. 앱 종료 시 서버 자동 종료

### 5-2. 실행 순서 요약

```
[터미널 1개만 필요] python main.py (프로젝트 루트)
  └─ 서버 자동 시작 → UI 앱 실행 → 앱 종료 시 서버 자동 종료
```

---

## 6. 정상 동작 확인

### 6-1. 서버 API 테스트

PowerShell에서:

```powershell
# 화이트리스트 조회
Invoke-RestMethod -Uri "http://localhost:8000/whitelist" -Method GET

# 시선 데이터 전송 테스트
Invoke-RestMethod -Uri "http://localhost:8000/headpose" -Method POST `
  -ContentType "application/json" `
  -Body '{"student_id": "test01", "x": 0.5, "y": 0.5}'
```

### 6-2. DB 직접 확인

```powershell
$env:PAGER='more'
$env:PGPASSWORD='aisw2026'
& "C:\Program Files\PostgreSQL\<버전>\bin\psql" -h localhost -U postgres -d istudy -c "SELECT * FROM whitelist_urls;"
```

### 6-3. 앱 기능 확인

1. 앱 실행 후 **화이트리스트** 탭에서 기본 7개 사이트가 표시되는지 확인
2. 새 URL 추가/삭제 후 서버 DB에 반영되는지 확인
3. **집중 모드 ON** → 카메라 작동, 머리 방향 추적 시작 확인

---

## 7. 서버 주소 변경 (원격 접속)

기본 설정은 서버와 앱이 **같은 PC**에서 실행되는 것을 전제합니다.  
서버를 다른 PC에서 실행하는 경우 아래를 수정합니다.

### 7-1. 앱 → 서버 접속 주소 변경

`utils/api_client.py`의 `API_BASE`를 서버 PC의 IP로 변경:

```python
# 변경 전 (같은 PC)
API_BASE = "http://localhost:8000"

# 변경 후 (서버가 192.168.0.10에 있는 경우)
API_BASE = "http://192.168.0.10:8000"
```

### 7-2. 서버 PC의 방화벽 설정

서버 PC에서 8000번 포트를 열어야 다른 PC에서 접속 가능합니다:

```powershell
# 관리자 권한 PowerShell에서 실행
New-NetFirewallRule -DisplayName "I-Study Server" -Direction Inbound -Port 8000 -Protocol TCP -Action Allow
```

### 7-3. PostgreSQL 원격 접속 허용 (필요 시)

PostgreSQL을 별도 서버에서 운영하는 경우:

1. `postgresql.conf`에서 `listen_addresses = '*'` 설정
2. `pg_hba.conf`에서 접속 IP 대역 허용 추가
3. 방화벽에서 5432 포트 개방
4. `server/database.py`의 `DATABASE_URL` 호스트를 해당 IP로 변경

---

## 8. 로그 파일 관리

앱 실행 시 `logs/` 폴더에 자동으로 로그 파일이 생성됩니다.

| 파일 | 내용 | 관련 모듈 |
|------|------|-----------|
| `logs/headpose.log` | 머리 방향 추적 이벤트, 방향 변화, 이탈/복귀 | `core/head_pose_tracker.py` |
| `logs/monitor.log` | URL 모니터링, 사이트 차단 이벤트 | `core/monitor.py` |
| `logs/app.log` | 앱 전반 이벤트, 세션 시작/종료 | `ui/app.py` |

- 로그는 **RotatingFileHandler**로 관리되어 파일 크기가 커지면 자동 교체됩니다
- 로그 설정은 `utils/logger_config.py`에서 변경 가능
- 문제 발생 시 해당 로그 파일을 확인하면 원인을 파악할 수 있습니다

---

## 9. 문제 해결

### PostgreSQL 연결 실패

```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError)
```

**원인 및 해결**:
- PostgreSQL 서비스가 실행 중인지 확인
- 비밀번호가 `aisw2026`과 일치하는지 확인
- `istudy` 데이터베이스가 생성되었는지 확인
- 포트가 5432인지 확인

### 모듈을 찾을 수 없음

```
ModuleNotFoundError: No module named 'customtkinter'
```

**해결**: 데스크톱 앱 패키지 재설치

```powershell
cd D:\I-Study
pip install -r requirements.txt
```

### 화이트리스트가 비어 있음

**원인**: PostgreSQL 서비스가 실행 중이 아님  
**해결**: PostgreSQL 서비스 실행 확인 후 앱 재시작  
> 서버 다운 시에도 `api_client.py`가 로컬 PostgreSQL에 직접 접속하여 폴백 동작합니다.

### 카메라 오류

**원인**: 웹캠이 연결되지 않았거나 다른 프로그램이 사용 중  
**해결**: 다른 카메라 사용 프로그램 종료 후 재시도

### PowerShell 스크립트 실행 오류

```
.venv\Scripts\Activate.ps1 : 이 시스템에서 스크립트를 실행할 수 없습니다.
```

**해결**:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### MediaPipe 모델 다운로드 실패

**원인**: 인터넷 연결 불가 또는 방화벽 차단  
**해결**: 다른 PC에서 모델 파일을 수동 다운로드하여 `models/face_landmarker.task`에 복사

### matplotlib 한글 깨짐

**해결**: `config/settings.py`에서 폰트 설정 확인 → `Malgun Gothic`이 설치되어 있는지 확인

### 서버는 실행 중인데 앱에서 화이트리스트가 안 보임

**원인**: 서버 주소 불일치  
**해결**: `utils/api_client.py`의 `API_BASE`가 서버 주소와 일치하는지 확인

---

## 참고: 프로젝트 구조

```
I-Study/
├── main.py                  # 데스크톱 앱 진입점
├── requirements.txt         # 데스크톱 앱 패키지
├── config/settings.py       # 앱 설정
├── core/                    # 비즈니스 로직 (머리방향 추적, 모니터링, DB)
├── ui/                      # GUI (홈, 화이트리스트, 통계, 다이얼로그)
├── utils/                   # 유틸리티 (로거, 헬퍼, API 클라이언트)
├── server/                  # FastAPI 서버
│   ├── main.py              # 서버 진입점
│   ├── database.py          # PostgreSQL 연결 설정
│   ├── models.py            # DB 테이블 모델
│   └── requirements.txt     # 서버 패키지
├── utils/                   # 유틸리티
│   ├── api_client.py        # FastAPI 서버 HTTP 클라이언트
│   ├── logger_config.py     # 로깅 설정
│   └── helpers.py           # 브라우저 제어 유틸
├── models/                  # AI 모델 (자동 다운로드)
│   └── face_landmarker.task # MediaPipe 얼굴 랜드마크
├── logs/                    # 로그 파일 (자동 생성)
│   ├── headpose.log             # 머리 방향 추적 로그
│   ├── monitor.log          # 모니터링 로그
│   └── app.log              # 앱 로그
├── venv/                    # Python 가상환경
└── docs/                    # 문서
```

---

## 빠른 시작 체크리스트

새 PC에서 아래 순서대로 따라하면 됩니다:

- [ ] Python 3.10+ 설치 (PATH 추가 체크)
- [ ] PostgreSQL 설치 (비밀번호: `aisw2026`)
- [ ] 프로젝트 소스 복사 또는 git clone
- [ ] `pip install -r requirements.txt` (프로젝트 루트)
- [ ] `pip install -r requirements.txt` (server/ 폴더)
- [ ] PostgreSQL 서비스 실행 확인 (DB는 자동 생성됨)
- [ ] `python main.py` (서버 자동 시작 + 앱 실행)
- [ ] 앱에서 화이트리스트 7개 표시 확인
- [ ] 집중 모드 ON → 카메라 작동 확인
- [ ] Swagger UI 접속 확인: http://localhost:8000/docs

---

**문서 버전**: 3.0  
**최종 수정일**: 2026-04-10  
**작성자**: I-Study Development Team
