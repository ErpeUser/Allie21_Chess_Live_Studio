$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    & uv run --no-project --python '3.12' python tools/maintain.py --deploy-only --force-build
    if ($LASTEXITCODE -ne 0) { throw "Verified release update failed ($LASTEXITCODE)." }
} finally { Pop-Location }
