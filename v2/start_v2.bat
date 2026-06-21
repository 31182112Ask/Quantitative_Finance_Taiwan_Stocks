@echo off
setlocal
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
  echo [ERROR] Run setup_v2.bat first.
  exit /b 1
)
if not exist "frontend\node_modules" (
  echo [ERROR] Run setup_v2.bat first.
  exit /b 1
)

start "QFT V2 Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
start "QFT V2 Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Backend: http://127.0.0.1:8000/docs
echo Frontend: http://127.0.0.1:5173
endlocal
