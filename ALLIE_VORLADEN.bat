@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Bitte zuerst START_HIER.bat ausfuehren. & pause & exit /b 1)
echo Lade die offiziellen Allie-2.1-Modellgewichte (ca. 18 GB). Speicher pruefen.
".venv\Scripts\python.exe" backend\preload_allie.py
pause
