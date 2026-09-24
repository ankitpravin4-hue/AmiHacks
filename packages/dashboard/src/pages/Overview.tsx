import { Link } from "react-router-dom";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { EmptyState, ErrorState, LoadingState } from "@/components/EmptyState";
import { Card, CardHeader } from "@/components/ui/card";
import { SeverityBadge } from "@/components/ui/badge";
import { useScans } from "@/context/ScanContext";
import { riskFromFindings, severityColor } from "@/lib/severity";
import { chainTitle, prettyClass } from "@/lib/utils";

export function OverviewPage() {
  const { current, scans, loading, error } = useScans();

  if (loading) return <LoadingState label="Loading scans…" />;
  if (error) return <ErrorState message={error} />;
  if (scans.length === 0) {
    return (
      <EmptyState
        title="Run your first scan"
        body="No reports yet. Launch a ShopAPI scan to populate the console — findings are never hardcoded."
      />
    );
  }
  if (!current) return <LoadingState label="Loading report…" />;

  const risk = riskFromFindings(current.findings.map((item) => item.severity_score));
  const donut = Object.entries(current.summary.by_severity).map(([name, value]) => ({
    name,
    value,
    color: severityColor(name),
  }));

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-sky-400">Executive overview</p>
        <h1 className="mt-2 text-3xl font-semibold">Risk posture</h1>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="flex flex-col items-center justify-center px-6 py-8">
          <p className="text-xs uppercase tracking-widest text-slate-500">Headline risk</p>
          <p className="mt-3 font-mono text-6xl font-bold" style={{ color: severityColor(risk.label) }}>
            {risk.score.toFixed(1)}
          </p>
          <p className="mt-2">
            <SeverityBadge label={risk.label} />
          </p>
          <p className="mt-3 text-center text-xs text-slate-500">
            Max finding score across {current.summary.total_findings} issues
          </p>
        </Card>
        <Card className="px-4 py-4">
          <CardHeader title="Severity mix" subtitle="Counts by label" />
          <div className="flex h-52 items-center gap-4 px-4 py-2">
            {donut.length === 0 ? (
              <p className="p-6 text-sm text-slate-500">No findings</p>
            ) : (
              <>
                <div className="h-full min-w-0 flex-1">
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie data={donut} dataKey="value" nameKey="name" innerRadius={48} outerRadius={72} paddingAngle={3}>
                        {donut.map((slice) => (
                          <Cell key={slice.name} fill={slice.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ background: "#111827", border: "1px solid #1e2a3a" }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <ul className="w-28 shrink-0 space-y-2 text-xs">
                  {donut.map((slice) => (
                    <li key={slice.name} className="flex items-center justify-between gap-2">
                      <span className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-full" style={{ background: slice.color }} />
                        {slice.name}
                      </span>
                      <span className="font-mono text-slate-300">{slice.value}</span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </Card>
        <Card>
          <CardHeader title="By class" subtitle="Detector hits" />
          <ul className="space-y-2 px-5 py-4">
            {Object.entries(current.summary.by_vuln_class).map(([name, count]) => (
              <li key={name} className="flex justify-between text-sm">
                <span className="capitalize text-slate-300">{prettyClass(name)}</span>
                <span className="font-mono text-slate-100">{count}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {current.chains.map((chain) => (
          <Link key={chain.id} to="/chains">
            <Card className="h-full transition hover:border-sky-500/40">
              <CardHeader
                title={chainTitle(chain.id)}
                subtitle={`${chain.max_severity_label} · ${chain.max_severity_score.toFixed(1)}`}
                action={<SeverityBadge label={chain.max_severity_label} />}
              />
              <p className="px-5 py-4 text-sm leading-relaxed text-slate-300">{chain.narrative}</p>
            </Card>
          </Link>
        ))}
      </div>

      <Card>
        <CardHeader
          title="Business impact"
          subtitle="Plain English for non-technical stakeholders"
        />
        <ul className="divide-y divide-line">
          {current.findings.map((finding) => (
            <li key={finding.id} className="flex gap-4 px-5 py-4">
              <SeverityBadge label={finding.severity_label} />
              <div>
                <p className="font-mono text-xs text-slate-500">{finding.endpoint}</p>
                <p className="mt-1 text-sm text-slate-200">{finding.business_impact}</p>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
