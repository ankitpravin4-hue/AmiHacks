import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Check, Copy } from "lucide-react";
import { EmptyState, ErrorState, LoadingState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { SeverityBadge } from "@/components/ui/badge";
import { Card, CardHeader } from "@/components/ui/card";
import { useScans } from "@/context/ScanContext";
import { api, type Finding, type ReplayResult } from "@/lib/api";
import { chainTitle } from "@/lib/utils";

export function FindingDetailPage() {
  const { findingKey } = useParams();
  const { currentId, current, loading: scanLoading } = useScans();
  const [finding, setFinding] = useState<Finding | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [replay, setReplay] = useState<ReplayResult | null>(null);
  const [replaying, setReplaying] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!currentId || !findingKey) return;
    void api
      .getFinding(currentId, findingKey)
      .then(setFinding)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load finding"));
  }, [currentId, findingKey]);

  if (scanLoading) return <LoadingState label="Loading scans…" />;
  if (!currentId || !findingKey) {
    return <EmptyState title="No scan selected" body="Run a scan first, then open a finding." />;
  }
  if (error) return <ErrorState message={error} />;
  if (!finding) return <LoadingState label="Loading finding…" />;

  const evidence = finding.evidence[0];
  const onCopy = async () => {
    await navigator.clipboard.writeText(finding.poc_curl);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };
  const onReplay = async () => {
    setReplaying(true);
    try {
      setReplay(await api.replay(currentId, finding.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Replay failed");
    } finally {
      setReplaying(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-sky-400">Finding</p>
          <h1 className="mt-2 text-2xl font-semibold">{finding.title || finding.endpoint}</h1>
          <p className="mt-1 font-mono text-sm text-slate-400">{finding.endpoint}</p>
        </div>
        <div className="flex items-center gap-2">
          <SeverityBadge label={finding.severity_label} />
          <span className="font-mono text-lg">{finding.severity_score.toFixed(1)}</span>
        </div>
      </div>

      <p className="rounded-xl border border-line bg-ink-900 px-5 py-4 text-sm leading-relaxed text-slate-200">
        {finding.business_impact}
      </p>

      {finding.chain_id && current ? (
        <Link to="/chains" className="text-sm text-sky-300 hover:underline">
          Part of chain: {chainTitle(finding.chain_id)}
        </Link>
      ) : null}

      <Card>
        <CardHeader title="Proof of concept" subtitle="Copy-pasteable curl (demo tokens)" />
        <div className="flex items-start justify-between gap-3 px-5 py-4">
          <pre className="flex-1 overflow-auto font-mono text-xs text-slate-300">{finding.poc_curl}</pre>
          <Button variant="outline" onClick={() => void onCopy()}>
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            Copy
          </Button>
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Replay attack"
          subtitle="Re-runs the exact PoC through SafeClient"
          action={
            <Button variant="danger" onClick={() => void onReplay()} disabled={replaying}>
              {replaying ? "Replaying…" : "Replay attack"}
            </Button>
          }
        />
        {replay ? (
          <div className="space-y-3 px-5 py-4">
            <span
              className={
                replay.still_vulnerable
                  ? "rounded-md border border-critical/40 bg-critical/15 px-2 py-1 text-xs font-bold uppercase text-critical"
                  : "rounded-md border border-emerald-500/40 bg-emerald-500/15 px-2 py-1 text-xs font-bold uppercase text-emerald-300"
              }
            >
              {replay.still_vulnerable ? "Still vulnerable" : "No longer vulnerable"}
            </span>
            <p className="font-mono text-xs text-slate-400">
              {replay.request.method} {replay.request.url} → {replay.response.status}
            </p>
            <pre className="max-h-48 overflow-auto rounded-md bg-ink-800 p-3 font-mono text-xs text-slate-300">
              {replay.response.body}
            </pre>
          </div>
        ) : (
          <p className="px-5 py-4 text-sm text-slate-500">Run the live replay to see a fresh response.</p>
        )}
      </Card>

      {evidence ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader title="Request evidence" subtitle="Authorization redacted" />
            <pre className="max-h-72 overflow-auto px-5 py-4 font-mono text-xs text-slate-300">
              {JSON.stringify(evidence.request, null, 2)}
            </pre>
          </Card>
          <Card>
            <CardHeader title="Response evidence" />
            <pre className="max-h-72 overflow-auto px-5 py-4 font-mono text-xs text-slate-300">
              {JSON.stringify(evidence.response, null, 2)}
            </pre>
          </Card>
        </div>
      ) : null}

      {finding.severity_breakdown ? (
        <Card>
          <CardHeader
            title="Why this score"
            subtitle={`Impact ${finding.severity_breakdown.impact} + exploitability ${finding.severity_breakdown.exploitability}`}
          />
          <div className="space-y-3 px-5 py-4">
            {finding.severity_breakdown.factors.map((factor) => {
              const pct = factor.max_score > 0 ? (factor.score / factor.max_score) * 100 : 0;
              return (
                <div key={factor.name}>
                  <div className="mb-1 flex justify-between text-xs">
                    <span className="font-medium capitalize text-slate-200">
                      {factor.name.replaceAll("_", " ")}
                    </span>
                    <span className="font-mono text-slate-400">
                      {factor.score}/{factor.max_score}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-ink-800">
                    <div className="h-full rounded-full bg-sky-400" style={{ width: `${pct}%` }} />
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{factor.reason}</p>
                </div>
              );
            })}
          </div>
        </Card>
      ) : null}

      <Card>
        <CardHeader title="Remediation" />
        <pre className="whitespace-pre-wrap px-5 py-4 font-mono text-xs leading-relaxed text-slate-300">
          {finding.remediation}
        </pre>
      </Card>
    </div>
  );
}
