"use client";
import { useEffect, useState } from "react";
import { BarChart3, Target, Clock, ShieldCheck, Loader2 } from "lucide-react";
import { API_CLIENT, ReplayBaselineResult } from "@/lib/api";
import { PageHeading, Panel, Stat, FilterTabs, Badge, Notice, Empty } from "@/components/ui/Workspace";

export default function ReplayPage() {
  const [baselines, setBaselines] = useState<ReplayBaselineResult[]>([]);
  const [selected, setSelected] = useState("P2");
  const [metric, setMetric] = useState("Precision");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    API_CLIENT.getReplayBaselines()
      .then(data => {
        setBaselines(data || []);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="page-stack">
        <PageHeading eyebrow="RESEARCH & BENCHMARKS" title="Replay Studio" description="Evaluating policy models and comparative baseline benchmarks." />
        <div className="panel" style={{ padding: "40px 0", textAlign: "center" }}>
          <Loader2 className="spin" style={{ margin: "0 auto 12px" }} />
          <p className="subtitle">Loading evaluation baselines...</p>
        </div>
      </div>
    );
  }

  if (baselines.length === 0) {
    return (
      <div className="page-stack">
        <PageHeading eyebrow="RESEARCH & BENCHMARKS" title="Replay Studio" description="Evaluating policy models and comparative baseline benchmarks." />
        <Empty title="No replay benchmarks available" description="Run the research replay evaluation harness or import historical evaluation results to compare B0-B2 and P1-P2 policies." />
      </div>
    );
  }

  const active = baselines.find(b => b.system === selected) || baselines[0];
  const getValue = (b: typeof active) => metric === "Precision" ? b.alert_episode_precision : metric === "Recall" ? b.incident_recall : b.actionable_recall;

  return (
    <div className="page-stack">
      <PageHeading eyebrow="UNDERSTAND THE POLICY" title="Replay Studio" description="Compare baseline models and inspect the tradeoffs behind each operational approach." />
      <Notice>Comparative policy evaluation metrics across backtested periods.</Notice>
      
      <div className="stats-grid">
        <Stat label="Episode precision" value={<>{Math.round(active.alert_episode_precision * 100)}<small>%</small></>} detail={`Selected policy: ${active.system}`} icon={<Target />} />
        <Stat label="Incident recall" value={<>{Math.round(active.incident_recall * 100)}<small>%</small></>} detail="Incidents with a prior warning" icon={<ShieldCheck />} />
        <Stat label="Warning lead time" value={<>{active.warning_lead_time_days}<small> days</small></>} detail="Lead time before stockout" icon={<Clock />} />
        <Stat label="False-alert burden" value={active.false_alert_burden.toFixed(2)} detail="Episodes per supplier-month" icon={<BarChart3 />} />
      </div>

      <div className="detail-grid">
        <Panel title="Baseline comparison" description="Click a system below to inspect it" action={<FilterTabs options={["Precision", "Recall", "Actionable recall"]} value={metric} onChange={setMetric} label="Comparison metric" />}>
          <div className="panel-body replay-bars">
            {baselines.map(b => (
              <button
                className={`replay-row ${selected === b.system ? "selected" : ""}`}
                key={b.system}
                onClick={() => setSelected(b.system)}
                aria-pressed={selected === b.system}
                aria-label={`${b.system} ${b.name}, ${metric} ${Math.round(getValue(b) * 100)} percent`}
                style={{ background: "transparent", border: 0, padding: "6px 0", textAlign: "left" }}
              >
                <span>{b.system}</span>
                <div className="replay-track">
                  <div className="replay-fill" style={{ width: `${getValue(b) * 100}%` }} />
                </div>
                <span>{Math.round(getValue(b) * 100)}%</span>
              </button>
            ))}
          </div>
        </Panel>

        <Panel title={active.system + " · " + active.name} description="Selected system">
          <div className="panel-body detail-body">
            <p style={{ marginTop: 0 }}>{active.inputs}</p>
            <div className="key-value"><span>Actionable recall</span><strong>{Math.round(active.actionable_recall * 100)}%</strong></div>
            <div className="key-value"><span>Top-k agreement</span><strong>{Math.round(active.top_k_agreement * 100)}%</strong></div>
            <p className="subtitle" style={{ marginTop: 15 }}>Actionable recall counts warnings at least five days before stockout. Top-k agreement compares the priority order against the benchmark.</p>
          </div>
        </Panel>
      </div>

      <Panel title="Compare every system" description="Comparative metrics across all evaluated approaches">
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>System</th>
                <th>Precision</th>
                <th>Recall</th>
                <th>Lead time</th>
                <th>False-alert burden</th>
                <th>Actionable recall</th>
                <th>Inspect</th>
              </tr>
            </thead>
            <tbody>
              {baselines.map(b => (
                <tr key={b.system} style={{ background: selected === b.system ? "#f1f5e9" : undefined }}>
                  <td><strong style={{ fontWeight: 500 }}>{b.system} · {b.name}</strong></td>
                  <td>{Math.round(b.alert_episode_precision * 100)}%</td>
                  <td>{Math.round(b.incident_recall * 100)}%</td>
                  <td>{b.warning_lead_time_days} days</td>
                  <td>{b.false_alert_burden.toFixed(2)}</td>
                  <td>{Math.round(b.actionable_recall * 100)}%</td>
                  <td>
                    <button className="button small" onClick={() => setSelected(b.system)} aria-pressed={selected === b.system}>
                      {selected === b.system ? "Selected" : "Inspect"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="table-footer">
          <span>Comparative policy benchmarks · B0–B2 baselines · P1–P2 combined policies</span>
          <Badge kind="neutral">Backtest</Badge>
        </div>
      </Panel>
    </div>
  );
}
