$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$tmp = Join-Path $root '.build\pyinstaller-dist'
$work = Join-Path $root '.build\pyinstaller2'
Remove-Item $tmp, $work -Recurse -Force -ErrorAction SilentlyContinue
& uvx --python '3.12' --from 'pyinstaller==6.22.3' --with 'pystray==0.19.5' --with 'pillow==13.0.0' pyinstaller `
  --noconfirm --clean --onedir --windowed --icon (Join-Path $root 'assets\allie21_icon.ico') `
  --hidden-import 'pystray._win32' --name 'Allie21 Chess Live Studio' `
  --distpath $tmp --workpath $work --specpath (Join-Path $root '.build') `
  (Join-Path $PSScriptRoot 'launcher.py')
if ($LASTEXITCODE -ne 0) { throw "PyInstaller fehlgeschlagen ($LASTEXITCODE)." }
$bundle = Join-Path $root 'release\Allie21 Chess Live Studio'
Copy-Item (Join-Path $tmp 'Allie21 Chess Live Studio\Allie21 Chess Live Studio.exe') (Join-Path $bundle 'Allie21 Chess Live Studio.exe') -Force
$app = Join-Path $bundle 'app'
foreach ($directory in @('assets','backend','browser','viewer','beispiele')) {
  Copy-Item (Join-Path $root $directory) (Join-Path $app $directory) -Recurse -Force
}
foreach ($file in @('config.json','pyproject.toml','uv.lock','README_DE.md','VERSIONEN.md','CHANGELOG.md','LICENSE.txt','QUELLEN_LIZENZEN.md')) {
  Copy-Item (Join-Path $root $file) (Join-Path $app $file) -Force
}
Write-Host "Release aktualisiert: $bundle"
