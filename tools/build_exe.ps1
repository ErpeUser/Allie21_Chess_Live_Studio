$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root 'release'
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

& $uvx --python '3.12' --from 'pyinstaller==6.22.3' --with 'pystray==0.19.5' --with 'pillow==13.0.0' pyinstaller `
    --noconfirm --clean --onedir --windowed `
    --hidden-import 'pystray._win32' `
    --name 'Allie21 Chess Live Studio' `
    --distpath $dist `
    --workpath (Join-Path $root '.build\pyinstaller') `
    --specpath (Join-Path $root '.build') `
    (Join-Path $PSScriptRoot 'launcher.py')
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fehlgeschlagen (Code $LASTEXITCODE)." }

Write-Host "Fertig: $(Join-Path $dist 'Allie21 Chess Live Studio\Allie21 Chess Live Studio.exe')"
