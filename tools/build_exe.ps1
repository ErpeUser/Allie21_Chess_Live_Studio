$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$env:UV_CACHE_DIR = Join-Path $root '.uv-cache'
$uvx = Join-Path $root '.venv\Scripts\uvx.exe'
if (-not (Test-Path -LiteralPath $uvx)) {
    $uvx = Join-Path $env:USERPROFILE '.local\bin\uvx.exe'
}
if (-not (Test-Path -LiteralPath $uvx)) {
    $command = Get-Command uvx -ErrorAction SilentlyContinue
    if (-not $command) { throw 'uvx fehlt. START_HIER.bat einmal ausführen und erneut bauen.' }
    $uvx = $command.Source
}

& $uvx --from 'pyinstaller==6.22.3' pyinstaller `
    --noconfirm --clean --onefile --windowed `
    --name 'Allie21 Chess Live Studio' `
    --distpath $root `
    --workpath (Join-Path $root '.build\pyinstaller') `
    --specpath (Join-Path $root '.build') `
    (Join-Path $PSScriptRoot 'launcher.py')
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fehlgeschlagen (Code $LASTEXITCODE)." }

Write-Host "Fertig: $(Join-Path $root 'Allie21 Chess Live Studio.exe')"
