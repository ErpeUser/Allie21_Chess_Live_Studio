param([Parameter(Mandatory=$true)][string]$Bundle)
$ErrorActionPreference = 'Stop'
$exe = Join-Path $Bundle 'Allie21 Chess Live Studio.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw 'Verified executable is missing.' }
if (-not (Test-Path -LiteralPath (Join-Path $Bundle 'runtime\python.exe'))) { throw 'Portable runtime is missing.' }
$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut((Join-Path $desktop 'Allie21 Chess Live Studio.lnk'))
$link.TargetPath = $exe
$link.WorkingDirectory = $Bundle
$link.IconLocation = "$exe,0"
$link.Description = 'Allie - aktueller verifizierter portabler Build'
$link.Save()
Write-Host "Desktop shortcut updated: $desktop"
