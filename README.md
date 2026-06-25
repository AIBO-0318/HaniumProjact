# I-Study — AI 시선 추적 학습 집중도 관리 시스템

> Windows 데스크톱 앱 + 웹 대시보드 통합 플랫폼

---

## 바로 사용하기

> 이 프로젝트는 **로컬/LAN 서버 모드**로 동작합니다. 서버 PC 한 대에서
> Spring Boot(REST+웹, 8000) + FastAPI AI(시선추적, 8001) + PostgreSQL 을 실행하고,
> 같은 공유기(Wi-Fi/LAN)의 다른 기기에서 접속합니다.

### 방법 1 — 웹 브라우저 접속 (설치 불필요)

서버 PC에서:
```
http://127.0.0.1:8000
```
LAN 내 다른 기기(같은 Wi-Fi)에서:
```
http://<서버PC의_사설IP>:8000     예) http://172.31.57.34:8000
```

1. 위 주소를 브라우저에 입력 (서버 PC의 IP는 `ipconfig` 의 IPv4 주소)
2. **회원가입** 클릭 → 이름, ID, 비밀번호, 역할 선택 후 가입
3. 관리자 승인 후 로그인 → 사용 시작

> LAN 접속이 안 되면 서버 PC의 **방화벽 인바운드 8000포트**를 허용했는지 확인하세요(아래 참고).

---

### 방법 2 — 데스크톱 앱 (EXE)

1. [GitHub Releases](https://github.com/AIBO-0318/HaniumProjact/releases) 에서 `I-Study-Windows.zip` 다운로드
2. 압축 해제
3. `I-Study.exe` 실행
4. 방법 1에서 만든 계정으로 로그인

> **필요 사항**: Windows 10/11 64-bit, 웹캠

---

## 계정 종류

| 역할 | 가입 방법 | 주요 기능 |
|------|-----------|-----------|
| **학생** | 회원가입 페이지 | 집중 모드, 학습 통계, 일정 |
| **학습지도자** | 회원가입 페이지 | 학생 일정·화이트리스트 관리 |
| **관리자** | 아래 참고 | 사용자 승인·관리 |

### 관리자 계정 생성

서버 PC에서 PowerShell 로 `POST /admins/signup` 호출:
```powershell
$body = '{"admin_id":"admin","password":"비밀번호입력","name":"관리자","level":9}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/admins/signup" -Method POST `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

---

## 주요 기능

| 기능 | 설명 | 대상 |
|------|------|------|
| **집중 모드** | 시선 추적으로 집중도 실시간 측정 | 학생 (앱) |
| **학습 통계** | 일별/주별 집중 시간 그래프 | 학생 |
| **학습 일정** | 과목별 일정 등록·완료 체크 | 학생 |
| **화이트리스트** | 허용 사이트 목록 조회 | 학생 |
| **화이트리스트 관리** | 학생별 허용 사이트 추가/삭제 | 지도자 |
| **사용자 승인** | 신규 가입자 승인/비활성화 | 관리자 |
| **전체 통계** | 모든 학생 학습 현황 조회 | 관리자 |

---

## 개발자 — 로컬 실행

<details>
<summary>펼치기</summary>

### 사전 요구사항
- Python 3.10+
- PostgreSQL 14+
- 웹캠

### 설치 및 실행

```bash
# 1. 클론
git clone https://github.com/AIBO-0318/HaniumProjact.git
cd HaniumProjact

# 2. 가상환경
python -m venv venv
venv\Scripts\activate

# 3. 패키지 설치
pip install -r requirements.txt

# 4. 환경변수 설정
copy .env.example .env
# .env 파일에서 DB_PASSWORD 수정

# 5-A. 데스크톱 앱 + 웹 서버 동시 실행
python run_desktop.py

# 5-B. 웹 서버만 실행
python run_backend.py
# → http://localhost:8000 접속
```

### EXE 빌드

```bash
python build_exe.py
# 서버 URL 입력: 엔터만 누르면 이 PC의 LAN 주소(http://<사설IP>:8000)로 빌드
# → dist/I-Study/I-Study.exe 생성 (EXE 옆 _server_url.txt 에 서버 URL 번들링)
```

### LAN 서버 실행 (서버 PC 한 대)

1. **Spring Boot (REST + 웹, 8000)**
   ```powershell
   cd backend_spring
   .\run.bat            # JAVA_HOME 자동 설정 + gradlew bootRun
   ```
2. **FastAPI AI (시선추적 WS, 8001)**
   ```powershell
   python run_ai_server.py
   ```
3. **방화벽 인바운드 허용** (최초 1회, 관리자 PowerShell)
   ```powershell
   New-NetFirewallRule -DisplayName "I-Study 8000" -Direction Inbound `
     -Protocol TCP -LocalPort 8000 -Action Allow
   New-NetFirewallRule -DisplayName "I-Study 8001" -Direction Inbound `
     -Protocol TCP -LocalPort 8001 -Action Allow
   ```
4. 클라이언트는 `.env` 의 `API_SERVER_URL=http://<서버PC IP>:8000` 으로 접속.
   (서버 PC IP가 DHCP로 바뀌면 값을 갱신; 고정 IP 권장)

</details>

---

**I-Study Team** · 2026
