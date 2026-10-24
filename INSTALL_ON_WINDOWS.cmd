@echo off
cd /d "%~dp0"
title Data Quality Detective - Setup
if not exist "pyproject.toml" (
  echo Extract the complete app ZIP, then run this installer from that folder.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating the app environment...
  python -m venv .venv
  if errorlevel 1 goto failed
)
echo Installing the local app...
".venv\Scripts\python.exe" -m pip install -e ".[web,excel-native,macro-audit]"
if errorlevel 1 goto failed
echo Setup complete. Double-click START_DATA_QUALITY_DETECTIVE.cmd to launch.
pause
exit /b 0
:failed
echo Setup could not finish. Check that Python is installed and read the error above.
pause
exit /b 1
