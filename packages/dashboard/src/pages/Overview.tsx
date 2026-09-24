import { Link } from "react-router-dom";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { EmptyState, ErrorState, LoadingState } from "@/components/EmptyState";
import { Card } from "@/components/ui/card";
import { SeverityBadge } from "@/components/ui/badge";
import { useScans } from "@/context/ScanContext";
import { riskFromFindings, severityColor } from "@/lib/severity";
import { chainTitle, formatWhen, prettyClass } from "@/lib/utils";

export function OverviewPage() {
  const { current, scans, loading, error } = useScans();

  if (loading) return <LoadingState label="Loading scans…" />;
  if (error) return <ErrorState message={error} />;
  if (scans.length === 0) {
    return (
      <EmptyState
        title="Run your first scan"
        body="No reports yet. Launch a scan to populate the console."
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
  const classRows = Object.entries(current.summary.by_vuln_class);
  const classMax = Math.max(1, ...classRows.map(([, count]) => count));
  const lastScanned = current.finished_at ?? current.started_at;

  return (
    <div className="space-y-8">
      <div>
        <p className="text-2xs font-medium uppercase tracking-[0.16em] text-inktext-faint">
          Executive overview
        </p>
        <h1 className="mt-2 text-[28px] font-semibold tracking-tight text-inktext">Risk score</h1>
        <p className="mt-1 text-sm text-inktext-muted">Highest finding on this scan.</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <Card className="px-6 py-7 lg:col-span-5">
          <p className="text-2xs font-medium uppercase tracking-[0.14em] text-inktext-faint">
            Overall risk score
          </p>
          <div className="mt-4 flex items-end gap-3">
            <p
              className="tabular font-sans text-hero"
              style={{ color: severityColor(risk.label) }}
            >
              {risk.score.toFixed(1)}
            </p>
            <p className="mb-2 text-lg text-inktext-faint">/ 10</p>
            <div className="mb-3">
              <SeverityBadge label={risk.label} />
            </div>
          </div>
          <div className="mt-5 h-1 overflow-hidden rounded-full bg-ink-700">
            <div
              className="h-full rounded-full transition-all duration-150"
              style={{
                width: `${Math.min(100, (risk.score / 10) * 100)}%`,
                background: severityColor(risk.label),
              }}
            />
          </div>
          {lastScanned ? (
            <p className="mt-4 text-xs text-inktext-faint">
              Last scanned {formatWhen(lastScanned)}
            </p>
          ) : null}
        </Card>

        <Card className="px-5 py-5 lg:col-span-7">
          <p className="text-2xs font-medium uppercase tracking-[0.14em] text-inktext-faint">
            Severity breakdown
          </p>
          <div className="mt-2 flex h-48 items-center gap-6">
            {donut.length === 0 ? (
              <p className="text-sm text-inktext-muted">No findings</p>
            ) : (
              <>
                <div className="relative h-full min-w-0 flex-1">
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie
                        data={donut}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={52}
                        outerRadius={72}
                        paddingAngle={2}
                        stroke="none"
                      >
                        {donut.map((slice) => (
                          <Cell key={slice.name} fill={slice.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          background: "#1e222b",
                          border: "1px solid #2d3340",
                          borderRadius: 8,
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                    <span className="tabular text-2xl font-semibold text-inktext">
                      {current.summary.total_findings}
                    </span>
                    <span className="text-2xs text-inktext-faint">findings</span>
                  </div>
                </div>
                <ul className="w-32 shrink-0 space-y-2.5 text-[13px]">
                  {donut.map((slice) => (
                    <li key={slice.name} className="flex items-center justify-between gap-2">
                      <span className="flex items-center gap-2 text-inktext-muted">
                        <span className="h-1.5 w-1.5 rounded-full" style={{ background: slice.color }} />
                        {slice.name}
                      </span>
                      <span className="tabular text-inktext">{slice.value}</span>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        </Card>
      </div>

      {(current.skipped_checks ?? []).length > 0 ? (
        <Card className="px-5 py-5">
          <h2 className="text-[13px] font-semibold text-inktext">Checks not run</h2>
          <p className="mt-1 text-xs text-inktext-faint">
            Spec-only scan — live detectors need a reachable allow-listed target and identities.
          </p>
          <ul className="mt-3 space-y-2">
            {current.skipped_checks?.map((item) => (
              <li key={item.check} className="text-sm">
                <span className="text-inktext">{item.check}</span>
                <span className="mt-0.5 block text-xs text-inktext-muted">{item.reason}</span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <section>
        <h2 className="text-[13px] font-semibold text-inktext">Findings by class</h2>
        <ul className="mt-3 space-y-3">
          {classRows.map(([name, count]) => (
            <li key={name}>
              <div className="mb-1 flex justify-between text-[13px]">
                <span className="text-inktext-muted">{prettyClass(name)}</span>
                <span className="tabular text-inktext">{count}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-ink-700">
                <div
                  className="h-full rounded-full bg-inktext-faint/70"
                  style={{ width: `${(count / classMax) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="text-[13px] font-semibold text-inktext">Attack chains</h2>
        <div className="mt-3 grid gap-4 lg:grid-cols-2">
          {current.chains.map((chain, index) => (
            <Link key={chain.id} to="/chains">
              <Card className="h-full px-5 py-5 transition-colors duration-150 hover:border-accent/40">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-baseline gap-3">
                    <span className="tabular text-2xs text-inktext-faint">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <h3 className="text-[15px] font-semibold text-inktext">{chainTitle(chain.id)}</h3>
                  </div>
                  <SeverityBadge label={chain.max_severity_label} />
                </div>
                <p className="mt-3 text-sm leading-relaxed text-inktext-muted">{chain.narrative}</p>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      <Card>
        <div className="border-b border-line px-5 py-4">
          <h2 className="text-[13px] font-semibold text-inktext">Business impact</h2>
        </div>
        <ul className="divide-y divide-line">
          {current.findings.map((finding) => (
            <li key={finding.id} className="flex gap-4 px-5 py-4">
              <SeverityBadge label={finding.severity_label} />
              <div>
                <p className="font-mono text-[12px] text-inktext-faint">{finding.endpoint}</p>
                <p className="mt-1 text-sm text-inktext">{finding.business_impact}</p>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
