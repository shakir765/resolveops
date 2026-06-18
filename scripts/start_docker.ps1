# ResolveOps - start Docker infrastructure only (postgres, redis, rabbitmq).
# Does NOT start API, RAG, Tool Runner, or Graph Worker.
#
# Usage:
#   .\scripts\start_docker.ps1           # start infra containers
#   .\scripts\start_docker.ps1 -SeedKb    # start infra + seed knowledge base (same as start_all step 1-2)

param(
    [switch]$SeedKb
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

. (Join-Path $PSScriptRoot "docker_infra.ps1")

Write-Host "== ResolveOps: starting Docker infrastructure ==" -ForegroundColor Cyan

Ensure-ResolveOpsEnvFile -ProjectRoot $ProjectRoot
Start-ResolveOpsInfra

if ($SeedKb) {
    Write-Host ""
    Invoke-SeedKnowledgeBase -ProjectRoot $ProjectRoot
}

Write-Host ""
Write-Host "Done. Start apps: .\scripts\start_apps.ps1 -Background" -ForegroundColor Green
