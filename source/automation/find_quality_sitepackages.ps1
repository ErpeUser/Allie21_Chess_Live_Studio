param(
    [Parameter(Mandatory = $true)][string]$Root,
    [Parameter(Mandatory = $true)][string]$StateRoot
)
$ErrorActionPreference = 'Stop'

# Prefer the source environment, but a verified portable installation carries
# the same locked production packages and does not require another Torch copy.
$candidates = @(
    (Join-Path $StateRoot 'environments\source\Lib\site-packages'),
    (Join-Path $Root 'generated\dist\win\Allie21 Chess Live Studio\runtime\Lib\site-packages')
)
foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate -PathType Container) {
        Write-Output (Resolve-Path -LiteralPath $candidate).Path
        return
    }
}
throw 'Keine Produktionsbibliotheken gefunden. START_HIER.bat oder den portablen Release installieren.'
