@echo off
setlocal
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHON_EXE=%~dp0.allie-venv\Scripts\python.exe"
set "MODEL_SETUP=%~dp0backend\model_setup.py"
if exist "%~dp0runtime\python.exe" if exist "%~dp0app\backend\model_setup.py" (
  set "PYTHON_EXE=%~dp0runtime\python.exe"
  set "MODEL_SETUP=%~dp0app\backend\model_setup.py"
)
if not exist "%PYTHON_EXE%" (
  echo Die Projektumgebung fehlt. Zuerst START_HIER.bat ausfuehren.
  pause
  exit /b 1
)
echo Dies kann grosse Modelldateien herunterladen. Der Server bleibt offline beim Laden.
choice /C JN /N /M "Gepinnte Allie-Gewichte jetzt herunterladen? [J/N] "
if errorlevel 2 exit /b 0
if errorlevel 1 goto :download
exit /b 1
:download
"%PYTHON_EXE%" "%MODEL_SETUP%" --download
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" goto :done
echo Einrichtung abgeschlossen. Den Allie-Server jetzt neu starten.
:done
pause
exit /b %RESULT%
