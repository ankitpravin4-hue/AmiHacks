import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  ReactFlowProvider,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import { ChainStepNode, type ChainStepData } from "@/components/ChainStepNode";
import { EmptyState, ErrorState, LoadingState } from "@/components/EmptyState";
import { Card } from "@/components/ui/card";
import { SeverityBadge } from "@/components/ui/badge";
import { useScans } from "@/context/ScanContext";
import { cn, chainTitle } from "@/lib/utils";

const NODE_TYPES = { chainStep: ChainStepNode };
const NODE_WIDTH = 248;
const NODE_GAP = 80;
const NODE_Y = 96;

function splitEndpoint(endpoint: string): { method: string; path: string } {
  const [method, ...rest] = endpoint.split(" ");
  if (rest.length === 0) return { method: "GET", path: endpoint };
  return { method, path: rest.join(" ") };
}

export function ChainsPage() {
  const { current, scans, loading, error } = useScans();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string | null>(null);
  const active = current?.chains.find((chain) => chain.id === selected) ?? current?.chains[0] ?? null;

  const { nodes, edges } = useMemo(() => {
    if (!current || !active) return { nodes: [] as Node<ChainStepData>[], edges: [] as Edge[] };
    const count = active.finding_ids.length;
    const builtNodes: Node<ChainStepData>[] = active.finding_ids.map((findingId, index) => {
      const finding = current.findings.find((item) => item.id === findingId);
      const { method, path } = splitEndpoint(finding?.endpoint ?? findingId);
      return {
        id: findingId,
        type: "chainStep",
        position: { x: index * (NODE_WIDTH + NODE_GAP), y: NODE_Y },
        data: {
          findingId,
          step: index + 1,
          method,
          path,
          vulnClass: finding?.vuln_class ?? "",
          severity: finding?.severity_label ?? "Low",
          isEntry: index === 0,
          isImpact: index === count - 1 && count > 0,
        },
        draggable: false,
      };
    });
    const builtEdges: Edge[] = active.finding_ids.slice(1).map((findingId, offset) => {
      const prev = active.finding_ids[offset];
      return {
        id: `${prev}->${findingId}`,
        source: prev,
        target: findingId,
        type: "smoothstep",
        animated: true,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "#6b8cff",
          width: 12,
          height: 12,
        },
        style: { stroke: "#6b8cff", strokeWidth: 2 },
      };
    });
    return { nodes: builtNodes, edges: builtEdges };
  }, [current, active]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (scans.length === 0) {
    return <EmptyState title="No chains yet" body="Scan ShopAPI to detect account-takeover and data-theft chains." />;
  }
  if (!current) return <LoadingState label="Loading report…" />;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-2xs font-medium uppercase tracking-[0.16em] text-inktext-faint">Attack chains</p>
        <h1 className="mt-2 text-[28px] font-semibold tracking-tight text-inktext">Attack chains</h1>
      </div>
      <div className="flex flex-wrap gap-2">
        {current.chains.map((chain) => (
          <button
            key={chain.id}
            type="button"
            onClick={() => setSelected(chain.id)}
            className={cn(
              "rounded-[8px] border px-3 py-1.5 text-sm transition-colors duration-150",
              (active?.id ?? "") === chain.id
                ? "border-accent/50 bg-white/[0.06] text-inktext"
                : "border-line bg-ink-800 text-inktext-muted hover:border-accent/40 hover:text-inktext",
            )}
          >
            {chainTitle(chain.id)}
          </button>
        ))}
      </div>
      {active ? (
        <Card className="px-5 py-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-2xs font-medium uppercase tracking-[0.14em] text-inktext-faint">Story</p>
              <h2 className="mt-1 text-[15px] font-semibold text-inktext">{chainTitle(active.id)}</h2>
            </div>
            <SeverityBadge label={active.max_severity_label} />
          </div>
          <p className="mt-3 text-sm leading-relaxed text-inktext-muted">{active.narrative}</p>
        </Card>
      ) : null}
      <div className="h-[min(60vh,560px)] min-h-[420px] overflow-hidden rounded-card border border-line bg-ink-800">
        {nodes.length === 0 ? (
          <p className="p-8 text-sm text-inktext-faint">No chained findings in this scan.</p>
        ) : (
          <ReactFlowProvider>
            <ReactFlow
              key={active?.id}
              nodes={nodes}
              edges={edges}
              nodeTypes={NODE_TYPES}
              fitView
              fitViewOptions={{ padding: 0.24, minZoom: 0.55, maxZoom: 1.15 }}
              minZoom={0.4}
              maxZoom={1.4}
              proOptions={{ hideAttribution: true }}
              onNodeClick={(_, node) => {
                const findingId = (node.data as ChainStepData).findingId;
                navigate(`/findings/${encodeURIComponent(findingId)}`);
              }}
            >
              <Background color="#2d3340" gap={20} size={1} />
              <Controls showInteractive={false} />
            </ReactFlow>
          </ReactFlowProvider>
        )}
      </div>
    </div>
  );
}
