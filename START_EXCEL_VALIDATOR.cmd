@echo off
cd /d "%~dp0"
title Data Quality Detective - Excel Native Validation
python -m webapp.excel_desktop
if errorlevel 1 echo If necessary run INSTALL_ON_WINDOWS.cmd first.
pause
