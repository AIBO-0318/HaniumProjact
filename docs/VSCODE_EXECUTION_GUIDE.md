# I-Study VSCode 실행 가이드

## 📖 실행 방법

### 1️⃣ 테스트 모델 실행

**터미널에서:**
```powershell
cd d:\I-Study\tests
python test_head_pose.py
```

**설명:**
- 고개 방향 인식률 테스트 도구
- 메인 앱과 동일한 알고리즘 사용
- 캘리브레이션 후 방향별 인식률 측정 가능

---

### 2️⃣ 메인 앱 실행 (서버 자동 시작)

**터미널에서:**
```powershell
cd d:\I-Study
python run_desktop.py
```

**설명:**
- 데스크톱 앱이 시작됨
- 백그라운드에서 FastAPI 서버 자동 실행 (포트 8000)
- 웹사이트 접속: http://127.0.0.1:8000
- 데스크톱 앱 + 웹사이트 동시 사용 가능

---

### 3️⃣ 서버만 따로 실행

**터미널에서:**
```powershell
cd d:\I-Study
python run_backend.py
```

**설명:**
- 웹사이트만 실행됨
- 데스크톱 앱 없음
- 웹 기능만 테스트할 때 사용

---

## 🔧 VSCode 디버깅 설정 (launch.json)

### 파일 위치
```
d:\I-Study\.vscode\launch.json
```

### 설정 내용
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "메인 앱 (서버 자동)",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/run_desktop.py",
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal"
        },
        {
            "name": "서버만",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/run_backend.py",
            "cwd": "${workspaceFolder}",
            "console": "integratedTerminal"
        },
        {
            "name": "테스트 모델",
            "type": "debugpy",
            "request": "launch",
            "program": "${workspaceFolder}/tests/test_head_pose.py",
            "cwd": "${workspaceFolder}/tests",
            "console": "integratedTerminal"
        }
    ]
}
```

### 사용 방법
1. `F5` 키 또는 상단 메뉴 `Run > Start Debugging`
2. 디버그 구성 선택
3. 자동으로 해당 실행 모드로 시작

---

## 🚀 빠른 시작 (터미널)

VSCode 터미널 (`Ctrl+`~``)에서 바로 실행:

### 메인 앱 실행 (데스크톱 + 서버 자동)
```powershell
cd d:\I-Study
python run_desktop.py
```

### 서버만 실행
```powershell
cd d:\I-Study
python run_backend.py
```

### 테스트 모델 실행
```powershell
cd d:\I-Study\tests
python test_head_pose.py
```

---

## 📊 실행 모드 비교

| 모드 | 데스크톱 앱 | 서버 | 웹사이트 | 용도 |
|------|------------|------|----------|------|
| **메인 앱** | ✅ | ✅ (자동) | ✅ | 전체 기능 테스트 |
| **서버만** | ❌ | ✅ | ✅ | 웹 기능만 테스트 |
| **테스트 모델** | ❌ | ❌ | ❌ | 인식률 측정 |

---

## ⚠️ 주의사항

### 포트 충돌 방지
- 서버는 포트 8000 사용
- 이미 실행 중인 프로세스가 있으면 먼저 종료:
  ```powershell
  Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
  ```

### 모델 다운로드
- 처음 실행 시 MediaPipe 모델 자동 다운로드 (약 50MB)
- 인터넷 연결 필요
- 다운로드 완료 후 다시 실행

### 카메라 권한
- 테스트 모델/메인 앱 실행 시 카메라 권한 허용 필요
- Windows: 설정 → 개인정보 → 카메라

---

## 🔗 관련 링크

- **웹사이트**: http://127.0.0.1:8000
- **API 문서**: http://127.0.0.1:8000/docs
- **테스트 계정**:
  - 학생: `alice` / `pass1234`
  - 선생님: `teacher1` / `pass1234`

---

## 📝 추가 정보

### 테스트 모델 사용법
- 정면 응시 후 `C`키 10번 (캘리브레이션)
- `1~5`키로 방향별 테스트 (5초)
- `R`키로 결과 리포트
- `Q/ESC`로 종료

### 메인 앱 기능
- 얼굴 감지 및 시선 추적
- 화이트리스트 모니터링
- 학습 타이머
- 웹사이트 연동

### 웹사이트 기능
- 회원가입/로그인
- 학습 통계
- 시선 보정
- 화이트리스트 관리
- 일정표
