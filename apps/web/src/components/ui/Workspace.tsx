"use client";

import Link from "next/link";
import { ArrowUpRight, Search, ArrowRight, Info, Loader2, Play, CheckCircle2, ShieldCheck } from "lucide-react";
import { SupplierSummary } from "@/lib/api";
import { useData } from "@/components/DataProvider";

export function PageHeading({ eyebrow, title, description, children }: { eyebrow?: string; title: string; description: string; children?: React.ReactNode }) {
  return <div className="page-heading"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1>{title}</h1><p className="subtitle">{description}</p></div>{children && <div className="heading-actions">{children}</div>}</div>;
}
export function Panel({ title, description, action, children, className = "" }: { title: string; description?: string; action?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><div className="panel-head"><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{action}</div>{children}</section>;
}
export function Badge({ kind = "neutral", children }: { kind?: string; children: React.ReactNode }) {
  return <span className={`badge ${kind}`}><span className="dot" />{children}</span>;
}
export function Stat({ label, value, detail, icon, tone = "" }: { label: string; value: React.ReactNode; detail: React.ReactNode; icon: React.ReactNode; tone?: string }) {
  return <div className="panel stat"><div className="stat-top"><span>{label}</span><span className="stat-icon">{icon}</span></div><div className={`stat-value ${tone}`}>{value}</div><div className="stat-foot">{detail}</div></div>;
}
export function SearchField({ value, onChange, placeholder = "Search suppliers…" }: { value: string; onChange: (value: string) => void; placeholder?: string }) {
  return <div className="search-field"><Search /><input className="input" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} aria-label={placeholder} /></div>;
}
export function FilterTabs({ options, value, onChange, label = "Filter" }: { options: string[]; value: string; onChange: (v: string) => void; label?: string }) {
  return <div className="filter-tabs" role="group" aria-label={label}>{options.map(option => <button key={option} className={`filter-tab ${value === option ? "active" : ""}`} aria-pressed={value === option} onClick={() => onChange(option)}>{option}</button>)}</div>;
}
export function Empty({ title = "Nothing to show", description = "Try changing your filters." }: { title?: string; description?: string }) {
  return <div className="empty-state"><strong>{title}</strong>{description}</div>;
}
export function Notice({ children, kind = "" }: { children: React.ReactNode; kind?: string }) {
  return <div className={`notice ${kind}`} role={kind === "error" ? "alert" : "status"}>{kind === "success" ? <CheckCircle2 /> : <Info />}{children}</div>;
}
export function evidenceLabel(status: SupplierSummary["external_status"]) {
  return {
    reliable_evidence: "Offline event fixture", no_relevant_evidence: "No relevant evidence",
    ambiguous_entity: "Company match unclear", unavailable: "Check unavailable", stale: "Stale evidence",
  }[status];
}
const riskLabel = (band: string) => band === "low" ? "Low risk" : band === "high" ? "High risk" : "Watch";
const initials = (name: string) => name.split(" ").slice(0, 2).map(word => word[0]).join("");

export function SupplierTable({ suppliers, compact = false }: { suppliers: SupplierSummary[]; compact?: boolean }) {
  return <>
    <div className="table-wrap supplier-desktop-table">
      <table className="data-table"><thead><tr><th>Supplier</th><th>Material</th><th>On-time delivery</th><th>Risk score</th><th>Risk level</th>{!compact && <th>External evidence</th>}<th><span className="sr-only">View supplier</span></th></tr></thead>
        <tbody>{suppliers.map(s => <tr key={s.id}>
          <td><div className="supplier-cell"><span className="supplier-avatar">{initials(s.legal_name)}</span><div><Link className="supplier-name" href={`/suppliers/${s.id}`}>{s.legal_name}</Link><span className="supplier-location">{s.location}{s.total_due_lines < 10 && <span className="history-note"> · Limited history</span>}</span></div></div></td>
          <td className="supplier-material-cell">{s.materials_supplied.join(", ")}</td>
          <td><span className={s.on_time_rate < .6 ? "negative" : ""}>{(s.on_time_rate * 100).toFixed(0)}%</span></td>
          <td><div className="score-cell"><span>{s.blended_risk_R.toFixed(1)}</span><span className="score-track"><span style={{ width: `${s.blended_risk_R}%`, background: s.band === "high" ? "var(--red)" : s.band === "watch" ? "var(--amber)" : "var(--green)" }} /></span></div>{!!s.excluded_factors?.length && <small className="score-partial">Partial index</small>}</td>
          <td><Badge kind={s.band}>{riskLabel(s.band)}</Badge></td>
          {!compact && <td><span className={`evidence-state ${s.external_status}`}>{evidenceLabel(s.external_status)}</span></td>}
          <td><Link className="row-open" aria-label={`View ${s.legal_name}`} href={`/suppliers/${s.id}`}><ArrowUpRight size={14} /></Link></td>
        </tr>)}</tbody>
      </table>
    </div>
    <div className="mobile-supplier-list">{suppliers.map(s => <article className="mobile-supplier" key={s.id}>
      <div className="mobile-supplier-heading"><span className="supplier-avatar">{initials(s.legal_name)}</span><div><Link href={`/suppliers/${s.id}`}>{s.legal_name}</Link><span>{s.location}</span></div><Badge kind={s.band}>{riskLabel(s.band)}</Badge></div>
      <p>{s.materials_supplied.join(", ")}</p>
      <div className="mobile-supplier-metrics"><div><span>On time</span><strong>{Math.round(s.on_time_rate * 100)}%</strong></div><div><span>Risk index</span><strong>{s.blended_risk_R.toFixed(1)}{s.excluded_factors?.length ? <small> · Partial</small> : null}</strong></div><Link href={`/suppliers/${s.id}`} className="text-link">Inspect <ArrowUpRight size={13} /></Link></div>
      {!compact && <div className="mobile-supplier-evidence">{evidenceLabel(s.external_status)} · {s.total_due_lines < 10 ? "Limited history" : `${s.total_due_lines} due lines`}</div>}
    </article>)}</div>
    {suppliers.length === 0 && <Empty title="No matching suppliers" description="Try another supplier name, material, or risk filter." />}
  </>;
}

export function MonitoringButton({ onMessage }: { onMessage: (message: string, error?: boolean) => void }) {
  const { running, runMonitoring, hydrated } = useData();
  async function run() {
    try {
      await runMonitoring();
      onMessage("Demo assessment ready. Inspect the calculation steps in Monitoring runs.");
    } catch (error) { onMessage(error instanceof Error ? error.message : "Could not complete the walkthrough.", true); }
  }
  return <button className="button primary" onClick={run} disabled={running || !hydrated}>{running ? <Loader2 className="spin" /> : <Play />}{running ? "Assessing demo…" : "Run demo assessment"}</button>;
}
export function RunProgress() {
  const { running, progress, stage } = useData();
  if (!running) return null;
  return <div className="assessment-progress" role="status" aria-live="polite">
    <div><Loader2 className="spin" size={16} /><strong>{stage}</strong><span>{progress}%</span></div>
    <div className="assessment-progress-track" role="progressbar" aria-label="Demo assessment progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}><span style={{ width: `${progress}%` }} /></div>
    <small>Frozen synthetic records · Local calculation walkthrough</small>
  </div>;
}
export function GoLink({ href, children }: { href: string; children: React.ReactNode }) {
  return <Link className="text-link" href={href}>{children}<ArrowRight /></Link>;
}

