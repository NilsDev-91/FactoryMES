@echo off

:: 1. The "Silver Bullet" Cleanup (SAFE MODE)
echo [FactoryOS] Performing robust cleanup...
:: NUR cmd.exe Prozesse töten, die "FactoryOS" im Titel haben. Editor bleibt offen.
powershell -Command "Get-Process cmd | Where-Object {$_.MainWindowTitle -like 'FactoryOS*'} | Stop-Process -Force" >nul 2>&1

:: 2. Timing & Self-Identification
timeout /t 1 /nobreak >nul
title FactoryOS Launcher
cls

echo.
echo ===================================================
echo --- CLEANUP COMPLETE: Ports 3000/8000 freed ---
echo ===================================================
echo.
setlocal

:: 3. Docker Check
echo [FactoryOS] Checking Docker status...
docker info >nul 2>&1
if %errorlevel% == 0 (
    echo [FactoryOS] Docker Engine is already running.
    goto :STARTUP
)

:: 4. Auto-Start Logic
echo [FactoryOS] Docker is not running.
echo Starting Docker Desktop...
if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
) else (
    echo [ERROR] Docker Desktop executable not found at C:\Program Files\Docker\Docker\Docker Desktop.exe
    echo [ERROR] Please start Docker manually.
    pause
    exit /b 1
)

:: 5. Wait Loop
echo [FactoryOS] Waiting for Docker Engine to start...
:WAIT_LOOP
timeout /t 5 /nobreak >nul
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [FactoryOS] Waiting for Docker Engine...
    goto :WAIT_LOOP
)

echo [FactoryOS] Docker Engine started successfully.

:: 6. Launch Stack
:STARTUP
echo [FactoryOS] Cleaning up previous containers...
docker-compose down --remove-orphans

echo [FactoryOS] Starting Database Containers (with build)...
docker-compose up --build -d

echo [FactoryOS] Starting Backend API Server...
start "FactoryOS API" cmd /k "python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo [FactoryOS] Starting Worker Service...
start "FactoryOS Worker" cmd /k "python worker_service.py"

echo [FactoryOS] Starting Order Service...
start "FactoryOS Orders" cmd /k "python order_service.py"

echo [FactoryOS] Starting Frontend...
start "FactoryOS Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================
echo [FactoryOS] All systems go!
echo [FactoryOS] Backend: http://localhost:8000
echo [FactoryOS] Frontend: http://localhost:3000
echo ===================================================
echo.

pause
