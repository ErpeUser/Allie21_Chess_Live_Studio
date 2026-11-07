@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "UV_CACHE_DIR=%~dp0.uv-cache"

where uv >nul 2>nul
if errorlevel 1 (
  echo [Allie] Installiere den Paketmanager uv 0.13.7 ...
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/0.13.7/install.ps1 | iex"
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

where uv >nul 2>nul
if errorlevel 1 goto :uv_error

echo [Allie] Pruefe die reproduzierbare Python-Umgebung ...
uv sync --frozen --all-extras --no-dev
if errorlevel 1 goto :setup_error

if not exist "backend\engines\stockfish.exe" (
  echo [Allie] Lade Stockfish 19 von der offiziellen Quelle ...
  uv run --frozen python backend\download_stockfish.py
  if errorlevel 1 echo [Hinweis] Stockfish konnte nicht geladen werden. Allie funktioniert trotzdem.
)

echo [Allie] Starte http://127.0.0.1:8765/viewer
uv run --frozen python backend\live_server.py
if errorlevel 1 goto :server_error
exit /b 0

:uv_error
echo.
echo FEHLER: uv konnte nicht installiert oder gefunden werden.
echo Manuelle Installation: https://docs.astral.sh/uv/getting-started/installation/
goto :failed

:setup_error
echo.
echo FEHLER: Die Python-Umgebung konnte nicht eingerichtet werden.
echo Pruefe Internetzugang, freien Speicherplatz und die Meldung oben.
goto :failed

:server_error
echo.
echo FEHLER: Der lokale Server konnte nicht starten. Ist Port 8765 bereits belegt?

:failed
pause
exit /b 1
