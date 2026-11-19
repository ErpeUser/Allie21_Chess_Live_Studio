param(
    [Parameter(Mandatory=$true)][string]$Bundle,
    [switch]$Check
)
$ErrorActionPreference = 'Stop'
$exe = Join-Path $Bundle 'Allie21 Chess Live Studio.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Verified executable is missing.' }
if (-not (Test-Path -LiteralPath (Join-Path $Bundle 'runtime\python.exe'))) { throw 'Portable runtime is missing.' }
if (-not (Test-Path -LiteralPath (Join-Path $Bundle 'app\release-version.json'))) { throw 'Release version proof is missing.' }
$desktop = [Environment]::GetFolderPath('Desktop')
$linkPath = Join-Path $desktop 'Allie21 Chess Live Studio.lnk'
$shell = New-Object -ComObject WScript.Shell
if ($Check) {
    if (-not (Test-Path -LiteralPath $linkPath)) { exit 1 }
    $existing = $shell.CreateShortcut($linkPath)
    $expectedTarget = [IO.Path]::GetFullPath($exe)
    $actualTarget = [IO.Path]::GetFullPath([string]$existing.TargetPath)
    $expectedWorkingDirectory = [IO.Path]::GetFullPath($Bundle)
    $actualWorkingDirectory = [IO.Path]::GetFullPath([string]$existing.WorkingDirectory)
    if (-not [StringComparer]::OrdinalIgnoreCase.Equals($actualTarget, $expectedTarget)) { exit 1 }
    if (-not [StringComparer]::OrdinalIgnoreCase.Equals($actualWorkingDirectory, $expectedWorkingDirectory)) { exit 1 }
    exit 0
}
$link = $shell.CreateShortcut($linkPath)
$link.TargetPath = $exe
$link.WorkingDirectory = $Bundle
$link.IconLocation = "$exe,0"
$link.Description = 'Allie - aktueller verifizierter portabler Build'
$link.Save()
Write-Host "Desktop shortcut updated: $desktop"
