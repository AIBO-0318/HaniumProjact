# I-Study 두 서버 동시 실행 (Spring Boot 8000 + FastAPI AI 8001)
# 사용: 우클릭 > PowerShell로 실행  또는  powershell -ExecutionPolicy Bypass -File .\run_all.ps1
$root = $PSScriptRoot

if (-not (Test-Path "$root\.env")) {
    Write-Host "[오류] .env 파일이 없습니다. .env.example 을 복사해 .env 를 만들고 DB_PASSWORD, JWT_SECRET 을 채우세요." -ForegroundColor Red
    exit 1
}
# 가상환경이 있으면 그 Python 을 사용
$py = if (Test-Path "$root\venv\Scripts\python.exe") { "$root\venv\Scripts\python.exe" } else { "python" }

Write-Host "I-Study 서버 2개를 각각 새 창에서 시작합니다..." -ForegroundColor Cyan

# 1) Spring Boot (REST + 웹, 8000) — 기존 run_spring.ps1 재사용
Start-Process powershell -ArgumentList '-NoExit','-ExecutionPolicy','Bypass','-File',"$root\run_spring.ps1"

# 2) FastAPI AI (시선추적 WS, 8001)
Start-Process powershell -ArgumentList '-NoExit','-Command',"Set-Location '$root'; & '$py' run_ai_server.py"

Write-Host "  Spring Boot -> http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "  FastAPI AI  -> http://127.0.0.1:8001/health  (ws://.../ws/gaze)" -ForegroundColor Green
Write-Host "각 창에서 Ctrl+C 로 개별 종료하세요."
