param(
    [string]$OutputFile = "route_inventory.txt"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$routes = @()
$routes += rg -n "@.*route\(" backend/project/blueprints --glob "*.py"
$routes += rg -n "@.*route\(" backend/project/modules --glob "*.py"
if (-not $routes) {
    Write-Error "Nenhuma rota encontrada em backend/project/blueprints ou backend/project/modules."
}

$normalized = $routes |
    ForEach-Object {
        $parts = $_ -split ":", 3
        [PSCustomObject]@{
            File = $parts[0]
            Line = [int]$parts[1]
            Route = $parts[2].Trim()
        }
    } |
    Sort-Object File, Line

"# Route Inventory" | Out-File -FilePath $OutputFile -Encoding utf8
"# GeneratedAt: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")" | Out-File -FilePath $OutputFile -Append -Encoding utf8
"" | Out-File -FilePath $OutputFile -Append -Encoding utf8

$normalized | ForEach-Object {
    "$($_.File):$($_.Line) - $($_.Route)" | Out-File -FilePath $OutputFile -Append -Encoding utf8
}

Write-Host "Inventário gerado em: $OutputFile"
