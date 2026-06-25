# I-Study 서버 시작 스크립트 (Spring Boot 8000 + FastAPI AI 8001)
# 관리자 권한 불필요

$ErrorActionPreference = "Stop"

$PROJECT_ROOT = "d:\I-Study"
$SPRING_DIR = "$PROJECT_ROOT\backend_spring"
$VENV_PYTHON = "$PROJECT_ROOT\venv\Scripts\python.exe"

Write-Host "=== I-Study 서버 시작 ===" -ForegroundColor Cyan
Write-Host "Spring Boot 8000 + FastAPI AI 8001" -ForegroundColor Cyan
Write-Host ""

# Spring Boot 실행 (백그라운드)
Write-Host "[1/2] Spring Boot 시작..." -ForegroundColor Yellow
$springJob = Start-Job -ScriptBlock {
    $env:JAVA_HOME = "C:\Program Files\Java\jdk-17"
    $env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
    Set-Location "d:\I-Study\backend_spring"
    & cmd /c run.bat
} -Name "SpringBoot"

# FastAPI AI 실행 (백그라운드)
Write-Host "[2/2] FastAPI AI 시작..." -ForegroundColor Yellow
$aiJob = Start-Job -ScriptBlock {
    Set-Location "d:\I-Study"
    & "d:\I-Study\venv\Scripts\python.exe" run_ai_server.py
} -Name "FastAPI_AI"

# 기동 대기
Write-Host ""
Write-Host "서버 기동 대기 중..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# 상태 확인
$springUp = $false
$aiUp = $false

# 최대 30초 대기
for ($i = 0; $i -lt 30; $i++) {
    $springUp = [bool](Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
    $aiUp = [bool](Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue)
    if ($springUp -and $aiUp) {
        break
    }
    Start-Sleep -Seconds 1
}

Write-Host ""
if ($springUp -and $aiUp) {
    Write-Host "✓ 두 서버 모두 정상 기동 완료" -ForegroundColor Green
    Write-Host "  Spring: http://127.0.0.1:8000" -ForegroundColor Gray
    Write-Host "  AI    : http://127.0.0.1:8001/health" -ForegroundColor Gray
    Write-Host ""
    Write-Host "서버를 종료하려면:" -ForegroundColor Gray
    Write-Host "  .\stop_servers.ps1" -ForegroundColor Gray
} else {
    Write-Host "✗ 서버 기동 실패" -ForegroundColor Red
    Write-Host "  Spring 8000: $springUp" -ForegroundColor Gray
    Write-Host "  AI 8001: $aiUp" -ForegroundColor Gray
    Write-Host ""
    Write-Host "백그라운드 작업 상태:" -ForegroundColor Gray
    Get-Job | Select-Object Name, State
}
