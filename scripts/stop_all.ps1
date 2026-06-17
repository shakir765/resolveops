# ResolveOps — stop Docker infrastructure (+ optional data wipe).
# App processes must be stopped separately unless already closed.
#
# Usage:
#   .\scripts\stop_all.ps1                  # stop infra containers (data preserved)
#   .\scripts\stop_all.ps1 -ClearData       # truncate app tables, then stop infra
#   .\scripts\stop_all.ps1 -ResetVolume     # remove infra containers + named volumes

param(
    [switch]$ClearData,
    [switch]$ResetVolume
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

& (Join-Path $PSScriptRoot "stop_docker.ps1") -ClearData:$ClearData -ResetVolume:$ResetVolume

Write-Host "Close any open API/RAG/Tool/Worker terminal windows manually, or run .\scripts\stop_apps.ps1" -ForegroundColor Green
