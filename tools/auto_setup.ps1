# Repeatable, local Windows setup. Uses only Microsoft winget and official PyPI.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$root = (Get-Location).Path
$venvDir = Join-Path $root '.venv'
$venv = Join-Path $venvDir 'Scripts\python.exe'
$stamp = Join-Path $venvDir 'requirements-sha256.txt'

function Find-Python {
  $choices = @()
  if (Get-Command py -ErrorAction SilentlyContinue) { $choices += [pscustomobject]@{ Executable = 'py'; Args = @('-3.12') } }
  $local = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
  if (Test-Path $local) { $choices += [pscustomobject]@{ Executable = $local; Args = @() } }
  if (Get-Command python -ErrorAction SilentlyContinue) { $choices += [pscustomobject]@{ Executable = 'python'; Args = @() } }
  foreach ($p in $choices) {
    try {
      $args_ = [string[]]$p.Args
      $pythonExe = [string]$p.Executable
      $result = & $pythonExe @args_ -c "import sys;print('OK' if sys.version_info[:2] == (3,12) and sys.maxsize > 2**32 else 'NO')" 2>$null
      if ($LASTEXITCODE -eq 0 -and @($result)[0].Trim() -eq 'OK') { return $p }
    } catch { }
  }
  return $null
}

Write-Host '=== Allie 2.1 Live Studio v10 | Windows Setup ===' -ForegroundColor Cyan
$py = Find-Python
if (-not $py) {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw 'Python 3.12 x64 fehlt. Installation: https://www.python.org/downloads/windows/'
  }
  Write-Host 'Python 3.12 x64 wird via winget installiert.' -ForegroundColor Yellow
  & winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  $wingetExitCode = $LASTEXITCODE
  $py = Find-Python
  if (-not $py) {
    if ($wingetExitCode -ne 0) {
      throw "winget meldet Fehlercode $wingetExitCode und Python 3.12 x64 wurde nicht gefunden. Python bitte von https://www.python.org/downloads/windows/ installieren."
    }
    throw 'Python wurde installiert, ist aber noch nicht auffindbar. Bitte Windows-Terminal neu starten und die EXE erneut öffnen.'
  }
}
Write-Host ("Python 3.12 x64 gefunden: " + $py.Executable) -ForegroundColor Green
if (-not (Test-Path $venv)) {
  $cmdArgs = [string[]]$py.Args
  $pythonExe = [string]$py.Executable
  & $pythonExe @cmdArgs -m venv $venvDir
  if ($LASTEXITCODE -ne 0) { throw 'Lokale Python-Umgebung konnte nicht erstellt werden.' }
}
$hash = (Get-FileHash -Algorithm SHA256 (Join-Path $root 'requirements.txt')).Hash
$needInstall = (-not (Test-Path $stamp))
if (-not $needInstall) { $needInstall = ((Get-Content $stamp -Raw).Trim() -ne $hash) }
if (-not $needInstall) {
  & $venv -c 'import chess,chessvision,rapidocr,onnxruntime,transformers,torch'
  $needInstall = ($LASTEXITCODE -ne 0)
}
if ($needInstall) {
  Write-Host 'Installiere Bibliotheken (inkl. PyTorch, Modell-Laufzeit und Bild-Erkennung) ...'
  & $venv -m pip install --disable-pip-version-check --prefer-binary -r requirements.txt
  if ($LASTEXITCODE -ne 0) { throw 'Bibliotheken konnten nicht installiert werden. Internetzugang und Speicherplatz pruefen.' }
  Set-Content -Path $stamp -Value $hash -Encoding Ascii
}
$cfg = Get-Content (Join-Path $root 'config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($cfg.auto_download_stockfish) {
  & $venv backend\download_stockfish.py
  if ($LASTEXITCODE -ne 0) { Write-Warning 'Stockfish nicht geladen. Die Modellanalyse kann dennoch laufen.' }
}
if ($cfg.auto_download_openings) {
  & $venv backend\download_openings.py
  if ($LASTEXITCODE -ne 0) { Write-Warning 'ECO-Datenbank nicht geladen. Grund-Eröffnungen sind eingebaut.' }
}
if ($cfg.prefetch_allie_weights) {
  & $venv backend\preload_allie.py
  if ($LASTEXITCODE -ne 0) { Write-Warning 'Allie-2.1-Gewichte noch nicht geladen.' }
}
Write-Host 'Bereit: http://127.0.0.1:8765/viewer' -ForegroundColor Green
& $venv backend\live_server.py
if ($LASTEXITCODE -ne 0) { throw 'Server konnte nicht gestartet werden (Port 8765 belegt?).' }
