@echo off
title Asset Auto Generator v2
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup\setup.ps1"
echo.
pause
