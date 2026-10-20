param(
    [int]$Port = 18080
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$evidenceRoot = Join-Path $env:TEMP ("voltwise-phase2a-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $evidenceRoot | Out-Null
$database = Join-Path $evidenceRoot "voltwise.db"
$stdout = Join-Path $evidenceRoot "server.out.log"
$stderr = Join-Path $evidenceRoot "server.err.log"
$baseUrl = "http://127.0.0.1:$Port"

$env:PYTHONPATH = Join-Path $repo "backend"
$env:PORT = "$Port"
$env:VOLTWISE_HOST = "127.0.0.1"
$env:VOLTWISE_DB_PATH = $database
$env:VOLTWISE_STATIC_DIR = Join-Path $repo "frontend\dist"
$env:VOLTWISE_MCP_ALLOWED_HOSTS = "127.0.0.1:*,localhost:*"
$env:VOLTWISE_MCP_ALLOWED_ORIGINS = "http://127.0.0.1:*,http://localhost:*"

function Start-SmokeServer {
    $process = Start-Process `
        -FilePath (Join-Path $repo ".venv\Scripts\python.exe") `
        -ArgumentList @("-m", "app.deployment") `
        -WorkingDirectory $repo `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -WindowStyle Hidden `
        -PassThru
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        if ($process.HasExited) {
            throw "Deployment exited early with code $($process.ExitCode): $(Get-Content $stderr -Raw)"
        }
        try {
            $health = Invoke-RestMethod -Uri "$baseUrl/health" -TimeoutSec 1
            if ($health.status -eq "ok") { return $process }
        } catch {
            Start-Sleep -Milliseconds 100
        }
    }
    throw "Timed out waiting for the combined deployment."
}

function Stop-SmokeServer([System.Diagnostics.Process]$Process) {
    if ($Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id
        $Process.WaitForExit()
    }
}

function Post-Json([string]$Path, [hashtable]$Body) {
    Invoke-RestMethod `
        -Method Post `
        -Uri ($baseUrl + $Path) `
        -ContentType "application/json" `
        -Body ($Body | ConvertTo-Json -Compress)
}

function Reset-And-Assert {
    $reset = Invoke-RestMethod -Method Post -Uri "$baseUrl/api/demo/reset"
    $overview = Invoke-RestMethod -Uri "$baseUrl/api/household/overview"
    $heater = $overview.devices | Where-Object device_id -eq "heater"
    if (
        $reset.heater_fault -ne "NONE" -or
        $reset.energy_scenario -ne "NORMAL_CURRENT_CYCLE" -or
        $heater.reported_state -ne "OFF" -or
        $heater.current_watts -ne 2
    ) {
        throw "Reset did not restore the canonical demo state."
    }
}

$process = $null
try {
    $process = Start-SmokeServer
    $index = Invoke-WebRequest -Uri "$baseUrl/" -UseBasicParsing
    if ($index.StatusCode -ne 200 -or $index.Content -notmatch '<div id="root">') {
        throw "The production frontend did not load."
    }

    & (Join-Path $repo ".venv\Scripts\python.exe") `
        (Join-Path $repo "scripts\check-mcp.py") "$baseUrl/mcp"
    if ($LASTEXITCODE -ne 0) { throw "The official MCP readiness check failed." }

    Reset-And-Assert
    Post-Json "/api/demo/device-fault" @{device = "heater"; fault = "NO_DRAW"} | Out-Null
    $noDrawVerify = Post-Json "/api/sim/chat" @{message = "Turn on the heater"}
    $noDrawDiagnostic = Post-Json "/api/sim/chat" @{message = "Diagnose the heater"}
    if (
        $noDrawVerify.result.observed_power_watts -ne 7 -or
        $noDrawDiagnostic.result.diagnostic_classification -ne "NO_ELECTRICAL_RESPONSE" -or
        $noDrawDiagnostic.result.final_status -ne "UNRESOLVED"
    ) { throw "NO_DRAW flow mismatch." }

    Reset-And-Assert
    Post-Json "/api/demo/device-fault" @{device = "heater"; fault = "NO_DRAW_THEN_RECOVER"} | Out-Null
    $recovery = Post-Json "/api/sim/chat" @{message = "Diagnose the heater"}
    $recoveryWatts = $recovery.result.attempts[-1].observed_watts
    if (
        $recovery.result.final_status -ne "RECOVERED" -or
        $recoveryWatts -ne 1500 -or
        $recovery.result.retries_used -ne 1
    ) { throw "Recovery flow mismatch." }

    Reset-And-Assert
    Post-Json "/api/demo/device-fault" @{device = "heater"; fault = "HIGH_DRAW"} | Out-Null
    $highVerify = Post-Json "/api/sim/chat" @{message = "Turn on the heater"}
    $highDiagnostic = Post-Json "/api/sim/chat" @{message = "Diagnose the heater"}
    if (
        $highVerify.result.observed_power_watts -ne 2200 -or
        $highDiagnostic.result.diagnostic_classification -ne "ABNORMAL_HIGH_DRAW" -or
        $highDiagnostic.result.final_status -ne "SAFETY_STOP" -or
        $highDiagnostic.result.retries_used -ne 0 -or
        $highDiagnostic.result.safety_action -ne "POWER_CUT_HIGH_DRAW"
    ) { throw "HIGH_DRAW safety flow mismatch." }

    Reset-And-Assert
    $energy = Post-Json "/api/sim/chat" @{message = "Why is our usage higher?"}
    $ac = $energy.result.contributors | Where-Object device_id -eq "ac"
    if (
        $energy.tool_call.name -ne "power_explain_usage_change" -or
        $ac.energy_impact_kwh -ne 15.75 -or
        $ac.energy_impact_type -ne "ESTIMATED" -or
        $energy.result.unattributed_kwh -ne 4.65
    ) { throw "Energy explanation mismatch." }

    Reset-And-Assert
    Post-Json "/api/demo/energy-scenario" @{scenario = "NEAR_THRESHOLD"} | Out-Null
    Post-Json "/api/demo/device-fault" @{device = "heater"; fault = "NO_DRAW"} | Out-Null
    Post-Json "/api/sim/chat" @{message = "Turn on the heater"} | Out-Null
    $traceCountBefore = @(Invoke-RestMethod -Uri "$baseUrl/api/sim/traces").Count
    Stop-SmokeServer $process
    $process = Start-SmokeServer
    $stateAfter = Invoke-RestMethod -Uri "$baseUrl/api/demo/state"
    $overviewAfter = Invoke-RestMethod -Uri "$baseUrl/api/household/overview"
    $heaterAfter = $overviewAfter.devices | Where-Object device_id -eq "heater"
    $traceCountAfter = @(Invoke-RestMethod -Uri "$baseUrl/api/sim/traces").Count
    if (
        $stateAfter.energy_scenario -ne "NEAR_THRESHOLD" -or
        $stateAfter.heater_fault -ne "NO_DRAW" -or
        $heaterAfter.reported_state -ne "OFF" -or
        $heaterAfter.current_watts -ne 2 -or
        $traceCountAfter -lt $traceCountBefore
    ) { throw "Persistent restart behavior mismatch." }

    Stop-SmokeServer $process
    $env:VOLTWISE_MCP_URL = "http://127.0.0.1:65534/mcp"
    $process = Start-SmokeServer
    $failedClosed = $false
    try {
        Post-Json "/api/sim/chat" @{message = "How are we doing this month?"} | Out-Null
    } catch {
        if ([int]$_.Exception.Response.StatusCode -eq 503) { $failedClosed = $true }
    }
    $failedTrace = @(Invoke-RestMethod -Uri "$baseUrl/api/sim/traces?limit=1")[0]
    if (
        -not $failedClosed -or
        $failedTrace.success -ne $false -or
        $failedTrace.result_summary -ne "MCP request failed."
    ) { throw "MCP did not fail closed." }

    [ordered]@{
        frontend_status = $index.StatusCode
        health_status = "ok"
        no_draw = "$($noDrawDiagnostic.result.diagnostic_classification)/$($noDrawDiagnostic.result.final_status)/$($noDrawVerify.result.observed_power_watts)W"
        recovery = "$($recovery.result.final_status)/${recoveryWatts}W/retries=$($recovery.result.retries_used)"
        high_draw = "$($highDiagnostic.result.diagnostic_classification)/$($highDiagnostic.result.final_status)/$($highVerify.result.observed_power_watts)W/retries=$($highDiagnostic.result.retries_used)/$($highDiagnostic.result.safety_action)"
        energy = "AC=$($ac.energy_impact_kwh)kWh/$($ac.energy_impact_type); unattributed=$($energy.result.unattributed_kwh)kWh"
        restart = "scenario=$($stateAfter.energy_scenario); fault=$($stateAfter.heater_fault); heater=$($heaterAfter.reported_state)/$($heaterAfter.current_watts)W; traces=$traceCountBefore->$traceCountAfter"
        mcp_unavailable = "HTTP503=$failedClosed; trace_success=$($failedTrace.success)"
        temp_evidence = $evidenceRoot
    } | ConvertTo-Json
} finally {
    Stop-SmokeServer $process
}
