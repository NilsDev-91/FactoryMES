@echo off
title FactoryOS Launcher
echo 🚀 Starting FactoryOS Infrastructure...

:: 1. Start Backend (via new secure launcher)
echo Starting Backend (Python/FastAPI)...
start "FactoryMES Backend" cmd /k ".venv\Scripts\python.exe run.py"

:: 2. Start Frontend (Next.js)
echo Starting Frontend (Next.js)...
cd frontend
start "FactoryMES Frontend" cmd /k "npm run dev"

:: Return to root
cd ..

echo.
echo ✅ System booting up.
echo    - Backend: http://localhost:8000
echo    - Frontend: http://localhost:3000
echo.
pause
