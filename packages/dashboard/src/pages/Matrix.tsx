import { EmptyState, ErrorState, LoadingState } from "@/components/EmptyState";
import { Card, CardHeader } from "@/components/ui/card";
import { useScans } from "@/context/ScanContext";
import { cn } from "@/lib/utils";

const IDENTITY_ORDER = ["alice", "bob", "admin", "anonymous"];

export function MatrixPage() {
  const { current, scans, loading, error } = useScans();

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (scans.length === 0) {
    return <EmptyState title="No matrix yet" body="BOLA probes populate this grid after a scan." />;
  }
  if (!current) return <LoadingState label="Loading report…" />;

  const matrix = current.access_matrix ?? {};
  const endpoints = Object.keys(matrix);
  const identities = IDENTITY_ORDER.filter((name) =>
    endpoints.some((endpoint) => matrix[endpoint]?.[name] !== undefined),
  );

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-sky-400">Identity matrix</p>
        <h1 className="mt-2 text-3xl font-semibold">Who can reach whose objects</h1>
        <p className="mt-2 text-sm text-slate-400">
          Green is correctly denied. Red is leaked access — the BOLA proof.
        </p>
      </div>
      {endpoints.length === 0 ? (
        <p className="text-sm text-slate-500">This scan did not emit an access matrix.</p>
      ) : (
        <Card>
          <CardHeader title="Cross-access results" subtitle="Identity × object endpoint" />
          <div className="overflow-auto px-4 py-4">
            <table className="min-w-full border-collapse text-sm">
              <thead>
                <tr>
                  <th className="px-3 py-2 text-left text-xs uppercase text-slate-500">Endpoint</th>
                  {identities.map((name) => (
                    <th key={name} className="px-3 py-2 text-center font-mono text-xs text-slate-400">
                      {name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {endpoints.map((endpoint) => (
                  <tr key={endpoint} className="border-t border-line">
                    <td className="px-3 py-3 font-mono text-xs text-slate-300">{endpoint}</td>
                    {identities.map((name) => {
                      const value = matrix[endpoint]?.[name];
                      const leaked = value === "allowed";
                      return (
                        <td key={name} className="px-3 py-3 text-center">
                          <span
                            className={cn(
                              "inline-block min-w-[5.5rem] rounded-md border px-2 py-1 text-[11px] font-semibold uppercase",
                              leaked
                                ? "border-critical/40 bg-critical/20 text-rose-200"
                                : "border-emerald-500/30 bg-emerald-500/15 text-emerald-200",
                            )}
                          >
                            {leaked ? "Leaked" : "Denied"}
                          </span>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
