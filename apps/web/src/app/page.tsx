"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, ArrowUpRight, ShieldCheck, AlertTriangle, Package, Clock, Users, Bell, SlidersHorizontal } from "lucide-react";
import { useData } from "@/components/DataProvider";
import { Panel, Stat, Badge, SupplierTable, FilterTabs, GoLink, MonitoringButton, Notice, SearchField, RunProgress } from "@/components/ui/Workspace";

const shortMaterial = (name: string) => name
  .replace("High Barrier PVDC Film 25um", "PVDC barrier film")
  .replace("Polyethylene Resin HD-500", "PE resin HD-500")
  .replace("White Masterbatch MB-01", "White masterbatch");

export default function OverviewPage() {
  const { suppliers, materials, alerts } = useData();
  const [filter, setFilter] = useState("All suppliers");
  const [query, setQuery] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState(false);
  const high = suppliers.filter(s => s.band === "high").length;
  const watch = suppliers.filter(s => s.band === "watch").length;
  const low = suppliers.filter(s => s.band === "low").length;
  const open = alerts.filter(a => a.status === "open");
  const exposed = materials.filter(m => m.scenario_gap_days > 0);
  const priority = [...open].sort((a, b) =>
    Number(b.severity === "critical") - Number(a.severity === "critical") ||
    a.grounded_explanation.impact_assumptions.coverage_days - b.grounded_explanation.impact_assumptions.coverage_days
  )[0];
  const impact = priority?.grounded_explanation.impact_assumptions;
  const total = suppliers.length;
  const rows = [...suppliers].filter(s =>
    (filter === "All suppliers" || s.band === (filter === "High risk" ? "high" : "watch")) &&
    [s.legal_name, ...s.materials_supplied].join(" ").toLowerCase().includes(query.toLowerCase())
  ).sort((a, b) => Number(b.critical_override) - Number(a.critical_override) || b.blended_risk_R - a.blended_risk_R);
  const assessed = suppliers.map(s => s.last_assessed).sort().at(-1);
  const riskGroups = [{label:"Low risk",count:low,kind:"low"},{label:"On watch",count:watch,kind:"watch"},{label:"High risk",count:high,kind:"high"}];

  return <div className="page-stack overview-page">
    <div className="overview-heading">
      <div>
        <div className="eyebrow"><span className="eyebrow-line" /> OPERATIONS OVERVIEW <span className="eyebrow-index">/ 01</span></div>
        <h1>Your supply chain, <span>in clear view.</span></h1>
        <p className="subtitle">The signals that matter. The time to act.</p>
      </div>
      <div className="overview-heading-right">
        <div className="assessment-stamp"><span className="dot" /> LATEST ASSESSMENT <strong>{assessed ? new Date(assessed).toLocaleDateString("en-GB", {day:"2-digit",month:"short",year:"numeric",timeZone:"Asia/Kolkata"}) : "Awaiting assessment"}</strong></div>
        <MonitoringButton onMessage={(m, e) => {setMessage(m);setError(!!e);}} />
      </div>
    </div>
    {message && <Notice kind={error ? "error" : "success"}>{message}</Notice>}
    <RunProgress />

    <div className="stats-grid overview-stats">
      <Stat label="Suppliers monitored" value={String(total).padStart(2,"0")} icon={<Users />} detail={<><span className="dot positive" /> Across your supply network</>} />
      <Stat label="High-risk suppliers" value={String(high).padStart(2,"0")} icon={<AlertTriangle />} detail={<><span className="metric-annotation">{watch} on watch</span><span>Review recommended</span></>} tone="negative" />
      <Stat label="Materials exposed" value={String(exposed.length).padStart(2,"0")} icon={<Package />} detail="Under a delayed-arrival scenario" />
      <Stat label="Open action items" value={String(open.length).padStart(2,"0")} icon={<Bell />} detail={<GoLink href="/alerts">Go to your action queue</GoLink>} />
    </div>

    <div className="section-heading"><h2>The operational picture</h2><span><span className="dot" /> Current snapshot</span></div>
    <div className="operating-grid">
      {priority && impact ? <section className="risk-feature" aria-labelledby="priority-heading">
        <div className="risk-feature-top"><span className="feature-kicker"><span className="priority-signal" /> ATTENTION REQUIRED</span><span className="feature-index">01 / PRIORITY</span></div>
        <div className="risk-feature-title"><div><p>Supplier disruption</p><h2 id="priority-heading">{priority.supplier_name}</h2></div><span className="feature-shield"><AlertTriangle size={23} strokeWidth={1.4} /></span></div>
        <p className="risk-feature-description">{shortMaterial(priority.material_name)} is running low. Review the delay scenario before the next production cycle.</p>
        <div className="feature-metrics">
          <div className="feature-primary-metric"><strong>{String(impact.coverage_days).padStart(2,"0")}</strong><span>days of<br />stock coverage</span></div>
          <div className="feature-secondary-metric"><span className="feature-metric-label">PROJECTED SUPPLY GAP</span><strong>{impact.supply_gap_days}<small> days</small></strong><span>Arrival expected on day {impact.scenario_arrival_days}</span></div>
        </div>
        <div className="runway-timeline" aria-label={`${impact.coverage_days} days covered, followed by ${impact.supply_gap_days} days supply gap`}>
          <div className="runway-timeline-labels"><span>AVAILABLE STOCK</span><span className="timeline-gap-label">{impact.supply_gap_days}-DAY GAP</span></div>
          <div className="timeline-segments">{Array.from({length:Math.ceil(impact.scenario_arrival_days)},(_,i)=><span key={i} className={i < impact.coverage_days ? "covered" : "shortage"} />)}</div>
          <div className="timeline-axis"><span>Today</span><span>Day {impact.coverage_days} · stock depleted</span><span>Day {impact.scenario_arrival_days}</span></div>
        </div>
        <div className="risk-feature-footer"><span><ShieldCheck size={14} /> Evidence-backed scenario</span><Link href={`/alerts/${priority.id}`} className="feature-action">Review disruption <ArrowUpRight size={17} /></Link></div>
      </section> : <section className="risk-feature clear-state"><ShieldCheck size={38}/><h2>Nothing urgent.<br/>Keep your next move clear.</h2><p>Your current snapshot has no open alerts to review.</p><Link href="/suppliers" className="feature-action">Explore suppliers <ArrowUpRight size={17}/></Link></section>}

      <section className="runway-panel">
        <div className="runway-header"><div><span className="overline">PRODUCTION CONTINUITY</span><h2>Material runway</h2></div><Link href="/materials" className="circle-link" aria-label="Explore material coverage"><ArrowUpRight size={18}/></Link></div>
        <p className="runway-subtitle">How long your available inventory lasts.</p>
        <div className="runway-materials">{materials.map((m,i) => <Link className="runway-material" key={m.material_id} href={`/materials?material=${m.material_id}`}>
          <div className="runway-material-top"><span className="material-number">0{i+1}</span><strong>{shortMaterial(m.material_name)}</strong><span className="material-days">{m.coverage_days}<small>d</small></span></div>
          <div className="material-segments" aria-label={`${m.coverage_days} days of coverage`}>{Array.from({length:20},(_,day)=><span className={day<m.coverage_days?"available":day<m.scenario_arrival_days?"exposed":""} key={day}/>)}</div>
          <div className="runway-material-bottom"><span>{m.scenario_gap_days>0?<><span className="dot negative"/>{m.scenario_gap_days}-day gap in delay scenario</>:<><span className="dot positive"/>Covered through arrival</>}</span><ArrowUpRight size={13}/></div>
        </Link>)}</div>
        <div className="runway-foot"><span><i className="legend-swatch stock"/> Stock coverage</span><span><i className="legend-swatch gap"/> Supply gap</span><span>20-day scale</span></div>
      </section>
    </div>

    <section className="portfolio-strip" aria-label="Supplier risk distribution">
      <div className="portfolio-label"><span className="overline">NETWORK HEALTH</span><strong>{low} of {total} suppliers in the low-risk band</strong></div>
      <div className="portfolio-bar" role="img" aria-label={`${low} low risk, ${watch} on watch, ${high} high risk`}>{riskGroups.map(g=><span key={g.kind} className={g.kind} style={{flex:g.count||0.001}}/>)}</div>
      <div className="portfolio-legend">{riskGroups.map(g=><span key={g.kind}><i className={`dot ${g.kind}`}/>{g.label}<strong>{String(g.count).padStart(2,"0")}</strong></span>)}</div>
    </section>

    <Panel title="Supplier watchlist" description="Your network, ordered by priority and risk." className="watchlist-panel" action={<GoLink href="/suppliers">View directory</GoLink>}>
      <div className="toolbar"><FilterTabs options={["All suppliers","High risk","Watch"]} value={filter} onChange={setFilter} label="Supplier risk"/><SearchField value={query} onChange={setQuery} placeholder="Find a supplier…"/></div>
      <SupplierTable compact suppliers={rows}/>
      <div className="table-footer"><span>Showing <strong>{rows.length}</strong> of {total} suppliers</span><span><ShieldCheck size={12}/> Scores informed by delivery history & available evidence</span></div>
    </Panel>
  </div>;
}

