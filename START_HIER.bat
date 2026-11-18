@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONDONTWRITEBYTECODE=1"
if "%ALLIE_PORT%"=="" set "ALLIE_PORT=8765"
if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"
set "ALLIE_GENERATED_DIR=%~dp0generated"
set "UV_CACHE_DIR=%ALLIE_GENERATED_DIR%\cache\uv"
set "UV_PROJECT_ENVIRONMENT=%ALLIE_GENERATED_DIR%\environments\source"
set "UV_EXE=uv"
set "UV_TOOL_DIR=%ALLIE_GENERATED_DIR%\toolchains\uv"
set "PLAYWRIGHT_BROWSERS_PATH=%ALLIE_GENERATED_DIR%\cache\browser"
set "HF_HOME=%~dp0generated\dependencies\models"

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

echo [Allie] Pruefe Stockfish 19 gegen den offiziellen SHA-256 ...
"%UV_EXE%" run --frozen python source\app\backend\download_stockfish.py
if errorlevel 1 goto :stockfish_error

echo [Allie] Starte http://127.0.0.1:%ALLIE_PORT%/viewer
"%UV_EXE%" run --frozen python source\app\backend\live_server.py
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
echo FEHLER: Der lokale Server konnte nicht starten. Ist Port %ALLIE_PORT% bereits belegt?

:failed
if "%ALLIE_NO_BROWSER%"=="1" exit /b 1
pause
exit /b 1
