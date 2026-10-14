"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Activity, Users, ShieldAlert, FileText, CheckCircle2, RefreshCw, ChevronRight } from "lucide-react";
import { API_CLIENT, MonitoringRunTrace } from "@/lib/api";
import { PageHeading, Panel, Stat, Badge, Notice, MonitoringButton } from "@/components/ui/Workspace";
export default function RunsPage() {
  const [run,setRun]=useState<MonitoringRunTrace|null>(null),[message,setMessage]=useState(""),[error,setError]=useState(false),[loading,setLoading]=useState(true);
  async function load() {setLoading(true);try{setRun(await API_CLIENT.getRun());setError(false);}catch(e){setMessage(e instanceof Error?e.message:"Could not load run");setError(true);}finally{setLoading(false);}}
  useEffect(()=>{void load();},[]);
  useEffect(()=>{if(!run||!["running","pending"].includes(run.status))return;const timer=setTimeout(()=>void load(),2000);return()=>clearTimeout(timer);},[run]);
  const summary=run?.summary;
  return (
    <div className="page-stack">
      <PageHeading eyebrow="A RECORD OF EVERY CHECK" title="Monitoring runs" description="See the latest monitoring result and what was checked.">
        <button className="button" onClick={load} disabled={loading}>
          <RefreshCw className={loading ? "spin" : ""} /> Refresh
        </button>
        <MonitoringButton onMessage={(m, e) => { setMessage(m); setError(!!e); if (!e) void load(); }} />
      </PageHeading>
      {message && <Notice kind={error ? "error" : "success"}>{message}</Notice>}
      <div className="stats-grid">
        <Stat label="Run status" value={run?.status || "—"} detail={loading ? "Fetching latest run" : "Latest available result"} icon={<Activity />} />
        <Stat label="Suppliers checked" value={summary?.suppliers_checked ?? "—"} detail="Evaluated in this run" icon={<Users />} />
        <Stat label="High risk flagged" value={summary?.high_risk_flagged ?? "—"} detail="Operational and external signals" icon={<ShieldAlert />} />
        <Stat label="Evidence found" value={summary?.evidence_found ?? "—"} detail="Signals and evidence records" icon={<FileText />} />
      </div>
      <Panel title="Latest run" description="Operational execution summary from the monitoring service">
        {run ? (
          <>
            <div className="run-row">
              <div>
                <strong>{run.id}</strong>
                <small>As of {new Date(run.as_of).toLocaleString("en-GB", { timeZone: "Asia/Kolkata" })} IST</small>
              </div>
              <Badge kind={run.status}>{run.status}</Badge>
              <span className="subtitle">{run.attempt_count} attempt{run.attempt_count !== 1 ? "s" : ""}</span>
              <Link className="text-link" href="/alerts">Review alerts <ChevronRight /></Link>
            </div>
            <div className="panel-body">
              <div className="key-value">
                <span>Completed at</span>
                <strong>{run.completed_at ? new Date(run.completed_at).toLocaleString("en-GB", { timeZone: "Asia/Kolkata" }) + " IST" : "Pending"}</strong>
              </div>
              <div className="key-value">
                <span>Shortage scenarios</span>
                <strong>{summary?.shortage_scenarios ?? "—"}</strong>
              </div>
            </div>
          </>
        ) : (
          <div className="empty-state">
            {loading ? "Loading the latest monitoring run…" : "No monitoring runs recorded yet. Trigger a monitoring cycle to evaluate suppliers."}
          </div>
        )}
      </Panel>
      <Panel title="Execution details" description="Node-level traces supplied by the monitoring service">
        {run?.node_traces?.length ? (
          run.node_traces.map((n, i) => (
            <details className="trace-row" key={i}>
              <summary>
                <CheckCircle2 size={16} className={n.status === "ok" ? "positive" : "negative"} />
                {n.node}
                <span className="trace-duration">{n.duration_ms} ms</span>
                <Badge kind={n.status === "ok" ? "low" : n.status === "failed" ? "failed" : "neutral"}>{n.status}</Badge>
              </summary>
              <p>{n.details}</p>
            </details>
          ))
        ) : (
          <div className="empty-state">
            <strong>No execution traces recorded</strong>
            Node execution timings and traces will appear here when emitted by the monitoring pipeline.
          </div>
        )}
      </Panel>
    </div>
  );
}
