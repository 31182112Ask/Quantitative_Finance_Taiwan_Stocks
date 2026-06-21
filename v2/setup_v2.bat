@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul || (echo [ERROR] Python launcher not found. Install Python 3.12+ & exit /b 1)
where npm >nul 2>nul || (echo [ERROR] npm not found. Install Node.js LTS & exit /b 1)

if not exist "backend\.venv\Scripts\python.exe" (
  py -3.12 -m venv backend\.venv || exit /b 1
)
backend\.venv\Scripts\python -m pip install --upgrade pip || exit /b 1
backend\.venv\Scripts\python -m pip install -e "backend[dev]" || exit /b 1

pushd frontend
call npm install || (popd & exit /b 1)
popd

echo.
echo Setup complete. Run start_v2.bat.
endlocal
