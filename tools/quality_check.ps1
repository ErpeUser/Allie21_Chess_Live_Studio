param(
    [switch]$InstallBrowsers,
    [switch]$SkipTests
)
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$env:UV_CACHE_DIR = Join-Path $root '.uv-quality-cache'
$qualityVenv = Join-Path $root '.quality-venv'
$qualityPython = Join-Path $qualityVenv 'Scripts\python.exe'
$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) { throw 'uv fehlt. START_HIER.bat oder uv-Installation zuerst ausführen.' }

if (-not (Test-Path -LiteralPath $qualityPython)) {
    & $uv.Source venv --python '3.12' $qualityVenv
    if ($LASTEXITCODE -ne 0) { throw "Qualitätsumgebung konnte nicht erstellt werden (Code $LASTEXITCODE)." }
}

# Install only on demand into a separate environment; the production .allie-venv
# and the portable release remain free of lint/type/browser tooling.
& $uv.Source pip install --python $qualityPython `
    'mypy>=1.13,<2' 'playwright>=1.50,<2' 'pytest>=8.3,<9' 'ruff>=0.8,<1'
if ($LASTEXITCODE -ne 0) { throw "Qualitätswerkzeuge konnten nicht installiert werden (Code $LASTEXITCODE)." }

if ($InstallBrowsers) {
    & $qualityPython -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw "Playwright-Chromium konnte nicht installiert werden (Code $LASTEXITCODE)." }
}

Push-Location $root
try {
    $ruffCode = 0
    $mypyCode = 0
    $pytestCode = 0
    & $qualityPython -m ruff check backend tools tests
    $ruffCode = $LASTEXITCODE
    & $qualityPython -m mypy backend --ignore-missing-imports
    $mypyCode = $LASTEXITCODE
    if (-not $SkipTests) {
        # Reuse the already-tested production dependencies without duplicating
        # the multi-gigabyte Torch/Vision environment in .quality-venv.
        $productionSitePackages = Join-Path $root '.allie-venv\Lib\site-packages'
        $env:PYTHONPATH = "$productionSitePackages;$(Join-Path $root 'backend')"
        & $qualityPython -m pytest -q -p no:cacheprovider
        $pytestCode = $LASTEXITCODE
    }
    Write-Host "Quality summary: ruff=$ruffCode mypy=$mypyCode pytest=$pytestCode"
    if ($ruffCode -or $mypyCode -or $pytestCode) { exit 1 }
} finally {
    Pop-Location
}
