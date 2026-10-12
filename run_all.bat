@echo off
chcp 65001 >nul
title I-Study 서버 런처

echo ===========================================================
echo  I-Study 서버 2개 동시 실행
echo    1) Spring Boot (REST + 웹)   http://127.0.0.1:8000
echo    2) FastAPI AI (시선추적 WS)  http://127.0.0.1:8001
echo  - 각 서버는 별도 창에서 열립니다.
echo  - 종료: 각 창에서 Ctrl + C
echo ===========================================================
echo.

rem 비밀번호·JWT 키는 .env 에서만 읽는다 (README 2단계)
if not exist "%~dp0.env" (
    echo [오류] .env 파일이 없습니다.
    echo        .env.example 을 복사해 .env 를 만들고 DB_PASSWORD, JWT_SECRET 을 채우세요.
    pause
    exit /b 1
)

rem 가상환경이 있으면 그 Python 을 사용
set "PY=python"
if exist "%~dp0venv\Scripts\python.exe" set "PY=%~dp0venv\Scripts\python.exe"

rem 1) Spring Boot (8000) — backend_spring\run.bat (JAVA_HOME 설정 + gradlew bootRun)
cd /d "%~dp0backend_spring"
start "I-Study  Spring Boot (8000)" cmd /k call run.bat

rem 2) FastAPI AI (8001) — uvicorn ai_server:app
cd /d "%~dp0"
start "I-Study  FastAPI AI (8001)" cmd /k ""%PY%" run_ai_server.py"

echo 두 서버 창을 띄웠습니다. 이 창은 닫아도 됩니다.
timeout /t 6 >nul
