@echo off
cd /d "%~dp0"
title Data Quality Detective - Setup
echo Installing local browser, macro scanner, and Excel integrations...
python -m pip install -e ".[web,excel-native,macro-audit]"
if errorlevel 1 (
  echo Installation failed. Check the Python error above.
  pause
  exit /b 1
)
echo.
echo Setup complete. Double-click START_DATA_QUALITY_DETECTIVE.cmd to launch.
pause
