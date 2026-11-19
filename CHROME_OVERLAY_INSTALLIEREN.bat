@echo off
start "" chrome.exe "chrome://extensions/"
start "" explorer.exe "%~dp0source\app\browser"
echo.
echo 1. Entwicklermodus einschalten.
echo 2. Entpackte Erweiterung laden anklicken.
echo 3. Den geoeffneten Ordner "source\app\browser" auswaehlen.
echo 4. Chess.com oder Lichess neu laden.
pause
