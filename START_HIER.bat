@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "UV_CACHE_DIR=%~dp0.uv-cache"
set "UV_PROJECT_ENVIRONMENT=%~dp0.allie-venv"
set "UV_EXE=uv"

where uv >nul 2>nul
if errorlevel 1 (
  echo [Allie] Installiere den Paketmanager uv 0.13.7 ...
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/0.13.7/install.ps1 | iex"
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)
where uv >nul 2>nul
if errorlevel 1 goto :uv_error

echo [Allie] Pruefe die reproduzierbare Python-Umgebung ...
"%UV_EXE%" sync --frozen --extra vision --no-dev
if errorlevel 1 goto :setup_error

if not exist "backend\engines\stockfish.exe" (
  echo [Allie] Lade Stockfish 19 von der offiziellen Quelle ...
  "%UV_EXE%" run --frozen python backend\download_stockfish.py
  if errorlevel 1 goto :stockfish_error
)

echo [Allie] Starte http://127.0.0.1:8765/viewer
"%UV_EXE%" run --frozen python backend\live_server.py
if errorlevel 1 goto :server_error
exit /b 0

:uv_error
echo.
echo FEHLER: uv konnte nicht installiert oder gefunden werden.
goto :failed

:setup_error
echo.
echo FEHLER: Die Python-Umgebung konnte nicht eingerichtet werden.
goto :failed

:stockfish_error
echo.
echo FEHLER: Stockfish konnte nicht verifiziert oder geladen werden.
goto :failed

:server_error
echo.
echo FEHLER: Der lokale Server konnte nicht starten. Ist Port 8765 bereits belegt?

:failed
pause
exit /b 1
