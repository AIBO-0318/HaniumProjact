@echo off
setlocal

set JAVA_HOME=C:\Program Files\Java\jdk-17
set PATH=%JAVA_HOME%\bin;%PATH%

echo [Spring Boot] Starting istudy-backend on port 8000...
call gradlew.bat bootRun

endlocal
