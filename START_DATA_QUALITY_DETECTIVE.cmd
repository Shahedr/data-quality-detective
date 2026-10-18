@echo off
cd /d "%~dp0"
title Data Quality Detective - Local Web App
echo Starting Data Quality Detective on the first available local port...
python -m webapp.launch_local
if errorlevel 1 (
  echo.
  echo If the application is not installed, run INSTALL_ON_WINDOWS.cmd once.
)
pause
