@echo off
SETLOCAL EnableExtensions EnableDelayedExpansion

REM ====================================================
REM FACTORY OS - ONE CLICK STARTUP
REM ====================================================

echo [PRE-FLIGHT] Checking Docker Status...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    color 4F
    echo.
    echo ====================================================
    echo [ERROR] DOCKER IS NOT RUNNING!
    echo ====================================================
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)
echo [OK] Docker is running.

REM ====================================================
REM 0. SAFETY CHECKS & UPDATES
REM ====================================================
echo [PRE-FLIGHT] Checking Safety...

if not exist ".env" (
    color 4F
    echo [ERROR] .env file not found!
    echo Please create one based on .env.example or configuration guide.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
    echo [INFO] Virtual Environment not found. Creating one...
    python -m venv .venv
)

echo [INFO] Activating and updating dependencies...
call .venv\Scripts\activate.bat
echo [INFO] Installing/Updating Python requirements...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [WARNING] Pip install failed. Please check requirements.txt.
)

REM ====================================================
REM 0.5 CLEANUP / RESTART (Robust)
REM ====================================================
echo [PRE-FLIGHT] Cleaning up old processes...
echo [INFO] Killing processes on Ports 8000, 8001, 3000...
call npx -y kill-port 8000 8001 3000
echo [OK] Ports cleared.

REM ====================================================
REM 1. START DATABASE
REM ====================================================
echo.
echo [1/3] Starting Database Infrastructure...
docker-compose up -d db
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start Docker containers.
    pause
    exit /b 1
)

echo Waiting 5 seconds for Database to warm up...
timeout /t 5 /nobreak >nul

REM ====================================================
REM 2. START BACKEND (New Window)
REM ====================================================
echo.
echo [2/3] Launching Backend API...
start "FactoryOS Backend" cmd /k "call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

REM ====================================================
REM 3. START FRONTEND (New Window)
REM ====================================================
echo.
echo [3/3] Launching Frontend Dashboard...
cd frontend
echo [INFO] Installing/Updating Frontend dependencies...
cmd /c "npm install"
start "FactoryOS Frontend" cmd /k "npm run dev"
cd ..

REM ====================================================
REM SUCCESS SUMMARY
REM ====================================================
color 0A
echo.
echo ====================================================
echo               FACTORY OS STARTED
echo ====================================================
echo.
echo [INFRA]  Database:   Running (Docker)
echo [API]    Backend:    http://127.0.0.1:8000 (Check "FactoryOS Backend" window)
echo [UI]     Frontend:   http://localhost:3000 (Check "FactoryOS Frontend" window)
echo.
echo Keep this window open to maintain the session.
echo Press any key to stop DB and exit...
echo.
pause

REM Cleanup on exit
echo Stopping Database...
docker-compose down
