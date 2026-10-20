export type Health = { status: string; service: string; mode: string };

export type DeviceCapabilities = {
  supports_control: boolean;
  supports_state_history: boolean;
  supports_runtime: boolean;
  supports_device_power: boolean;
  supports_device_energy: boolean;
  has_estimated_cycle_energy: boolean;
};

export type DeviceView = {
  device_id: string;
  name: string;
  device_type: string;
  reported_state: string | null;
  physical_state: string | null;
  available: boolean;
  capabilities: DeviceCapabilities;
  current_watts: number | null;
  current_runtime_hours: number | null;
  electrical_profile?: {
    expected_running_watts: number;
    abnormal_high_draw_threshold: number;
  } | null;
  simulation_only_fields: string[];
};

export type HouseholdOverview = {
  simulated_at: string;
  energy_scenario: string;
  current_cycle_kwh: number;
  previous_equivalent_kwh: number;
  change_percent: number | null;
  projected_month_end_kwh: number;
  tariff_warning: string;
  current_estimated_energy_charge: string;
  projected_estimated_energy_charge: string;
  devices: DeviceView[];
};

export type Projection = {
  projected_kwh: number;
  method: string;
  days_elapsed: number;
  cycle_days: number;
};

export type EnergyComparison = {
  current_kwh: number;
  previous_equivalent_kwh: number;
  difference_kwh: number;
  change_percent: number | null;
  elapsed_days: number;
  projection: Projection;
  evidence_source: string;
  speakable_summary: string;
};

export type Contributor = {
  device_id: string;
  device: string;
  reason: string;
  current_runtime_hours: number;
  previous_runtime_hours: number;
  runtime_change_hours: number;
  runtime_change_percent: number | null;
  energy_impact_kwh: number;
  energy_impact_type: string;
  evidence_source: string;
  confidence: string;
};

export type UsageExplanation = {
  household_change_kwh: number;
  household_change_percent: number | null;
  contributors: Contributor[];
  known_contribution_kwh: number;
  unattributed_kwh: number;
  attribution_overage_kwh: number;
  limitations: string[];
  speakable_summary: string;
  current_kwh?: number;
  previous_equivalent_kwh?: number;
};

export type ThresholdCrossing = {
  threshold_kwh: string;
  estimated_at: string;
  method: string;
};

export type TariffStatus = {
  tariff_id: string;
  tariff_name: string;
  tariff_type: string;
  currency: string;
  source: string;
  is_demo: boolean;
  current_usage_kwh: string;
  current_slab: string;
  current_estimated_energy_charge: string;
  next_threshold_kwh: string | null;
  units_until_next_threshold: string | null;
  current_marginal_rate: string;
  next_marginal_rate: string | null;
  projected_month_end_kwh: string;
  projected_slab: string;
  projected_estimated_energy_charge: string;
  expected_threshold_crossings: ThresholdCrossing[];
  threshold_warning: string;
  speakable_summary: string;
};

export type Recommendation = {
  rank: number;
  action: string;
  reason: string;
  evidence_source: string;
  estimated_reduction_kwh: string | null;
  impact_type: string | null;
};

export type ActionSuggestions = {
  target_kwh: string | null;
  target_status: string | null;
  current_usage_kwh: string;
  projected_usage_kwh: string;
  remaining_kwh_budget: string | null;
  remaining_days: string;
  required_average_daily_kwh: string | null;
  current_daily_run_rate_kwh: string;
  recommendations: Recommendation[];
  speakable_summary: string;
};

export type VerificationResult = {
  device: string;
  command: string;
  reported_state: string;
  verification: string;
  expected_power_watts: number;
  observed_power_delta_watts: number;
  observed_power_watts: number;
  confidence: number;
  confidence_level: string;
  evidence_source: string;
  telemetry_available: boolean;
  diagnostic_classification: string;
  reason: string;
  speakable_summary: string;
};

export type DiagnosticAttempt = {
  attempt: number;
  reported_state: string;
  available: boolean;
  baseline_watts: number;
  power_samples_watts: number[];
  observed_watts: number;
  observed_power_delta_watts: number;
  verification: string;
  diagnostic_classification: string;
  confidence: number;
  evidence: string[];
};

export type DiagnosticResult = {
  device: string;
  requested_action: string;
  final_status: string;
  initial_verification: string;
  diagnostic_classification: string;
  confidence: number;
  attempts: DiagnosticAttempt[];
  retries_used: number;
  safety_action: string;
  resolved: boolean;
  evidence: string[];
  speakable_summary: string;
};

export type DemoState = {
  mode: string;
  energy_scenario: string;
  heater_fault: string;
  simulated_at: string;
};

export type ActivityEvent = {
  event_id: number;
  timestamp: string;
  event_type: string;
  device_id: string | null;
  action: string;
  outcome: string;
  details: Record<string, string | number | boolean | null>;
};

export type MCPTrace = {
  trace_id: string;
  timestamp: string;
  transport: "STREAMABLE_HTTP";
  protocol_version: string | null;
  intent: string;
  tool_name: string;
  tool_arguments: Record<string, string | number | boolean | null>;
  result_summary: string;
  duration_ms: number;
  success: boolean;
  error: string | null;
};

export type SimulatorChatResponse = {
  message: string;
  intent: string;
  tool_call: {
    name: string;
    arguments: Record<string, string | number | boolean | null>;
  };
  result: Record<string, unknown>;
  trace_id: string;
};

export type Evidence =
  | { kind: "overview"; data: HouseholdOverview }
  | { kind: "energy"; data: EnergyComparison }
  | { kind: "usage"; data: UsageExplanation }
  | { kind: "tariff"; data: TariffStatus }
  | { kind: "target"; data: ActionSuggestions }
  | { kind: "verification"; data: VerificationResult }
  | { kind: "diagnostic"; data: DiagnosticResult };
