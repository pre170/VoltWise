@echo off
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-demo.ps1"
if errorlevel 1 (
  echo.
  echo [VoltWise] Startup failed. Review the error and .voltwise-run logs above.
  pause
  exit /b 1
)

echo [VoltWise] Demo is ready. Run stop-voltwise.bat when finished.
endlocal
