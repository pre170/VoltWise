import type {
  ActionSuggestions,
  ActivityEvent,
  DemoState,
  DiagnosticResult,
  EnergyComparison,
  Health,
  HouseholdOverview,
  MCPTrace,
  SimulatorChatResponse,
  TariffStatus,
  UsageExplanation,
  VerificationResult,
} from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL
  ?? (import.meta.env.PROD ? "" : "http://127.0.0.1:8000");

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly code = "API_ERROR",
    public readonly status = 0,
  ) {
    super(message);
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      headers: { "Content-Type": "application/json", ...options?.headers },
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new ApiError(
        payload?.error?.message ?? `Request failed with status ${response.status}`,
        payload?.error?.code ?? "API_ERROR",
        response.status,
      );
    }
    return payload as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("The VoltWise API request timed out.", "TIMEOUT");
    }
    throw new ApiError("Backend unavailable. Start the VoltWise API on port 8000.", "OFFLINE");
  } finally {
    window.clearTimeout(timeout);
  }
}

export const api = {
  health: () => request<Health>("/api/health"),
  overview: () => request<HouseholdOverview>("/api/household/overview"),
  comparison: () => request<EnergyComparison>("/api/energy/comparison"),
  explanation: () => request<UsageExplanation>("/api/energy/explanation"),
  tariffStatus: () => request<TariffStatus>("/api/tariff/status"),
  recommendations: (target_kwh: number) =>
    request<ActionSuggestions>("/api/tariff/recommendations", {
      method: "POST",
      body: JSON.stringify({ target_kwh }),
    }),
  verifyHeater: () =>
    request<VerificationResult>("/api/devices/heater/turn-on-and-verify", { method: "POST" }),
  diagnoseHeater: () =>
    request<DiagnosticResult>("/api/devices/heater/diagnose", { method: "POST" }),
  demoState: () => request<DemoState>("/api/demo/state"),
  resetDemo: () => request<DemoState>("/api/demo/reset", { method: "POST" }),
  setScenario: (scenario: string) =>
    request<DemoState>("/api/demo/energy-scenario", {
      method: "POST",
      body: JSON.stringify({ scenario }),
    }),
  setFault: (fault: string) =>
    request<DemoState>("/api/demo/device-fault", {
      method: "POST",
      body: JSON.stringify({ device: "heater", fault }),
    }),
  events: (limit = 30) => request<ActivityEvent[]>(`/api/events?limit=${limit}`),
  traces: (limit = 30) => request<MCPTrace[]>(`/api/sim/traces?limit=${limit}`),
  simChat: (message: string) =>
    request<SimulatorChatResponse>("/api/sim/chat", {
      method: "POST",
      body: JSON.stringify({ message }),
    }),
};
