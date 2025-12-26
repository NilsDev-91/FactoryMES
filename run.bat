@echo off
echo Starting FactoryOS...

:: Start Backend Daemon
echo Starting Backend Daemon...
start "FactoryOS Backend Daemon" cmd /k "python main_daemon.py"

:: Start Backend API Server
echo Starting API Server...
start "FactoryOS API Server" cmd /k "python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

:: Start Frontend
echo Starting Frontend Application...
start "FactoryOS Frontend" cmd /k "cd frontend && npm run dev"

echo FactoryOS startup initiated.
