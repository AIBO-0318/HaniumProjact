@echo off
title I-Study Local Server (Demo)
cd /d D:\I-Study\backend_db
echo ============================================
echo  I-Study 로컬 서버 (시연용)
echo  이 창을 닫지 마세요. 닫으면 로그인이 안 됩니다.
echo  서버가 켜진 뒤 I-Study.exe 를 실행하세요.
echo ============================================
python -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
