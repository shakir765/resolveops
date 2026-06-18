# ResolveOps - stop Docker infrastructure only (postgres, redis, rabbitmq).
# Does NOT stop local app processes (API, RAG, Tool Runner, Graph Worker).
#
# Usage:
#   .\scripts\stop_docker.ps1                  # stop infra containers (data preserved)
#   .\scripts\stop_docker.ps1 -ClearData       # truncate app tables, then stop infra
#   .\scripts\stop_docker.ps1 -ResetVolume     # remove infra containers + named volumes

param(
    [switch]$ClearData,
    [switch]$ResetVolume
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

. (Join-Path $PSScriptRoot "docker_infra.ps1")

Write-Host "== ResolveOps: stopping Docker infrastructure ==" -ForegroundColor Cyan

if ($ClearData -and $ResetVolume) {
    Write-Warning "-ClearData is ignored when -ResetVolume is used (volume removal wipes all Postgres data)."
}

if ($ClearData -and -not $ResetVolume) {
    Clear-ResolveOpsDatabase -ScriptsRoot $PSScriptRoot
}

Stop-ResolveOpsInfra -ProjectRoot $ProjectRoot -ResetVolume:$ResetVolume

Write-Host ""
Write-Host "Done. App processes are unchanged - stop them with .\scripts\stop_apps.ps1" -ForegroundColor Green
