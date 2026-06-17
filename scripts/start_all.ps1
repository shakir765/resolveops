# ResolveOps - one-click start (infra + all app services locally)
# Usage: .\scripts\start_all.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

Write-Host "== ResolveOps: starting all services ==" -ForegroundColor Cyan

& (Join-Path $PSScriptRoot "start_docker.ps1") -SeedKb

Write-Host ""
Write-Host "Launching app services..." -ForegroundColor Yellow
& (Join-Path $PSScriptRoot "start_apps.ps1")
