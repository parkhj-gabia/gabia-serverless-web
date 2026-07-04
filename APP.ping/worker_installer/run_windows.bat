@echo off
title Gabia Serverless Ping Worker (Windows)
echo =========================================
echo  Gabia Serverless Ping Worker Installer ^& Runner (Windows)
echo =========================================

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 에러: Python이 설치되어 있지 않거나 PATH 등록이 누락되었습니다.
    echo     python.exe를 찾을 수 없습니다. python.org에서 설치 시 
    echo     "Add Python to PATH" 옵션을 반드시 선택해 주세요.
    pause
    exit /b 1
)

:: Check Node.js/npm for npx tunnel
set HAS_NPX=true
npx --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] 알림: Node.js/npm이 설치되어 있지 않습니다.
    echo     설치하지 않아도 로컬 주소(127.0.0.1)로 연동 가능하지만,
    echo     GCP 웹 사이트에서 접속하려면 Node.js를 설치하여 npx 터널을 가동해야 합니다.
    echo     (https://nodejs.org/ 에서 다운로드 가능)
    echo -----------------------------------------
    set HAS_NPX=false
)

:: Install dependencies
echo [*] 필요한 Python 패키지(Flask)를 설치하는 중...
python -m pip install -r requirements.txt

:: Run Python worker and spawn tunnel, forwarding command-line arguments
echo [*] 워커 및 터널 서비스를 가동합니다...
if "%HAS_NPX%"=="true" (
    python worker.py --tunnel %*
) else (
    python worker.py %*
)
pause
