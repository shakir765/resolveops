# Stop ResolveOps app services (API, RAG, Tool Runner, Graph Worker, Portal).
# Does NOT stop Docker infrastructure.
#
# Usage: .\scripts\stop_apps.ps1

$ErrorActionPreference = "Continue"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$PidFile = Join-Path $ProjectRoot ".run\apps.pids.json"

Write-Host "== ResolveOps: stopping app services ==" -ForegroundColor Cyan

function Stop-ProcessTree {
    param([int]$ProcessId, [string]$Label)
    if (-not $ProcessId -or $ProcessId -le 4) { return $false }
    $proc = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $proc) { return $false }
    & taskkill.exe /PID $ProcessId /T /F 2>$null | Out-Null
    Write-Host "  Stopped $Label (PID $ProcessId, process tree)" -ForegroundColor Yellow
    return $true
}

function Get-PythonProcesses {
    @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue)
}

function Stop-MatchingPython {
    param([scriptblock]$MatchFilter, [string]$Label)
    $stopped = 0
    foreach ($proc in (Get-PythonProcesses | Where-Object $MatchFilter)) {
        if (Stop-ProcessTree -ProcessId $proc.ProcessId -Label $Label) {
            $stopped++
        }
    }
    return $stopped
}

function Stop-UvicornProcesses {
    $procs = @(Get-PythonProcesses | Where-Object {
            $_.CommandLine -like "*uvicorn*services.api.main*" -or
            $_.CommandLine -like "*uvicorn*services.rag_service.main*" -or
            $_.CommandLine -like "*uvicorn*services.tool_runner.main*"
        })

    if ($procs.Count -eq 0) { return 0 }

    # With --reload, kill reloader parents first or the worker respawns immediately.
    $reloaders = foreach ($p in $procs) {
        if ($procs | Where-Object { $_.ParentProcessId -eq $p.ProcessId }) { $p }
    }

    $stopped = 0
    foreach ($p in $reloaders) {
        if (Stop-ProcessTree -ProcessId $p.ProcessId -Label "uvicorn reloader") { $stopped++ }
    }

    Start-Sleep -Milliseconds 300

    foreach ($p in (Get-PythonProcesses | Where-Object {
            $_.CommandLine -like "*uvicorn*services.api.main*" -or
            $_.CommandLine -like "*uvicorn*services.rag_service.main*" -or
            $_.CommandLine -like "*uvicorn*services.tool_runner.main*"
        })) {
        if (Stop-ProcessTree -ProcessId $p.ProcessId -Label "uvicorn") { $stopped++ }
    }

    return $stopped
}

function Stop-PortListener {
    param([int]$Port, [string]$Label)
    $stopped = $false
    $pids = @(
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )

    if ($pids.Count -eq 0) {
        $lines = netstat -ano | Select-String "LISTENING" | Select-String ":$Port\s"
        foreach ($line in $lines) {
            if ($line -match '\s(\d+)\s*$') {
                $pids += [int]$matches[1]
            }
        }
        $pids = $pids | Select-Object -Unique
    }

    foreach ($processId in $pids) {
        if ($processId -le 4) { continue }
        if (Stop-ProcessTree -ProcessId $processId -Label "$Label on port $Port") {
            $stopped = $true
        }
    }
    return $stopped
}

function Test-PortListening {
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) { return $true }
    return [bool](netstat -ano | Select-String "LISTENING" | Select-String ":$Port\s")
}

# 1) Stop processes from PID file (background mode)
if (Test-Path $PidFile) {
    Write-Host "Stopping background processes from PID file..."
    $saved = Get-Content $PidFile -Raw | ConvertFrom-Json
    foreach ($prop in $saved.PSObject.Properties) {
        $entry = $prop.Value
        Stop-ProcessTree -ProcessId ([int]$entry.pid) -Label $entry.title | Out-Null
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
}

# 2) Stop uvicorn reloaders/workers by command line (before port kill - avoids respawn)
Write-Host "Stopping uvicorn services..."
$uvicornStopped = Stop-UvicornProcesses
if ($uvicornStopped -eq 0) {
    Write-Host "  No uvicorn processes found." -ForegroundColor DarkGray
}

# 3) Stop graph worker
Write-Host "Stopping Graph Worker processes..."
$workerStopped = Stop-MatchingPython -MatchFilter { $_.CommandLine -like "*services.graph_worker.main*" } -Label "Graph Worker"
if ($workerStopped -eq 0) {
    Write-Host "  No graph worker processes found." -ForegroundColor DarkGray
}

# 3b) Stop portal (Vite / Node)
Write-Host "Stopping Portal processes..."
$nodeStopped = 0
foreach ($proc in @(Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" -ErrorAction SilentlyContinue)) {
    if ($proc.CommandLine -like "*vite*" -or $proc.CommandLine -like "*portal*") {
        if (Stop-ProcessTree -ProcessId $proc.ProcessId -Label "Portal (Vite)") {
            $nodeStopped++
        }
    }
}
if ($nodeStopped -eq 0) {
    Write-Host "  No portal processes found." -ForegroundColor DarkGray
}

# 4) Cleanup anything still listening on app ports
Write-Host "Cleaning up listeners on ports 8000, 8002, 8003, 5173..."
Stop-PortListener -Port 8000 -Label "API" | Out-Null
Stop-PortListener -Port 8002 -Label "RAG" | Out-Null
Stop-PortListener -Port 8003 -Label "Tool Runner" | Out-Null
Stop-PortListener -Port 5173 -Label "Portal" | Out-Null

Start-Sleep -Milliseconds 500

# 5) Verify
$stillListening = @()
foreach ($port in @(8000, 8002, 8003, 5173)) {
    if (Test-PortListening -Port $port) { $stillListening += $port }
}

Write-Host ""
if ($stillListening.Count -gt 0) {
    Write-Host "Warning: ports still in use: $($stillListening -join ', ')" -ForegroundColor Red
    Write-Host "Close any remaining ResolveOps terminal windows manually, then run stop_apps.ps1 again."
    Write-Host "Or find the PID: netstat -ano | findstr :8000"
} else {
    Write-Host "All app ports are free." -ForegroundColor Green
}

Write-Host ""
Write-Host "Done. Docker infra is still running." -ForegroundColor Green
Write-Host "Start apps:  .\scripts\start_apps.ps1 -Background"
Write-Host "Stop infra:  .\scripts\stop_docker.ps1"
