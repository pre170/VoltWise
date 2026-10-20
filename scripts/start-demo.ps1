param([switch]$NoBrowser)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$frontendRoot = Join-Path $projectRoot "frontend"
$viteEntry = Join-Path $frontendRoot "node_modules\vite\bin\vite.js"
$mcpCheck = Join-Path $PSScriptRoot "check-mcp.py"
$runtimeDir = Join-Path $projectRoot ".voltwise-run"
$pidFile = Join-Path $runtimeDir "pids.json"
$started = @()

function Assert-Port-Free([int]$Port) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue
    if ($listener) {
        throw "Port $Port is already in use by PID $($listener[0].OwningProcess). Stop the existing service first."
    }
}

function Wait-ProcessPort([System.Diagnostics.Process]$Process, [int]$Port, [string]$Name) {
    $deadline = (Get-Date).AddSeconds(15)
    do {
        if ($Process.HasExited) { throw "$Name exited before opening port $Port." }
        # Virtual-environment launchers may hand off to a child Python process,
        # so the listener PID is resolved after the port appears.
        if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) { return }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    throw "$Name did not open port $Port within 15 seconds."
}

function Resolve-ListenerProcess([int]$Port) {
    $listener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop | Select-Object -First 1
    $process = Get-Process -Id $listener.OwningProcess -ErrorAction Stop
    if (-not ($script:started | Where-Object { $_.Id -eq $process.Id })) {
        $script:started += $process
    }
    return $process
}

function Wait-Http([System.Diagnostics.Process]$Process, [string]$Url, [string]$Name) {
    $deadline = (Get-Date).AddSeconds(15)
    do {
        if ($Process.HasExited) { throw "$Name exited before becoming healthy." }
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) { return }
        } catch { }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    throw "$Name did not become healthy at $Url within 15 seconds."
}

function Start-LoggedProcess([string]$Name, [string]$FilePath, [string[]]$Arguments, [string]$WorkingDirectory) {
    $stdout = Join-Path $runtimeDir "$Name.out.log"
    $stderr = Join-Path $runtimeDir "$Name.err.log"
    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
    $script:started += $process
    return $process
}

try {
    if (-not (Test-Path -LiteralPath $python)) {
        throw "Python environment missing. Run: py -3.12 -m venv .venv; .\.venv\Scripts\python -m pip install -e '.[dev]'"
    }
    $node = (Get-Command node.exe -ErrorAction Stop).Source
    if (-not (Test-Path -LiteralPath $viteEntry)) {
        throw "Frontend dependencies missing. Run: cd frontend; npm.cmd ci"
    }
    foreach ($port in 8001, 8000, 5173) { Assert-Port-Free $port }
    New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null

    $env:VOLTWISE_DB_PATH = Join-Path $projectRoot "data\voltwise.db"
    $env:VOLTWISE_MCP_PORT = "8001"
    $env:VOLTWISE_MCP_URL = "http://127.0.0.1:8001/mcp"

    Write-Output "[VoltWise] Starting real MCP Streamable HTTP server on 127.0.0.1:8001..."
    $mcp = Start-LoggedProcess "mcp" $python @("-m", "uvicorn", "app.mcp.http:create_mcp_http_app", "--factory", "--host", "127.0.0.1", "--port", "8001") $projectRoot
    Wait-ProcessPort $mcp 8001 "MCP server"
    $mcp = Resolve-ListenerProcess 8001
    & $python $mcpCheck "http://127.0.0.1:8001/mcp"
    if ($LASTEXITCODE -ne 0) {
        throw "MCP server failed the official-client readiness check. Review .voltwise-run\mcp.err.log."
    }

    Write-Output "[VoltWise] Starting REST API and simulator gateway on 127.0.0.1:8000..."
    $api = Start-LoggedProcess "api" $python @("-m", "uvicorn", "app.api.app:app", "--host", "127.0.0.1", "--port", "8000") $projectRoot
    Wait-ProcessPort $api 8000 "REST API"
    $api = Resolve-ListenerProcess 8000
    Wait-Http $api "http://127.0.0.1:8000/api/health" "REST API"

    Write-Output "[VoltWise] Starting frontend on 127.0.0.1:5173..."
    $web = Start-LoggedProcess "web" $node @("`"$viteEntry`"", "--host", "127.0.0.1") $frontendRoot
    Wait-ProcessPort $web 5173 "Frontend"
    $web = Resolve-ListenerProcess 5173
    Wait-Http $web "http://127.0.0.1:5173" "Frontend"

    # Reset only after all three required services are healthy. This writes a
    # reset generation that the separate MCP process adopts on its next call.
    $state = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/demo/reset" -TimeoutSec 5
    @{
        project_root = $projectRoot
        started_at = (Get-Date).ToString("o")
        mcp = $mcp.Id
        api = $api.Id
        web = $web.Id
    } | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8

    Write-Output "[VoltWise] Ready: fault=$($state.heater_fault), scenario=$($state.energy_scenario)"
    Write-Output "[VoltWise] UI http://127.0.0.1:5173 | API http://127.0.0.1:8000/docs | MCP http://127.0.0.1:8001/mcp"
    if (-not $NoBrowser) { Start-Process "http://127.0.0.1:5173" }
} catch {
    foreach ($process in ($started | Sort-Object StartTime -Descending)) {
        if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue }
    }
    Write-Error $_
    exit 1
}
