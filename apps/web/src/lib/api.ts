/**
 * VendorGuard AI Typed Client SDK
 * Production client connecting to FastAPI backend with zero hardcoded demo data.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL !== undefined 
  ? process.env.NEXT_PUBLIC_API_URL 
  : (typeof window !== "undefined" ? "" : "http://127.0.0.1:8000");

export async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options?.headers },
      signal: AbortSignal.timeout(15000),
    });
  } catch {
    throw new Error("The API is currently unavailable. Ensure the backend service is running.");
  }
  const data = await response.json();
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : "The request could not be completed.");
  }
  return data as T;
}

export interface ImportPreview {
  preview_id: string;
  total_rows: number;
  valid_rows_count: number;
  error_rows_count: number;
  errors: { row_index: number; errors: string[] }[];
  sample_preview: Record<string, unknown>[];
}

export interface SupplierSummary {
  id: string;
  legal_name: string;
  aliases: string[];
  location: string;
  materials_supplied: string[];
  total_due_lines: number;
  on_time_rate: number;
  late_fraction_L: number;
  delay_factor_D: number;
  trend_factor_T: number;
  shortfall_F: number;
  internal_index_I: number;
  external_index_E: number | null;
  blended_risk_R: number;
  band: "low" | "watch" | "high";
  external_status: "reliable_evidence" | "no_relevant_evidence" | "ambiguous_entity" | "unavailable" | "stale";
  excluded_factors?: ("L" | "D" | "T" | "F")[];
  critical_override: boolean;
  override_reason?: string;
  last_assessed: string;
}

export interface MaterialExposure {
  material_id: string;
  material_name: string;
  criticality: "tier_1" | "tier_2" | "tier_3";
  unit: string;
  on_hand_stock: number;
  reserved_stock: number;
  available_stock: number;
  daily_consumption: number;
  coverage_days: number;
  scenario_arrival_days: number;
  scenario_gap_days: number;
  day_to_stockout: number | null;
  primary_supplier: string;
  has_alternate_supplier: boolean;
  alternate_suppliers: { name: string; lead_time_days: number; approved: boolean }[];
  trajectory_base: { day: number; date_str: string; balance: number; is_stockout: boolean }[];
  trajectory_stress: { day: number; date_str: string; balance: number; is_stockout: boolean }[];
}

export interface AlertItem {
  id: string;
  supplier_id: string;
  supplier_name: string;
  material_name: string;
  incident_key: string;
  severity: "high" | "watch" | "critical";
  status: "open" | "acknowledged" | "resolved" | "dismissed";
  created_at: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
  grounded_explanation: {
    summary: string;
    drivers: { metric: string; label: string; value: number | string; benchmark: string }[];
    evidence_ids: string[];
    evidence_excerpt?: string;
    evidence_source?: string;
    evidence_date?: string;
    impact_assumptions: {
      material: string;
      available_stock: number;
      daily_burn: number;
      coverage_days: number;
      scenario_arrival_days: number;
      supply_gap_days: number;
    };
    suggested_actions: string[];
    limitations: string;
  };
}

export interface MonitoringRunTrace {
  id: string;
  as_of: string;
  status: "pending" | "running" | "completed" | "failed";
  attempt_count: number;
  completed_at?: string;
  summary: {
    suppliers_checked: number;
    high_risk_flagged: number;
    shortage_scenarios: number;
    evidence_found: number;
  };
  node_traces: {
    node: string;
    status: "ok" | "skipped" | "failed";
    duration_ms: number;
    details: string;
  }[];
}

export interface ReplayBaselineResult {
  system: string;
  name: string;
  inputs: string;
  alert_episode_precision: number;
  incident_recall: number;
  warning_lead_time_days: number;
  false_alert_burden: number;
  actionable_recall: number;
  top_k_agreement: number;
}

export const API_CLIENT = {
  async getSuppliers(): Promise<SupplierSummary[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/suppliers`);
      if (res.ok) return await res.json();
    } catch {}
    return [];
  },

  async getMaterials(): Promise<MaterialExposure[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/materials`);
      if (res.ok) return await res.json();
    } catch {}
    return [];
  },

  async getAlerts(): Promise<AlertItem[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/alerts`);
      if (res.ok) return await res.json();
    } catch {}
    return [];
  },

  async triggerMonitoringRun(): Promise<{ job_id: string; status: string; message: string }> {
    return apiRequest("/api/monitoring-runs", { method: "POST" });
  },

  async updateAlert(id: string, status: AlertItem["status"]): Promise<AlertItem> {
    return apiRequest(`/api/alerts/${encodeURIComponent(id)}`, { method: "PATCH", body: JSON.stringify({ status }) });
  },

  async submitFeedback(id: string, disposition: string, reason: string) {
    return apiRequest(`/api/alerts/${encodeURIComponent(id)}/feedback`, { method: "POST", body: JSON.stringify({ disposition, reason }) });
  },

  async getRun(id?: string): Promise<MonitoringRunTrace> {
    const runId = id || (typeof window !== "undefined" ? window.sessionStorage.getItem("vendorguard-latest-run") : null) || "run-default";
    return apiRequest(`/api/monitoring-runs/${encodeURIComponent(runId)}`);
  },

  async previewImport(file_type: string, csv_text: string): Promise<ImportPreview> {
    return apiRequest("/api/imports/preview", { method: "POST", body: JSON.stringify({ file_type, csv_text }) });
  },

  async commitImport(preview_id: string): Promise<{ committed_records: number; status: string }> {
    return apiRequest(`/api/imports/${encodeURIComponent(preview_id)}/commit`, { method: "POST" });
  },

  async getReplayBaselines(): Promise<ReplayBaselineResult[]> {
    try {
      const res = await fetch(`${API_BASE_URL}/api/replay/baselines`);
      if (res.ok) return await res.json();
    } catch {}
    return [];
  },
};
