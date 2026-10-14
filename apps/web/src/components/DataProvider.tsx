"use client";

import { createContext, useContext, useEffect, useRef, useState, useCallback } from "react";
import { AlertItem, MaterialExposure, MonitoringRunTrace, SupplierSummary, API_CLIENT } from "@/lib/api";

export interface ReviewFeedback { alert_id: string; disposition: string; reason: string; recorded_at: string; }
export interface ImportDraft { id: string; name: string; type: string; row_count: number; saved_at: string; }

type WorkspaceData = {
  suppliers: SupplierSummary[];
  materials: MaterialExposure[];
  alerts: AlertItem[];
  runs: MonitoringRunTrace[];
  feedback: ReviewFeedback[];
  drafts: ImportDraft[];
  running: boolean;
  progress: number;
  stage: string;
  hydrated: boolean;
  storageAvailable: boolean;
  refresh: () => Promise<void>;
  runMonitoring: () => Promise<MonitoringRunTrace>;
  updateAlert: (id: string, status: AlertItem["status"]) => Promise<void>;
  recordFeedback: (id: string, disposition: string, reason: string) => Promise<void>;
  saveDraft: (name: string, type: string, rowCount: number) => ImportDraft;
};

const Context = createContext<WorkspaceData | null>(null);

export function DataProvider({ children }: { children: React.ReactNode }) {
  const [suppliers, setSuppliers] = useState<SupplierSummary[]>([]);
  const [materials, setMaterials] = useState<MaterialExposure[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [runs, setRuns] = useState<MonitoringRunTrace[]>([]);
  const [feedback, setFeedback] = useState<ReviewFeedback[]>([]);
  const [drafts, setDrafts] = useState<ImportDraft[]>([]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const [storageAvailable, setStorageAvailable] = useState(true);
  const runLock = useRef(false);

  const loadLiveData = useCallback(async () => {
    try {
      const [sup, mat, alt] = await Promise.all([
        API_CLIENT.getSuppliers(),
        API_CLIENT.getMaterials(),
        API_CLIENT.getAlerts(),
      ]);
      setSuppliers(sup || []);
      setMaterials(mat || []);
      setAlerts(alt || []);
    } catch (e) {
      console.warn("Could not load live data:", e);
      setSuppliers([]);
      setMaterials([]);
      setAlerts([]);
    }
  }, []);

  useEffect(() => {
    loadLiveData().finally(() => setHydrated(true));
  }, [loadLiveData]);

  async function refresh() {
    await loadLiveData();
  }

  async function runMonitoring(): Promise<MonitoringRunTrace> {
    if (runLock.current) throw new Error("An assessment is already running.");
    runLock.current = true;
    setRunning(true);
    setProgress(15);
    setStage("Triggering monitoring cycle...");
    try {
      const res = await API_CLIENT.triggerMonitoringRun();
      setProgress(50);
      setStage("Evaluating supplier delivery indicators and material scenarios...");
      
      let run: MonitoringRunTrace = {
        id: res.job_id,
        as_of: new Date().toISOString(),
        status: "pending",
        attempt_count: 1,
        summary: { suppliers_checked: 0, high_risk_flagged: 0, shortage_scenarios: 0, evidence_found: 0 },
        node_traces: [],
      };
      
      const maxRetries = 20;
      for (let i = 0; i < maxRetries; i++) {
        await new Promise(r => setTimeout(r, 600));
        try {
          const check = await API_CLIENT.getRun(res.job_id);
          if (check && check.status === "completed") {
            run = check;
            break;
          }
        } catch {}
        setProgress(Math.min(90, 50 + i * 2));
      }
      
      setProgress(100);
      setStage("Assessment complete.");
      await loadLiveData();
      setRuns(prev => [run, ...prev].slice(0, 12));
      return run;
    } finally {
      runLock.current = false;
      setRunning(false);
    }
  }

  async function updateAlert(id: string, status: AlertItem["status"]) {
    await API_CLIENT.updateAlert(id, status);
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, status, acknowledged_at: new Date().toISOString() } : a));
  }

  async function recordFeedback(id: string, disposition: string, reason: string) {
    await API_CLIENT.submitFeedback(id, disposition, reason);
    setFeedback(prev => [...prev, { alert_id: id, disposition, reason, recorded_at: new Date().toISOString() }].slice(-100));
  }

  function saveDraft(name: string, type: string, rowCount: number) {
    const draft = { id: `draft-${Date.now().toString(36)}`, name, type, row_count: rowCount, saved_at: new Date().toISOString() };
    setDrafts(prev => [...prev, draft].slice(-20));
    return draft;
  }

  return (
    <Context.Provider value={{
      suppliers, materials, alerts, runs, feedback, drafts, running, progress,
      stage, hydrated, storageAvailable, refresh, runMonitoring, updateAlert, recordFeedback, saveDraft,
    }}>
      {children}
    </Context.Provider>
  );
}

export function useData() {
  const data = useContext(Context);
  if (!data) throw new Error("Workspace data is unavailable");
  return data;
}
