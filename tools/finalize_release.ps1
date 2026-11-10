$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$bundle = Join-Path $root 'release\Allie21 Chess Live Studio'
$runtimePython = Join-Path $bundle 'runtime\python.exe'
$inventory = Join-Path $bundle 'app\runtime-packages.json'
& $runtimePython -c "import importlib.metadata as m, json; p=[{'name':d.metadata['Name'],'version':d.version} for d in m.distributions() if d.metadata.get('Name')]; json.dump(sorted(p,key=lambda x:x['name'].lower()), open(r'$inventory','w',encoding='utf-8'), ensure_ascii=False, indent=2)"
if ($LASTEXITCODE -ne 0) { throw 'Runtime-Inventar fehlgeschlagen.' }
$manifest = Join-Path $bundle 'SHA256SUMS.txt'
$lines = Get-ChildItem $bundle -Recurse -File | Where-Object { $_.FullName -ne $manifest } | Sort-Object FullName | ForEach-Object {
  $relative = $_.FullName.Substring($bundle.Length + 1).Replace('\','/')
  "$( (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() )  $relative"
}
$lines | Set-Content $manifest -Encoding utf8
Write-Host "Manifest erstellt: $manifest"
