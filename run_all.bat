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

rem 1) Spring Boot (8000) — backend_spring\run.bat (JAVA_HOME 설정 + gradlew bootRun)
cd /d "%~dp0backend_spring"
start "I-Study  Spring Boot (8000)" cmd /k call run.bat

rem 2) FastAPI AI (8001) — uvicorn ai_server:app
cd /d "%~dp0"
start "I-Study  FastAPI AI (8001)" cmd /k python run_ai_server.py

echo 두 서버 창을 띄웠습니다. 이 창은 닫아도 됩니다.
timeout /t 6 >nul
