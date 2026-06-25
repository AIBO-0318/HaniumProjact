# Spring Boot 백엔드 실행 스크립트 (PowerShell)
$env:JAVA_HOME = "C:\Program Files\Java\jdk-17"
$env:Path = "$env:JAVA_HOME\bin;" + [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Set-Location "$PSScriptRoot\backend_spring"
Write-Host "[Spring Boot] istudy-backend 시작 (port 8000)..." -ForegroundColor Cyan
.\gradlew.bat bootRun
