param([string]$DistPath = '', [switch]$Offline)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $DistPath) { $DistPath = Join-Path $root 'release' }
$env:UV_CACHE_DIR = Join-Path $root '.uv-cache'
$env:UV_TOOL_DIR = Join-Path $root '.uv-tools'
if ($Offline) { $env:UV_OFFLINE = '1' } else { Remove-Item Env:UV_OFFLINE -ErrorAction SilentlyContinue }
$uv = Get-Command uv -ErrorAction SilentlyContinue
$uvx = Get-Command uvx -ErrorAction SilentlyContinue
if (-not $uv -or -not $uvx) { throw 'uv/uvx fehlt. START_HIER.bat einmal ausfuehren, danach erneut bauen.' }
$releaseVenv = Join-Path $root '.build\release-venv'
$env:UV_PROJECT_ENVIRONMENT = $releaseVenv
Push-Location $root
try {
    & $uv.Source sync --frozen --no-dev --extra vision --python '3.12'
    if ($LASTEXITCODE -ne 0) { throw 'Locked release environment could not be synchronized. No unverified venv fallback.' }
    $stockfish = Join-Path $root 'backend\engines\stockfish.exe'
    if (-not (Test-Path -LiteralPath $stockfish)) {
        & (Join-Path $releaseVenv 'Scripts\python.exe') (Join-Path $root 'backend\download_stockfish.py')
        if ($LASTEXITCODE -ne 0) { throw 'Stockfish download failed.' }
    }
    $expectedStockfishSha256 = '45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0'
    if ((Get-FileHash -LiteralPath $stockfish -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedStockfishSha256) {
        throw 'Stockfish SHA-256 mismatch.'
    }
    $bundle = Join-Path $DistPath 'Allie21 Chess Live Studio'
    # Never destroy a known-good bundle through PyInstaller --noconfirm.
    if (Test-Path -LiteralPath $bundle) { throw 'Output bundle already exists. Use UPDATE_ALLIE.cmd for staged replacement.' }
    & $uvx.Source --python '3.12' --from 'pyinstaller==6.22.3' --with 'pystray==0.19.5' --with 'pillow==13.0.0' pyinstaller `
        --noconfirm --clean --onedir --windowed --icon (Join-Path $root 'assets\allie21_icon.ico') `
        --hidden-import 'pystray._win32' --name 'Allie21 Chess Live Studio' --distpath $DistPath `
        --workpath (Join-Path $root '.build\pyinstaller') --specpath (Join-Path $root '.build') `
        (Join-Path $PSScriptRoot 'launcher.py')
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed ($LASTEXITCODE)." }
    $app = Join-Path $bundle 'app'
    $runtime = Join-Path $bundle 'runtime'
    New-Item -ItemType Directory -Force -Path $app, $runtime | Out-Null
    foreach ($directory in @('assets', 'backend', 'browser', 'viewer', 'beispiele')) {
        Copy-Item -LiteralPath (Join-Path $root $directory) -Destination $app -Recurse -Force
    }
    foreach ($file in @('config.json', 'pyproject.toml', 'uv.lock', 'README_DE.md', 'VERSIONEN.md', 'CHANGELOG.md', 'LICENSE.txt', 'QUELLEN_LIZENZEN.md')) {
        Copy-Item -LiteralPath (Join-Path $root $file) -Destination $app -Force
    }
    $homeLine = Get-Content -LiteralPath (Join-Path $releaseVenv 'pyvenv.cfg') |
        Where-Object { $_ -match '^home\s*=\s*(.+)$' } | Select-Object -First 1
    if (-not $homeLine -or $homeLine -notmatch '^home\s*=\s*(.+)$') { throw 'Python base directory is missing.' }
    $basePython = $Matches[1].Trim()
    foreach ($item in @('DLLs', 'Lib', 'python.exe', 'pythonw.exe', 'python3.dll', 'python312.dll', 'LICENSE.txt')) {
        $source = Join-Path $basePython $item
        if (Test-Path -LiteralPath $source) { Copy-Item -LiteralPath $source -Destination $runtime -Recurse -Force }
    }
    $site = Join-Path $runtime 'Lib\site-packages'
    New-Item -ItemType Directory -Force -Path $site | Out-Null
    Get-ChildItem -LiteralPath (Join-Path $releaseVenv 'Lib\site-packages') -Force |
        Copy-Item -Destination $site -Recurse -Force
    $runtimePython = Join-Path $runtime 'python.exe'
    $inventory = Join-Path $app 'runtime-packages.json'
    & $runtimePython -c "import importlib.metadata as m,json,sys; p=[{'name':d.metadata['Name'],'version':d.version} for d in m.distributions() if d.metadata.get('Name')]; json.dump(sorted(p,key=lambda x:x['name'].lower()),open(sys.argv[1],'w',encoding='utf-8'),indent=2)" $inventory
    if ($LASTEXITCODE -ne 0) { throw 'Runtime inventory failed.' }
    $packages = Get-Content -LiteralPath $inventory -Raw | ConvertFrom-Json
    foreach ($package in $packages) {
        if ($package.name.ToLowerInvariant() -in @('pytest', 'ruff', 'mypy', 'playwright')) { throw "Quality dependency in release: $($package.name)" }
    }
    $manifest = Join-Path $bundle 'SHA256SUMS.txt'
    $lines = Get-ChildItem -LiteralPath $bundle -Recurse -File | Where-Object { $_.FullName -ne $manifest } |
        Sort-Object FullName | ForEach-Object {
            $relative = $_.FullName.Substring($bundle.Length + 1).Replace('\', '/')
            "$( (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() )  $relative"
        }
    $lines | Set-Content -LiteralPath $manifest -Encoding utf8
    Write-Host "Build ready for smoke test: $bundle"
} finally { Pop-Location }

