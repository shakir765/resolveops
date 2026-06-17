param(
    [switch]$DockerOnly
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot/..

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

Write-Host "Starting infrastructure..."
docker compose up -d postgres redis rabbitmq

if ($DockerOnly) { exit 0 }

Write-Host "Seeding knowledge base..."
python scripts/seed_kb.py

Write-Host "Start services in separate terminals:"
Write-Host "  uvicorn services.rag_service.main:app --port 8002 --reload"
Write-Host "  uvicorn services.tool_runner.main:app --port 8003 --reload"
Write-Host "  uvicorn services.api.main:app --port 8000 --reload"
Write-Host "  python -m services.graph_worker.main"
