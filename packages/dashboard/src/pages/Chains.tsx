import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import ReactFlow, {
  Background,
  Controls,
  ReactFlowProvider,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import { EmptyState, ErrorState, LoadingState } from "@/components/EmptyState";
import { Card, CardHeader } from "@/components/ui/card";
import { SeverityBadge } from "@/components/ui/badge";
import { useScans } from "@/context/ScanContext";
import { severityColor } from "@/lib/severity";
import { chainTitle } from "@/lib/utils";

export function ChainsPage() {
  const { current, scans, loading, error } = useScans();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string | null>(null);

  const { nodes, edges } = useMemo(() => {
    if (!current) return { nodes: [] as Node[], edges: [] as Edge[] };
    const builtNodes: Node[] = [];
    const builtEdges: Edge[] = [];
    current.chains.forEach((chain, chainIndex) => {
      chain.finding_ids.forEach((findingId, index) => {
        const finding = current.findings.find((item) => item.id === findingId);
        builtNodes.push({
          id: `${chain.id}:${findingId}`,
          position: { x: 80 + index * 280, y: 60 + chainIndex * 200 },
          data: {
            label: finding?.endpoint ?? findingId,
            findingId,
          },
          style: {
            background: "#111827",
            color: "#e2e8f0",
            border: `1px solid ${severityColor(finding?.severity_label ?? "Low")}`,
            borderRadius: 10,
            padding: 10,
            width: 220,
            fontSize: 12,
          },
        });
        if (index > 0) {
          const prev = chain.finding_ids[index - 1];
          builtEdges.push({
            id: `${chain.id}-${prev}-${findingId}`,
            source: `${chain.id}:${prev}`,
            target: `${chain.id}:${findingId}`,
            animated: true,
            style: { stroke: "#38bdf8" },
          });
        }
      });
    });
    return { nodes: builtNodes, edges: builtEdges };
  }, [current]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (scans.length === 0) {
    return <EmptyState title="No chains yet" body="Scan ShopAPI to detect account-takeover and data-theft chains." />;
  }
  if (!current) return <LoadingState label="Loading report…" />;

  const active = current.chains.find((chain) => chain.id === selected) ?? current.chains[0];

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs uppercase tracking-[0.25em] text-sky-400">Attack chains</p>
        <h1 className="mt-2 text-3xl font-semibold">How findings combine</h1>
      </div>
      <div className="flex flex-wrap gap-2">
        {current.chains.map((chain) => (
          <button
            key={chain.id}
            type="button"
            onClick={() => setSelected(chain.id)}
            className="rounded-md border border-line bg-ink-800 px-3 py-1.5 text-sm hover:border-sky-500/40"
          >
            {chainTitle(chain.id)}
          </button>
        ))}
      </div>
      {active ? (
        <Card>
          <CardHeader
            title={chainTitle(active.id)}
            action={<SeverityBadge label={active.max_severity_label} />}
          />
          <p className="px-5 py-4 text-sm text-slate-300">{active.narrative}</p>
        </Card>
      ) : null}
      <div className="h-[420px] overflow-hidden rounded-xl border border-line bg-ink-900">
        {nodes.length === 0 ? (
          <p className="p-8 text-sm text-slate-500">No chained findings in this scan.</p>
        ) : (
          <ReactFlowProvider>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              onNodeClick={(_, node) => {
                const findingId = (node.data as { findingId: string }).findingId;
                navigate(`/findings/${encodeURIComponent(findingId)}`);
              }}
            >
              <Background color="#1e2a3a" gap={18} />
              <Controls />
            </ReactFlow>
          </ReactFlowProvider>
        )}
      </div>
    </div>
  );
}
