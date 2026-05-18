# I-Study — AI 시선 추적 학습 집중도 관리 시스템

> Windows 데스크톱 앱 + 웹 대시보드 통합 플랫폼

---

## 바로 사용하기

### 방법 1 — 웹 브라우저 접속 (설치 불필요)

```
https://haniumproject.onrender.com
```

1. 위 주소를 브라우저에 입력
2. **회원가입** 클릭 → 이름, ID, 비밀번호, 역할 선택 후 가입
3. 관리자 승인 후 로그인 → 사용 시작

> 첫 접속은 서버 시작으로 인해 약 30초 소요될 수 있습니다.

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

서버 URL 뒤에 `/docs` 를 입력해 API 문서 접속:
```
https://haniumproject.onrender.com/docs
```
`POST /admins/signup` 항목을 열고 아래 내용으로 실행:
```json
{
  "admin_id": "admin",
  "password": "비밀번호입력",
  "name": "관리자",
  "level": 9
}
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
# 서버 URL 입력 (배포 URL 또는 엔터로 로컬 모드)
# → dist/I-Study/I-Study.exe 생성
```

### 서버 배포 (Render + Neon)

1. [neon.tech](https://neon.tech) — PostgreSQL 무료 생성 → 연결 문자열 복사
2. [render.com](https://render.com) — Web Service 생성
   - Root Directory: `backend_db`
   - Build Command: `pip install -r ../requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - 환경변수: `DATABASE_URL`, `JWT_SECRET`
3. 배포 URL을 GitHub Secret `ISTUDY_SERVER_URL` 에 등록
4. `git tag v1.0 && git push origin v1.0` → EXE 자동 빌드 + GitHub Release

</details>

---

**I-Study Team** · 2026
