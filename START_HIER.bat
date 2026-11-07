@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\auto_setup.ps1"
if errorlevel 1 (
  echo.
  echo Fehler bei Installation oder Start. Siehe Meldung oben.
  pause
  exit /b 1
)
