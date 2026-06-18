@echo off
setlocal
chcp 65001 >nul

set "ROOT=%~dp0"
set "SCRIPT=%ROOT%scripts\run_ui.ps1"

if not exist "%SCRIPT%" (
  echo Missing helper script: %SCRIPT%
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
set "CODE=%ERRORLEVEL%"

endlocal & exit /b %CODE%
