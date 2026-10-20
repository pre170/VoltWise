$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $projectRoot ".voltwise-run\pids.json"

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Output "[VoltWise] No launcher PID file found; nothing was stopped."
    exit 0
}

$record = Get-Content -Raw -LiteralPath $pidFile | ConvertFrom-Json
if ([string]$record.project_root -ne $projectRoot) {
    throw "PID file belongs to a different project root; refusing to stop processes."
}
$services = @(
    @{ id = [int]$record.web; port = 5173; command = "*vite*" },
    @{ id = [int]$record.api; port = 8000; command = "*app.api.app:app*" },
    @{ id = [int]$record.mcp; port = 8001; command = "*app.mcp.http:create_mcp_http_app*" }
)
$stopped = 0
foreach ($service in $services) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($service.id)" -ErrorAction SilentlyContinue
    if (-not $process) { continue }
    $listener = Get-NetTCPConnection -State Listen -LocalPort $service.port -OwningProcess $service.id -ErrorAction SilentlyContinue
    if (-not $listener -or $process.CommandLine -notlike $service.command) {
        throw "PID $($service.id) no longer matches the launched service on port $($service.port); refusing to stop it."
    }
    Stop-Process -Id $service.id -Force -ErrorAction Stop
    $stopped++
}
Remove-Item -LiteralPath $pidFile -Force
Write-Output "[VoltWise] Stopped $stopped local demo process(es)."
