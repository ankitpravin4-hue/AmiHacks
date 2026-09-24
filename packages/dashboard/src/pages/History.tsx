import { useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { StatusChip } from "@/components/StatusChip";
import { useScans } from "@/context/ScanContext";
import { api, type ScanDiff } from "@/lib/api";
import { formatWhen } from "@/lib/utils";

export function HistoryPage() {
  const { scans, loading, error, setCurrentId } = useScans();
  const [a, setA] = useState<number | "">("");
  const [b, setB] = useState<number | "">("");
  const [diff, setDiff] = useState<ScanDiff | null>(null);
  const [diffError, setDiffError] = useState<string | null>(null);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (scans.length === 0) {
    return <EmptyState title="No scan history" body="Each completed scan lands here for regression diffs." />;
  }

  const onDiff = async () => {
    if (a === "" || b === "") return;
    setDiffError(null);
    try {
      setDiff(await api.diff(Number(a), Number(b)));
    } catch (err) {
      setDiffError(err instanceof Error ? err.message : "Diff failed");
    }
  };

  return (
    <div className="space-y-5">
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-sky-400">History</p>
        <h1 className="mt-2 text-3xl font-semibold">Scan history / diff</h1>
      </div>
      <Card>
        <CardHeader title="Past scans" subtitle="Click a row to make it the current report" />
        <table className="w-full text-sm">
          <thead className="border-b border-line text-xs uppercase text-slate-500">
            <tr>
              <th className="px-4 py-2 text-left">ID</th>
              <th className="px-4 py-2 text-left">Target</th>
              <th className="px-4 py-2 text-left">Started</th>
              <th className="px-4 py-2 text-left">Status</th>
              <th className="px-4 py-2 text-left">Findings</th>
            </tr>
          </thead>
          <tbody>
            {scans.map((scan) => (
              <tr
                key={scan.id}
                onClick={() => setCurrentId(scan.id)}
                className="cursor-pointer border-b border-line/70 hover:bg-white/5"
              >
                <td className="px-4 py-3 font-mono">{scan.id}</td>
                <td className="px-4 py-3 font-mono text-slate-300">{scan.target}</td>
                <td className="px-4 py-3 text-slate-400">{formatWhen(scan.started_at)}</td>
                <td className="px-4 py-3">
                  <StatusChip status={scan.status} />
                </td>
                <td className="px-4 py-3 font-mono">{scan.summary.total_findings}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card>
        <CardHeader title="Compare two scans" subtitle="new / fixed / persisting by finding key" />
        <div className="flex flex-wrap items-end gap-3 px-5 py-4">
          <label className="text-sm">
            <span className="mb-1 block text-slate-400">Scan A</span>
            <select
              value={a}
              onChange={(event) => setA(event.target.value ? Number(event.target.value) : "")}
              className="rounded-md border border-line bg-ink-800 px-3 py-2"
            >
              <option value="">Select</option>
              {scans.map((scan) => (
                <option key={scan.id} value={scan.id}>
                  #{scan.id} · {scan.status}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            <span className="mb-1 block text-slate-400">Scan B</span>
            <select
              value={b}
              onChange={(event) => setB(event.target.value ? Number(event.target.value) : "")}
              className="rounded-md border border-line bg-ink-800 px-3 py-2"
            >
              <option value="">Select</option>
              {scans.map((scan) => (
                <option key={scan.id} value={scan.id}>
                  #{scan.id} · {scan.status}
                </option>
              ))}
            </select>
          </label>
          <Button onClick={() => void onDiff()} disabled={a === "" || b === ""}>
            Diff
          </Button>
        </div>
        {diffError ? <div className="px-5 pb-4"><ErrorState message={diffError} /></div> : null}
        {diff ? (
          <div className="grid gap-4 px-5 pb-5 md:grid-cols-3">
            <DiffColumn title="New" tone="red" items={diff.new} />
            <DiffColumn title="Fixed" tone="green" items={diff.fixed} />
            <DiffColumn title="Persisting" tone="amber" items={diff.persisting} />
          </div>
        ) : null}
      </Card>
    </div>
  );
}

function DiffColumn({
  title,
  tone,
  items,
}: {
  title: string;
  tone: "red" | "green" | "amber";
  items: string[];
}) {
  const colors = {
    red: "border-critical/40 bg-critical/10 text-rose-100",
    green: "border-emerald-500/40 bg-emerald-500/10 text-emerald-100",
    amber: "border-medium/40 bg-medium/10 text-amber-100",
  };
  return (
    <div className={`rounded-lg border px-3 py-3 ${colors[tone]}`}>
      <p className="text-xs font-semibold uppercase tracking-wide">{title}</p>
      <ul className="mt-2 space-y-1 font-mono text-xs">
        {items.length === 0 ? <li className="opacity-60">None</li> : null}
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
