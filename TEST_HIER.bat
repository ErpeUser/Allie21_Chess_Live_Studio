@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Bitte zuerst START_HIER.bat ausfuehren. & pause & exit /b 1)
".venv\Scripts\python.exe" -m unittest discover -s tests -v
".venv\Scripts\python.exe" backend\doctor.py
pause
