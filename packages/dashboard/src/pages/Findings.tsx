import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { EmptyState, ErrorState, LoadingState } from "@/components/EmptyState";
import { SeverityBadge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { useScans } from "@/context/ScanContext";
import { SEVERITY_ORDER } from "@/lib/severity";
import { prettyClass } from "@/lib/utils";

export function FindingsPage() {
  const { current, scans, loading, error } = useScans();
  const navigate = useNavigate();
  const [severity, setSeverity] = useState("all");
  const [klass, setKlass] = useState("all");
  const [minConfidence, setMinConfidence] = useState(0);

  const rows = useMemo(() => {
    if (!current) return [];
    return current.findings
      .filter((item) => (severity === "all" ? true : item.severity_label === severity))
      .filter((item) => (klass === "all" ? true : item.vuln_class === klass))
      .filter((item) => item.confidence >= minConfidence)
      .sort((a, b) => (SEVERITY_ORDER[b.severity_label] ?? 0) - (SEVERITY_ORDER[a.severity_label] ?? 0));
  }, [current, severity, klass, minConfidence]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (scans.length === 0) {
    return <EmptyState title="No findings yet" body="Run a scan to populate this table from the live API." />;
  }
  if (!current) return <LoadingState label="Loading report…" />;

  const classes = [...new Set(current.findings.map((item) => item.vuln_class))];

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-sky-400">Findings</p>
        <h1 className="mt-2 text-3xl font-semibold">Severity-ranked issues</h1>
      </div>
      <div className="flex flex-wrap gap-3">
        <select
          value={severity}
          onChange={(event) => setSeverity(event.target.value)}
          className="rounded-md border border-line bg-ink-800 px-3 py-2 text-sm"
        >
          <option value="all">All severities</option>
          {["Critical", "High", "Medium", "Low"].map((label) => (
            <option key={label} value={label}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={klass}
          onChange={(event) => setKlass(event.target.value)}
          className="rounded-md border border-line bg-ink-800 px-3 py-2 text-sm"
        >
          <option value="all">All classes</option>
          {classes.map((name) => (
            <option key={name} value={name}>
              {prettyClass(name)}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-xs text-slate-400">
          Confidence ≥ {minConfidence.toFixed(2)}
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={minConfidence}
            onChange={(event) => setMinConfidence(Number(event.target.value))}
          />
        </label>
      </div>
      <Card>
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Class</th>
              <th className="px-4 py-3">Endpoint</th>
              <th className="px-4 py-3">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((finding) => (
              <tr
                key={finding.id}
                onClick={() => navigate(`/findings/${encodeURIComponent(finding.id)}`)}
                className="cursor-pointer border-b border-line/70 transition hover:bg-white/5"
              >
                <td className="px-4 py-3">
                  <SeverityBadge label={finding.severity_label} />
                </td>
                <td className="px-4 py-3 font-mono">{finding.severity_score.toFixed(1)}</td>
                <td className="px-4 py-3 capitalize">{prettyClass(finding.vuln_class)}</td>
                <td className="px-4 py-3 font-mono text-slate-300">{finding.endpoint}</td>
                <td className="px-4 py-3 font-mono">{finding.confidence.toFixed(2)}</td>
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                  No findings match these filters.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
