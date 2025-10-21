@echo off
REM Quick fix script for Windows Docker deployment
REM Run this before docker-compose up if you encounter issues

echo ========================================
echo AMT Trading Bot - Windows Docker Fix
echo ========================================
echo.

REM Check if yarn.lock exists, if not create it
if not exist "frontend\yarn.lock" (
    echo Creating yarn.lock...
    cd frontend
    call yarn install
    cd ..
    echo yarn.lock created!
) else (
    echo yarn.lock already exists
)

echo.
echo Fix complete! Now run:
echo docker compose up -d --build
echo.
pause
