$ErrorActionPreference = "Stop"
try {
    $state = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/demo/reset" -TimeoutSec 5
    Write-Output "[VoltWise] Reset complete: fault=$($state.heater_fault), scenario=$($state.energy_scenario), simulated_at=$($state.simulated_at)"
} catch {
    Write-Error "VoltWise API is not available at http://127.0.0.1:8000. Start the demo first."
    exit 1
}
