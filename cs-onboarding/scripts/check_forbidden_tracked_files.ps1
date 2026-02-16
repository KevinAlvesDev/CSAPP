#!/usr/bin/env pwsh

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$patterns = @(
    "backend/uploads/",
    "frontend/static/uploads/",
    "backend/project/logs/",
    ".db",
    ".sqlite",
    ".sqlite3"
)

$tracked = git ls-files
$violations = @()

foreach ($file in $tracked) {
    $normalized = $file.Replace("\", "/")
    if (
        $normalized.StartsWith("backend/uploads/") -or
        $normalized.StartsWith("frontend/static/uploads/") -or
        $normalized.StartsWith("backend/project/logs/") -or
        $normalized.EndsWith(".db") -or
        $normalized.EndsWith(".sqlite") -or
        $normalized.EndsWith(".sqlite3")
    ) {
        $violations += $normalized
    }
}

if ($violations.Count -gt 0) {
    Write-Host "Arquivos proibidos versionados encontrados:"
    $violations | Sort-Object | ForEach-Object { Write-Host " - $_" }
    exit 1
}

Write-Host "OK: nenhum arquivo proibido versionado."
