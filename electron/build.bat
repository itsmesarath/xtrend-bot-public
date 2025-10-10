@echo off
REM Windows Build Script for AMT Trading Bot
REM Run this to build the complete Electron desktop application

echo ================================
echo AMT Trading Bot - Build Script
echo ================================
echo.

REM Check if Node.js is installed
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Check if Python is installed
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PyInstaller is not installed
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo Step 1/3: Building Backend...
echo.
cd ..\backend
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.spec del /q *.spec

python -m PyInstaller --onefile --name server server.py --distpath ./dist
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Backend build failed
    pause
    exit /b 1
)
echo Backend build successful!
echo.

echo Step 2/3: Building Frontend...
echo.
cd ..\frontend
if exist build rmdir /s /q build

call yarn install
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install frontend dependencies
    pause
    exit /b 1
)

call yarn build
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Frontend build failed
    pause
    exit /b 1
)
echo Frontend build successful!
echo.

echo Step 3/3: Packaging Electron App...
echo.
cd ..\electron

call yarn install
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install Electron dependencies
    pause
    exit /b 1
)

call yarn build
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Electron packaging failed
    pause
    exit /b 1
)

echo.
echo ================================
echo Build Complete!
echo ================================
echo.
echo Installer location:
echo %CD%\dist\AMT Trading Bot Setup 1.0.0.exe
echo.
echo You can now distribute this installer to Windows users.
echo.
pause
