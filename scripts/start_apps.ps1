# Start ResolveOps app services only (API, RAG, Tool Runner, Graph Worker).
# Does NOT start Docker (postgres, redis, rabbitmq).
#
# Usage:
#   .\scripts\start_apps.ps1              # new terminal window per service (with --reload)
#   .\scripts\start_apps.ps1 -Background  # background + logs + PID file (recommended)

param(
    [switch]$Background
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot

$RunDir = Join-Path $ProjectRoot ".run"
$LogDir = Join-Path $RunDir "logs"
$PidFile = Join-Path $RunDir "apps.pids.json"
New-Item -ItemType Directory -Force -Path $RunDir, $LogDir | Out-Null

$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) { $python = $pythonCmd.Source }
}
if (-not $python) {
    Write-Error "Python not found. Create venv: python -m venv .venv; pip install -e .[dev]"
}

function Get-UvicornArgs {
    param([string]$Module, [int]$Port, [switch]$UseReload)
    $args = @("-m", "uvicorn", $Module, "--host", "127.0.0.1", "--port", "$Port")
    if ($UseReload) { $args += "--reload" }
    return $args
}

$services = @(
    @{
        Name = "rag"
        Title = "RAG :8002"
        Port = 8002
        HealthUrl = "http://127.0.0.1:8002/health"
        Args = Get-UvicornArgs -Module "services.rag_service.main:app" -Port 8002 -UseReload:(-not $Background)
    },
    @{
        Name = "tool_runner"
        Title = "Tool Runner :8003"
        Port = 8003
        HealthUrl = "http://127.0.0.1:8003/health"
        Args = Get-UvicornArgs -Module "services.tool_runner.main:app" -Port 8003 -UseReload:(-not $Background)
    },
    @{
        Name = "api"
        Title = "API :8000"
        Port = 8000
        HealthUrl = "http://127.0.0.1:8000/health"
        Args = Get-UvicornArgs -Module "services.api.main:app" -Port 8000 -UseReload:(-not $Background)
    },
    @{
        Name = "graph_worker"
        Title = "Graph Worker"
        Port = $null
        HealthUrl = $null
        Args = @("-m", "services.graph_worker.main")
    }
)

function Test-PortInUse {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) { return $true }
    return [bool](netstat -ano | Select-String "LISTENING" | Select-String ":$Port\s")
}

function Wait-ForService {
    param(
        [string]$Name,
        [int]$Port,
        [string]$HealthUrl,
        [int]$TimeoutSeconds = 30
    )

    if (-not $Port) {
        Start-Sleep -Seconds 2
        return $true
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortInUse -Port $Port) {
            if ($HealthUrl) {
                try {
                    $resp = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 3
                    if ($resp.StatusCode -eq 200) { return $true }
                } catch {
                    # Port open but not ready yet
                }
            } else {
                return $true
            }
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Start-InTerminal {
    param(
        [string]$Name,
        [string]$Title,
        [string[]]$ServiceArgs
    )

    $launcher = Join-Path $RunDir "start-$Name.ps1"
    $activate = Join-Path $ProjectRoot ".venv\Scripts\Activate.ps1"
    $argText = ($ServiceArgs | ForEach-Object {
            if ($_ -match '[\s''"]') { "'$($_ -replace "'", "''")'" } else { $_ }
        }) -join ' '

    @"
`$ErrorActionPreference = "Continue"
Set-Location "$ProjectRoot"
if (Test-Path "$activate") { . "$activate" }
Write-Host "[$Title]" -ForegroundColor Green
Write-Host "Command: $python $argText" -ForegroundColor DarkGray
& "$python" $argText
Write-Host ""
Write-Host "Process exited. Press Enter to close." -ForegroundColor Yellow
Read-Host
"@ | Set-Content -Path $launcher -Encoding UTF8

    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $launcher
}

Write-Host "== ResolveOps: starting app services ==" -ForegroundColor Cyan
if (-not $Background) {
    Write-Host "Mode: separate terminal windows (look for 4 new PowerShell windows)" -ForegroundColor DarkGray
} else {
    Write-Host "Mode: background (logs in .run/logs/)" -ForegroundColor DarkGray
}

$pids = @{}
$results = @()

foreach ($svc in $services) {
    if ($svc.Port -and (Test-PortInUse -Port $svc.Port)) {
        Write-Warning "Port $($svc.Port) already in use ($($svc.Title)). Skipping - run stop_apps.ps1 first."
        $results += [pscustomobject]@{ Service = $svc.Title; Status = "SKIPPED (port in use)"; Log = "" }
        continue
    }

    if ($Background) {
        $outLog = Join-Path $LogDir "$($svc.Name).log"
        $errLog = Join-Path $LogDir "$($svc.Name).err.log"
        if (Test-Path $outLog) { Remove-Item $outLog -Force -ErrorAction SilentlyContinue }
        if (Test-Path $errLog) { Remove-Item $errLog -Force -ErrorAction SilentlyContinue }

        $proc = Start-Process `
            -FilePath $python `
            -ArgumentList $svc.Args `
            -WorkingDirectory $ProjectRoot `
            -RedirectStandardOutput $outLog `
            -RedirectStandardError $errLog `
            -PassThru `
            -WindowStyle Hidden

        $pids[$svc.Name] = @{
            pid = $proc.Id
            title = $svc.Title
            port = $svc.Port
        }
        Write-Host "  Launching $($svc.Title) (PID $($proc.Id))..." -ForegroundColor DarkGray

        $ok = Wait-ForService -Name $svc.Name -Port $svc.Port -HealthUrl $svc.HealthUrl
        if ($ok) {
            Write-Host "  OK: $($svc.Title)" -ForegroundColor Green
            $results += [pscustomobject]@{ Service = $svc.Title; Status = "RUNNING"; Log = $outLog }
        } else {
            Write-Host "  FAILED: $($svc.Title) did not become ready" -ForegroundColor Red
            $results += [pscustomobject]@{ Service = $svc.Title; Status = "FAILED"; Log = $outLog }
            if (Test-Path $errLog) {
                $tail = Get-Content $errLog -Tail 8 -ErrorAction SilentlyContinue
                if ($tail) {
                    Write-Host "  --- stderr tail ---" -ForegroundColor DarkRed
                    $tail | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkRed }
                }
            }
        }
    } else {
        Start-InTerminal -Name $svc.Name -Title $svc.Title -ServiceArgs $svc.Args
        Write-Host "  Opened terminal: $($svc.Title)" -ForegroundColor Green
        $results += [pscustomobject]@{ Service = $svc.Title; Status = "TERMINAL"; Log = (Join-Path $RunDir "start-$($svc.Name).ps1") }
    }

    Start-Sleep -Milliseconds 400
}

if ($Background) {
    $pids | ConvertTo-Json -Depth 3 | Set-Content -Path $PidFile -Encoding UTF8
    Write-Host ""
    Write-Host "PIDs saved to $PidFile"
}

Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
$results | Format-Table -AutoSize

Write-Host "Endpoints:" -ForegroundColor Green
Write-Host "  API:          http://localhost:8000/docs"
Write-Host "  RAG:          http://localhost:8002/health"
Write-Host "  Tool Runner:  http://localhost:8003/health"
Write-Host "  Graph Worker: (no HTTP port - consumes RabbitMQ)"
Write-Host ""

if ($Background) {
    Write-Host "Logs:  $LogDir"
    Write-Host "Stop:  .\scripts\stop_apps.ps1"
} else {
    Write-Host "If a window closes immediately, check launcher scripts in the .run folder."
    Write-Host "Recommended: .\scripts\start_apps.ps1 -Background"
    Write-Host "Stop:  .\scripts\stop_apps.ps1"
}

if (-not (Test-PortInUse -Port 8000) -and -not $Background) {
    Write-Host ""
    Write-Host "Port 8000 is not listening yet. Wait a few seconds or check the API terminal window for errors." -ForegroundColor Yellow
    Write-Host "Ensure Docker is up: docker compose up -d postgres redis rabbitmq" -ForegroundColor Yellow
}
