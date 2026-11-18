@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
if "%ALLIE_UPDATE_ACTIVE%"=="1" exit /b 0
call :python tools\maintain.py --git-only --process-prs --cleanup --install-hooks %*
set "SYNC_RESULT=%ERRORLEVEL%"
if "%SYNC_RESULT%"=="1" exit /b 1
if %SYNC_RESULT% GTR 2 exit /b %SYNC_RESULT%
rem Start a fresh interpreter after pull so deployment uses the updated code.
call :python tools\maintain.py --deploy-only %*
if errorlevel 1 exit /b %ERRORLEVEL%
echo Update beendet. Bericht: %LOCALAPPDATA%\Allie21\maintenance\maintenance-report.json
exit /b %SYNC_RESULT%
:python
where py >nul 2>&1
if not errorlevel 1 (py -3 %* & exit /b)
where python >nul 2>&1
if not errorlevel 1 (python %* & exit /b)
where uv >nul 2>&1
if not errorlevel 1 (uv run --no-project --python 3.12 python %* & exit /b)
echo Python 3 oder uv fehlt. START_HIER.bat zuerst ausfuehren.
exit /b 1
