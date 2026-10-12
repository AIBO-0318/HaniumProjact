# I-Study — AI 시선 추적 학습 집중도 관리 시스템

> Windows 데스크톱 앱(집중 모드) + 웹 대시보드(통계·일정·화이트리스트) 통합 플랫폼

서버 PC 한 대에서 아래 세 가지를 실행하고, 같은 공유기(Wi-Fi/LAN)의 다른 기기는 브라우저나 데스크톱 앱으로 접속합니다.

| 구성 | 포트 | 역할 |
|------|------|------|
| Spring Boot (`backend_spring`) | 8000 | REST API + 웹 화면 |
| FastAPI AI (`backend_db/ai_server.py`) | 8001 | 웹캠 시선 추적 WebSocket (`/ws/gaze`) |
| PostgreSQL | 5432 | DB (`istudy`) |

---

## 처음 실행하기 (서버 PC, Windows 10/11)

아래 순서대로 따라 하면 됩니다. 명령은 모두 **PowerShell** 에서 프로젝트 폴더 기준으로 실행합니다.

### 0. 설치할 것

| 프로그램 | 버전 | 비고 |
|----------|------|------|
| [Python](https://www.python.org/downloads/) | 3.10 권장 | 설치 시 **Add python.exe to PATH** 체크 |
| [JDK](https://adoptium.net/temurin/releases/?version=17) | **17** | 다른 버전(21 등)으로는 빌드되지 않음. 설치 시 **Set JAVA_HOME** 체크 |
| [PostgreSQL](https://www.postgresql.org/download/windows/) | 14 이상 | 설치 중 정한 `postgres` 비밀번호를 기억해 두기 (2단계에서 사용) |
| [Git](https://git-scm.com/download/win) | — | |
| 웹캠 | — | 집중 모드에 필요 (없으면 집중 모드만 시작되지 않고 나머지는 사용 가능) |

### 1. 소스 받기 · 패키지 설치

```powershell
git clone https://github.com/AIBO-0318/HaniumProjact.git
cd HaniumProjact
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

패키지 설치는 인터넷 속도에 따라 몇 분 걸립니다.

### 2. 설정 파일 `.env` 만들기

DB 비밀번호와 JWT 서명 키는 **코드에 넣지 않고 `.env` 파일에만** 적습니다.
`.env` 는 `.gitignore` 에 들어 있어 GitHub 에 올라가지 않습니다.

```powershell
Copy-Item .env.example .env
venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"   # JWT 키 생성 → 출력값 복사
notepad .env
```

메모장에서 비어 있는 두 줄을 채우고 저장합니다 (따옴표 없이).

```
DB_PASSWORD=<PostgreSQL 설치 때 정한 비밀번호>
JWT_SECRET=<위에서 생성한 문자열>
```

> Spring Boot 와 FastAPI 가 이 `.env` 하나를 함께 읽습니다. `.env` 가 없거나 값이 비어 있으면
> 서버가 시작되지 않고 원인을 알려 줍니다 (아래 [문제 해결](#문제-해결) 참고).

### 3. DB 만들기 (최초 1회)

```powershell
venv\Scripts\python.exe init_db.py
```

`istudy` DB 와 테이블 7개를 만듭니다. 이미 있으면 건드리지 않으므로 다시 실행해도 안전합니다.

### 4. 서버 실행

```powershell
.\run_all.bat
```

창이 두 개 열립니다 — **Spring Boot (8000)**, **FastAPI AI (8001)**.
처음에는 Gradle 을 내려받느라 Spring Boot 가 뜨는 데 1~3분 걸립니다 (인터넷 필요).
`Started IStudyApplication` 이 보이면 준비 완료입니다.

| 확인 주소 | 정상 결과 |
|-----------|-----------|
| http://127.0.0.1:8000 | 로그인 화면 |
| http://127.0.0.1:8001/health | `{"status":"ok","service":"ai",...}` |

종료는 각 창에서 `Ctrl + C`.

### 5. 첫 관리자 계정 만들기 (최초 1회)

관리자가 **한 명도 없을 때만** 로그인 없이 만들 수 있습니다. 서버가 켜진 상태에서:

`password` 값을 원하는 비밀번호(8자 이상)로 바꿔서 실행하세요. 웹 로그인 화면의 **관리자** 탭에서 이 아이디·비밀번호로 로그인합니다.

```powershell
$body = '{"admin_id":"admin","password":"여기에비밀번호입력","name":"관리자","level":9}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/admins/signup" -Method POST `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

그 뒤로는 이 방법이 막히고(401), 관리자로 웹에 로그인한 상태에서 **회원가입 화면의 관리자 탭**으로만 추가할 수 있습니다
(자신보다 높은 등급은 만들 수 없음).

**모든 학생 공통 허용 사이트(기본 화이트리스트) 추가** — 웹 화면이 없어 관리자 토큰으로 API 를 호출합니다 (선택).
학생별 허용 사이트는 웹의 **화이트리스트 관리** 화면에서 추가합니다.

```powershell
$login = '{"admin_id":"admin","password":"여기에비밀번호입력"}'
$token = (Invoke-RestMethod -Uri "http://127.0.0.1:8000/admins/login" -Method POST -ContentType "application/json" -Body $login).access_token
$site  = '{"name":"EBS","url":"https://www.ebs.co.kr/"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/whitelist/admin/default" -Method POST `
  -Headers @{ Authorization = "Bearer $token" } `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($site))
```

### 6. 웹에서 가입·로그인

1. http://127.0.0.1:8000 → **회원가입**
2. 학생으로 먼저 가입합니다. 학습지도자는 가입할 때 담당 학생의 아이디를 입력하므로 학생이 먼저 있어야 합니다.
3. 가입하면 바로 로그인할 수 있습니다. 관리자가 **사용자 관리**에서 비활성화하면 로그인이 막힙니다.

### 7. 데스크톱 앱 실행 (집중 모드)

```powershell
venv\Scripts\python.exe run_desktop.py
```

학생 계정으로 로그인 → 왼쪽의 **⚡ 집중 모드** 버튼을 누르면 시작합니다.
처음 실행할 때 시선 추적 모델(약 4MB)을 자동으로 내려받습니다. 캘리브레이션은 웹캠 앞에 얼굴이 보여야 진행됩니다.

> 웹캠이 없거나 다른 프로그램이 쓰고 있으면 *"집중 모드를 시작할 수 없습니다 — 웹캠을 열 수 없습니다"* 안내가 뜨고
> 집중 모드는 시작되지 않습니다. 정상 동작이며, 웹캠을 연결한 뒤 다시 누르면 됩니다.

---

## 기능과 계정

| 역할 | 가입 | 웹에서 할 수 있는 일 | 데스크톱 앱 |
|------|------|----------------------|-------------|
| **학생** | 회원가입 화면 | 일정표, 학습 통계, 내 화이트리스트 확인, 마이페이지 | 집중 모드 (시선 추적·딴짓 사이트 차단) |
| **학습지도자** | 회원가입 화면 (담당 학생 아이디 필요) | 학생 일정 조회, 학생 화이트리스트 관리 | — |
| **관리자** | 5단계 참고 | 사용자 관리(승인·비활성화), 전체 학생 통계·일정 조회, 학생별 화이트리스트 관리, 관리자 추가 | — |

학습 통계와 화이트리스트는 **웹에서만** 보고 관리합니다. 데스크톱 앱은 집중 모드 전용입니다.

---

## 다른 PC에서 접속 (같은 LAN)

1. 서버 PC의 IP 확인: `ipconfig` → IPv4 주소 (예: `192.168.0.10`)
2. 서버 PC 방화벽 인바운드 허용 (최초 1회, **관리자 권한** PowerShell)
   ```powershell
   New-NetFirewallRule -DisplayName "I-Study 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
   New-NetFirewallRule -DisplayName "I-Study 8001" -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow
   ```
3. 웹: 다른 기기 브라우저에서 `http://<서버PC IP>:8000`
4. 데스크톱 앱(EXE): 서버 PC에서 서버 주소를 넣어 빌드한 뒤 `dist\I-Study` 폴더를 통째로 복사해 `I-Study.exe` 실행
   ```powershell
   venv\Scripts\python.exe build_exe.py --server-url http://<서버PC IP>:8000
   ```
   서버 주소는 EXE 옆 `_server_url.txt` 에 한 줄로 들어갑니다. 서버 IP가 바뀌면 이 파일만 고치면 됩니다.

---

## 설정과 보안

- **비밀 값은 `.env` 에만** 둡니다. 코드·설정 파일(`application.yml`, `shared/env_config.py`)에는 기본값이 없습니다.
  - Spring Boot: `application.yml` 의 `spring.config.import` 가 루트의 `.env` 를 불러옵니다.
  - FastAPI·데스크톱: `shared/env_config.py` 가 `.env` 를 읽습니다.
  - OS 환경변수로 같은 이름을 지정하면 `.env` 보다 우선합니다.
- git 에 올리지 않는 파일: `.env`, `_server_url.txt`, `tests/e2e/e2e_accounts.json`, `tests/e2e/results/`
- GitHub Actions 릴리스 빌드(`v*` 태그)는 서버 주소를 저장소 Secret `ISTUDY_SERVER_URL` 에서 받습니다.

| `.env` 키 | 설명 |
|-----------|------|
| `DB_HOST` `DB_PORT` `DB_USER` `DB_NAME` | PostgreSQL 접속 정보 (기본 `localhost` `5432` `postgres` `istudy`) |
| `DB_PASSWORD` | PostgreSQL 비밀번호 — **필수** |
| `JWT_SECRET` | 로그인 토큰 서명 키, 32자 이상 — **필수** |
| `SERVER_HOST` | `0.0.0.0` = LAN 접속 허용, `127.0.0.1` = 이 PC만 |
| `API_SERVER_URL` | `run_desktop.py` 로 실행한 앱이 접속할 서버 주소 |

---

## 문제 해결

| 증상 | 원인 · 해결 |
|------|-------------|
| `.env 파일이 없습니다` (run_all.bat) | 2단계를 하지 않음 → `.env.example` 을 `.env` 로 복사 |
| `Could not resolve placeholder 'JWT_SECRET'` / `'DB_PASSWORD'` (Spring 창) | `.env` 위치가 프로젝트 루트가 아니거나 키 이름이 틀림 |
| `JWT_SECRET 이 없거나 32바이트보다 짧습니다` (AI 창) | `JWT_SECRET` 을 32자 이상으로 채우기 |
| `password authentication failed for user "postgres"` | `.env` 의 `DB_PASSWORD` 가 PostgreSQL 비밀번호와 다름 |
| `Connection refused` … `5432` | PostgreSQL 서비스가 꺼져 있음 → `services.msc` 에서 `postgresql-x64-<버전>` 시작 |
| Spring 창에 `JAVA_HOME` / toolchain 17 오류 | JDK 17 설치 후 `JAVA_HOME` 을 JDK 17 폴더로 설정하고 창을 새로 열기 |
| `Port 8000 was already in use` | 이미 서버가 켜져 있음 → `netstat -ano \| findstr :8000` 로 PID 확인 후 종료 |
| 집중 모드: *웹캠을 열 수 없습니다* | 웹캠 연결 확인, Zoom 등 웹캠 사용 중인 프로그램 종료, Windows 설정 > 개인 정보 > 카메라 권한 확인 |
| 다른 PC에서 접속 안 됨 | 같은 네트워크인지, 방화벽 규칙(8000·8001)을 추가했는지 확인 |

---

## 개발자 참고

<details>
<summary>폴더 구조 · 테스트</summary>

```
ai_core/          시선 추적 엔진 (MediaPipe Face Landmarker), 사이트 감시
backend_spring/   Spring Boot 백엔드 (REST + 웹), schema.sql
backend_db/       FastAPI AI 서버 (/ws/gaze)
ui_ux/desktop/    데스크톱 앱 (customtkinter)
ui_ux/web/        웹 화면 (HTML/JS)
shared/           공통 설정·API 클라이언트 (.env 로더 포함)
tests/e2e/        서버·DB·AI·데스크톱 E2E 테스트
```

**E2E 테스트** (서버 두 개가 켜진 상태에서)

```powershell
venv\Scripts\python.exe tests\e2e\api_e2e.py          # API·DB·권한·WebSocket 87건
venv\Scripts\python.exe tests\e2e\cleanup.py --apply  # 테스트 계정·데이터 삭제
```

테스트는 `qa_e2e_` 로 시작하는 계정만 만들고 지웁니다.

</details>

---

**I-Study Team** · 2026
