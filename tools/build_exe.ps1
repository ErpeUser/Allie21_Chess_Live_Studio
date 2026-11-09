$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root 'release'
$env:UV_CACHE_DIR = Join-Path $root '.uv-cache'
$env:UV_TOOL_DIR = Join-Path $root '.uv-tools'
$env:UV_OFFLINE = '1'
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
    --icon (Join-Path $root 'assets\allie21_icon.ico') `
    --hidden-import 'pystray._win32' `
    --name 'Allie21 Chess Live Studio' `
    --distpath $dist `
    --workpath (Join-Path $root '.build\pyinstaller') `
    --specpath (Join-Path $root '.build') `
    (Join-Path $PSScriptRoot 'launcher.py')
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fehlgeschlagen (Code $LASTEXITCODE)." }

$bundle = Join-Path $dist 'Allie21 Chess Live Studio'
$app = Join-Path $bundle 'app'
$runtime = Join-Path $bundle 'runtime'
New-Item -ItemType Directory -Force -Path $app, $runtime | Out-Null

$stockfish = Join-Path $root 'backend\engines\stockfish.exe'
if (-not (Test-Path -LiteralPath $stockfish)) {
    throw 'Stockfish fehlt. Vor dem Build: uv run --frozen python backend\download_stockfish.py'
}

# Keep the release independent from a checkout, uv, and the user's PATH.  The
# executable remains the small tray controller; the adjacent app/runtime hold
# the server and its exact Python environment.
foreach ($directory in @('assets', 'backend', 'browser', 'viewer', 'beispiele')) {
    Copy-Item -LiteralPath (Join-Path $root $directory) -Destination $app -Recurse -Force
}
foreach ($file in @('config.json', 'pyproject.toml', 'uv.lock', 'README_DE.md',
                    'VERSIONEN.md', 'CHANGELOG.md', 'LICENSE.txt', 'QUELLEN_LIZENZEN.md')) {
    Copy-Item -LiteralPath (Join-Path $root $file) -Destination $app -Force
}

$venvConfig = Get-Content -LiteralPath (Join-Path $root '.allie-venv\pyvenv.cfg')
$homeLine = $venvConfig | Where-Object { $_ -match '^home\s*=\s*(.+)$' } | Select-Object -First 1
if (-not $homeLine -or $homeLine -notmatch '^home\s*=\s*(.+)$') {
    throw 'Python-Basis aus .allie-venv\pyvenv.cfg nicht lesbar.'
}
$basePython = $Matches[1].Trim()
if (-not (Test-Path -LiteralPath (Join-Path $basePython 'python.exe'))) {
    throw "Python-Basis fehlt: $basePython"
}
foreach ($item in @('DLLs', 'Lib', 'python.exe', 'pythonw.exe', 'python3.dll', 'python312.dll',
                    'LICENSE.txt')) {
    $source = Join-Path $basePython $item
    if (Test-Path -LiteralPath $source) {
        Copy-Item -LiteralPath $source -Destination $runtime -Recurse -Force
    }
}
$sitePackages = Join-Path $runtime 'Lib\site-packages'
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null
$venvSitePackages = Join-Path $root '.allie-venv\Lib\site-packages'
Get-ChildItem -LiteralPath $venvSitePackages -Force | Copy-Item -Destination $sitePackages -Recurse -Force

Write-Host "Fertig: $(Join-Path $bundle 'Allie21 Chess Live Studio.exe')"
Write-Host "Portable app: $app"
Write-Host "Portable runtime: $runtime"
