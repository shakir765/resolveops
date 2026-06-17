# Shared Docker infrastructure helpers (postgres, redis, rabbitmq).

$script:InfraServices = @("postgres", "redis", "rabbitmq")
$script:PostgresUser = "resolveops"
$script:PostgresDb = "resolveops"

function Get-ComposeProjectName {
    param([string]$ProjectRoot)
    (Split-Path $ProjectRoot -Leaf).ToLower()
}

function Ensure-ResolveOpsEnvFile {
    param([string]$ProjectRoot)
    $envFile = Join-Path $ProjectRoot ".env"
    if (-not (Test-Path $envFile)) {
        Copy-Item (Join-Path $ProjectRoot ".env.example") $envFile
        Write-Host "Created .env from .env.example"
    }
}

function Test-PostgresRunning {
    $line = docker compose ps postgres --format json 2>$null | Select-Object -First 1
    if (-not $line) { return $false }
    $info = $line | ConvertFrom-Json
    return $info.State -eq "running"
}

function Wait-PostgresHealthy {
    param([int]$TimeoutSeconds = 60)
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        $line = docker compose ps postgres --format json 2>$null | Select-Object -First 1
        if ($line) {
            $info = $line | ConvertFrom-Json
            if ($info.State -eq "running" -and $info.Health -eq "healthy") {
                return $true
            }
        }
        Start-Sleep -Seconds 2
        $elapsed += 2
    }
    return $false
}

function Wait-InfraHealthy {
    param([int]$TimeoutSeconds = 60)
    Write-Host "Waiting for containers to be healthy..."
    $elapsed = 0
    while ($elapsed -lt $TimeoutSeconds) {
        $lines = docker compose ps --format json 2>$null
        if ($lines) {
            $ps = $lines | ForEach-Object { $_ | ConvertFrom-Json }
            $healthy = @($ps | Where-Object {
                    $script:InfraServices -contains $_.Service -and $_.Health -eq "healthy"
                }).Count
            if ($healthy -ge $script:InfraServices.Count) { return $true }
        }
        Start-Sleep -Seconds 2
        $elapsed += 2
    }
    return $false
}

function Start-ResolveOpsInfra {
    Write-Host "Starting Docker ($($script:InfraServices -join ', '))..." -ForegroundColor Yellow
    docker compose up -d @script:InfraServices
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose up failed."
    }

    if (-not (Wait-InfraHealthy)) {
        Write-Warning "Not all infra containers reported healthy within 60 seconds."
    }

    docker compose ps @script:InfraServices
}

function Clear-ResolveOpsDatabase {
    param([string]$ScriptsRoot)

    $clearSqlFile = Join-Path $ScriptsRoot "clear_db.sql"
    if (-not (Test-Path $clearSqlFile)) {
        throw "Missing SQL script: $clearSqlFile"
    }

    if (-not (Test-PostgresRunning)) {
        Write-Host "Postgres is not running. Starting it temporarily to clear data..." -ForegroundColor Yellow
        docker compose up -d postgres
        if (-not (Wait-PostgresHealthy)) {
            throw "Postgres did not become healthy within 60 seconds."
        }
    }

    Write-Host "Clearing ResolveOps tables (tickets, workflow_runs, workflow_events, idempotency_keys)..." -ForegroundColor Yellow
    Get-Content $clearSqlFile -Raw | docker compose exec -T postgres psql -U $script:PostgresUser -d $script:PostgresDb -v ON_ERROR_STOP=1
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to clear database tables."
    }
    Write-Host "Database tables cleared." -ForegroundColor Green
}

function Invoke-SeedKnowledgeBase {
    param([string]$ProjectRoot)

    Write-Host "Seeding knowledge base..." -ForegroundColor Yellow
    $python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCmd) { $python = $pythonCmd.Source }
    }
    if (-not $python) {
        Write-Warning "Python not found. Skipping seed_kb.py. Run: python -m venv .venv; pip install -e .[dev]"
        return
    }
    & $python (Join-Path $ProjectRoot "scripts\seed_kb.py")
}

function Stop-ResolveOpsInfra {
    param(
        [string]$ProjectRoot,
        [switch]$ResetVolume
    )

    Write-Host "Stopping Docker infra ($($script:InfraServices -join ', '))..." -ForegroundColor Yellow
    docker compose stop @script:InfraServices
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose stop failed."
    }

    if ($ResetVolume) {
        Write-Host "Removing infra containers and named volumes (postgres_data, chroma_data)..." -ForegroundColor Yellow
        docker compose rm -f @script:InfraServices | Out-Null

        $projectName = Get-ComposeProjectName -ProjectRoot $ProjectRoot
        foreach ($volume in @("postgres_data", "chroma_data")) {
            $volumeName = "${projectName}_${volume}"
            docker volume rm $volumeName -f 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  Removed volume $volumeName" -ForegroundColor DarkGray
            }
        }
    }
}
