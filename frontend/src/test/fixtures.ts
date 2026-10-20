import type { DiagnosticResult } from "../types/api";

export const overview = {
  simulated_at: "2026-09-15T00:00:00", energy_scenario: "NORMAL_CURRENT_CYCLE",
  current_cycle_kwh: 142, previous_equivalent_kwh: 118, change_percent: 20.34,
  projected_month_end_kwh: 304.29, tariff_warning: "PROJECTED_TO_CROSS",
  current_estimated_energy_charge: "489.00", projected_estimated_energy_charge: "1384.32",
  devices: [
    { device_id: "ac", name: "Air Conditioner", device_type: "AIR_CONDITIONER", reported_state: "OFF", physical_state: null, available: true, capabilities: { supports_control: true, supports_state_history: true, supports_runtime: true, supports_device_power: false, supports_device_energy: false, has_estimated_cycle_energy: false }, current_watts: null, current_runtime_hours: 73, simulation_only_fields: [] },
    { device_id: "heater", name: "Living Room Heater", device_type: "HEATER", reported_state: "OFF", physical_state: "OFF", available: true, capabilities: { supports_control: true, supports_state_history: true, supports_runtime: true, supports_device_power: true, supports_device_energy: true, has_estimated_cycle_energy: false }, current_watts: 2, current_runtime_hours: 5, electrical_profile: { expected_running_watts: 1500, abnormal_high_draw_threshold: 1900 }, simulation_only_fields: ["physical_state"] },
    { device_id: "refrigerator", name: "Refrigerator", device_type: "REFRIGERATOR", reported_state: "OFF", physical_state: null, available: true, capabilities: { supports_control: false, supports_state_history: true, supports_runtime: true, supports_device_power: true, supports_device_energy: true, has_estimated_cycle_energy: false }, current_watts: null, current_runtime_hours: 112, simulation_only_fields: [] },
    { device_id: "tv", name: "TV", device_type: "TELEVISION", reported_state: "OFF", physical_state: null, available: true, capabilities: { supports_control: false, supports_state_history: true, supports_runtime: true, supports_device_power: false, supports_device_energy: false, has_estimated_cycle_energy: false }, current_watts: null, current_runtime_hours: 44, simulation_only_fields: [] },
    { device_id: "dishwasher", name: "Dishwasher", device_type: "DISHWASHER", reported_state: "OFF", physical_state: null, available: true, capabilities: { supports_control: true, supports_state_history: true, supports_runtime: true, supports_device_power: false, supports_device_energy: false, has_estimated_cycle_energy: true }, current_watts: null, current_runtime_hours: 9, simulation_only_fields: [] },
  ],
};

export const comparison = {
  current_kwh: 142, previous_equivalent_kwh: 118, difference_kwh: 24, change_percent: 20.34,
  elapsed_days: 14, projection: { projected_kwh: 304.29, method: "RUN_RATE", days_elapsed: 14, cycle_days: 30 },
  evidence_source: "WHOLE_HOME_METER", speakable_summary: "You've used about 142 kilowatt-hours, compared with 118.",
};

export const explanation = {
  household_change_kwh: 24, household_change_percent: 20.34,
  contributors: [
    { device_id: "ac", device: "Air Conditioner", reason: "RUNTIME_INCREASE", current_runtime_hours: 73, previous_runtime_hours: 52, runtime_change_hours: 21, runtime_change_percent: 40.38, energy_impact_kwh: 15.75, energy_impact_type: "ESTIMATED", evidence_source: "DEVICE_STATE_HISTORY", confidence: "HIGH" },
  ],
  known_contribution_kwh: 19.35, unattributed_kwh: 4.65, attribution_overage_kwh: 0, limitations: ["Device attribution is incomplete."],
  speakable_summary: "Your air conditioner is the strongest observed contributor.",
};

export const tariff = {
  tariff_id: "ILLUSTRATIVE_DEMO_TARIFF", tariff_name: "Illustrative tariff", tariff_type: "TELESCOPIC", currency: "INR", source: "demo", is_demo: true,
  current_usage_kwh: "142.000", current_slab: "100_TO_200_KWH", current_estimated_energy_charge: "489.00", next_threshold_kwh: "200", units_until_next_threshold: "58.000", current_marginal_rate: "4.50", next_marginal_rate: "6.00",
  projected_month_end_kwh: "304.290", projected_slab: "ABOVE_300_KWH", projected_estimated_energy_charge: "1384.32", expected_threshold_crossings: [], threshold_warning: "PROJECTED_TO_CROSS",
  speakable_summary: "You're projected to cross the 300 kilowatt-hour threshold.",
};

export const target = {
  target_kwh: "300.000", target_status: "UNLIKELY", current_usage_kwh: "296.000", projected_usage_kwh: "328.000", remaining_kwh_budget: "4.000", remaining_days: "5.000", required_average_daily_kwh: "0.80", current_daily_run_rate_kwh: "10.14",
  recommendations: [{ rank: 1, action: "Reduce unnecessary air-conditioner runtime.", reason: "Observed AC runtime increased by 21 hours.", evidence_source: "DEVICE_STATE_HISTORY", estimated_reduction_kwh: "1.500", impact_type: "ESTIMATED" }],
  speakable_summary: "Staying under 300 is achievable with a modest reduction.",
};

export const verification = {
  device: "heater", command: "ON", reported_state: "ON", verification: "FAILED", expected_power_watts: 1500, observed_power_delta_watts: 5, observed_power_watts: 7, confidence: .92, confidence_level: "HIGH", evidence_source: "DEVICE_LEVEL_POWER", telemetry_available: true, diagnostic_classification: "NO_ELECTRICAL_RESPONSE", reason: "No expected electrical response detected.", speakable_summary: "The heater reports on, but I cannot verify normal electrical operation.",
};

export function diagnostic(final_status = "UNRESOLVED"): DiagnosticResult {
  const recovered = final_status === "RECOVERED";
  const safety = final_status === "SAFETY_STOP";
  const attempt = (number: number, verified = false) => ({ attempt: number, reported_state: "ON", available: true, baseline_watts: number === 1 ? 2 : 7, power_samples_watts: [verified ? 1500 : safety ? 2200 : 7], observed_watts: verified ? 1500 : safety ? 2200 : 7, observed_power_delta_watts: verified ? 1493 : 5, verification: verified ? "VERIFIED" : "FAILED", diagnostic_classification: verified ? "OK" : safety ? "ABNORMAL_HIGH_DRAW" : "NO_ELECTRICAL_RESPONSE", confidence: .92, evidence: [] });
  return { device: "heater", requested_action: "ON", final_status, initial_verification: "FAILED", diagnostic_classification: safety ? "ABNORMAL_HIGH_DRAW" : recovered ? "OK" : "NO_ELECTRICAL_RESPONSE", confidence: .92, attempts: safety ? [attempt(1)] : [attempt(1), attempt(2, recovered)], retries_used: safety ? 0 : 1, safety_action: safety ? "POWER_CUT_HIGH_DRAW" : recovered ? "NONE" : "STOP_RETRYING", resolved: recovered, evidence: [], speakable_summary: `Diagnostic finished: ${final_status}.` };
}

export const demoState = { mode: "SIMULATION", energy_scenario: "NORMAL_CURRENT_CYCLE", heater_fault: "NONE", simulated_at: "2026-09-15T00:00:00" };
export const events = [{ event_id: 1, timestamp: "2026-10-05T10:00:00Z", event_type: "DEVICE_COMMAND", device_id: "heater", action: "COMMAND_SENT", outcome: "SENT", details: {} }];

export const trace = {
  trace_id: "trace-1", timestamp: "2026-10-05T10:00:01Z", transport: "STREAMABLE_HTTP" as const,
  protocol_version: "2025-11-25", intent: "ENERGY_COMPARISON", tool_name: "power_compare_periods",
  tool_arguments: {}, result_summary: comparison.speakable_summary, duration_ms: 84.2, success: true, error: null,
};
