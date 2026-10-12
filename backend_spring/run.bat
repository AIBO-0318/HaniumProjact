@echo off
setlocal

rem JDK 17: JAVA_HOME 이 이미 있으면 그대로, 없으면 기본 설치 경로 사용
if not defined JAVA_HOME if exist "C:\Program Files\Java\jdk-17" set "JAVA_HOME=C:\Program Files\Java\jdk-17"
if defined JAVA_HOME set "PATH=%JAVA_HOME%\bin;%PATH%"

echo [Spring Boot] Starting istudy-backend on port 8000...
call gradlew.bat bootRun

endlocal
