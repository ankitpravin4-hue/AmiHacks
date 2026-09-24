import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import ReactFlow, {
  Background,
  Controls,
  MarkerType,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import { ChainStepNode, type ChainStepData } from "@/components/ChainStepNode";
import { EmptyState, ErrorState, LoadingState } from "@/components/EmptyState";
import { Card } from "@/components/ui/card";
import { SeverityBadge } from "@/components/ui/badge";
import { useScans } from "@/context/ScanContext";
import { layoutSurface } from "@/lib/chainLayout";
import { cn, chainTitle } from "@/lib/utils";
import type { AttackChain, Finding } from "@/lib/api";

const NODE_TYPES = { chainStep: ChainStepNode };
const EDGE_HOT = "#6b8cff";
const EDGE_DIM = "#4a5160";
const ALL = "all";

function splitEndpoint(endpoint: string): { method: string; path: string } {
  const [method, ...rest] = endpoint.split(" ");
  if (rest.length === 0) return { method: "GET", path: endpoint };
  return { method, path: rest.join(" ") };
}

function isHighOrCritical(label: string): boolean {
  return label === "High" || label === "Critical";
}

function chainEdges(chains: AttackChain[]): Array<{
  id: string;
  chainId: string;
  source: string;
  target: string;
}> {
  const built: Array<{ id: string; chainId: string; source: string; target: string }> = [];
  for (const chain of chains) {
    for (let index = 1; index < chain.finding_ids.length; index += 1) {
      const source = chain.finding_ids[index - 1];
      const target = chain.finding_ids[index];
      built.push({
        id: `${chain.id}:${source}->${target}`,
        chainId: chain.id,
        source,
        target,
      });
    }
  }
  return built;
}

function roleInChains(
  findingId: string,
  chains: AttackChain[],
  selected: string,
): { isEntry: boolean; isImpact: boolean; step?: number; inSelected: boolean; inAny: boolean } {
  const members = chains.filter((chain) => chain.finding_ids.includes(findingId));
  const inAny = members.length > 0;
  if (selected === ALL) {
    return {
      isEntry: chains.some((chain) => chain.finding_ids[0] === findingId),
      isImpact: chains.some((chain) => chain.finding_ids.at(-1) === findingId),
      inSelected: inAny,
      inAny,
    };
  }
  const chain = chains.find((item) => item.id === selected);
  const index = chain?.finding_ids.indexOf(findingId) ?? -1;
  return {
    isEntry: index === 0,
    isImpact: Boolean(chain && index === chain.finding_ids.length - 1 && index >= 0),
    step: index >= 0 ? index + 1 : undefined,
    inSelected: index >= 0,
    inAny,
  };
}

function buildGraph(
  findings: Finding[],
  chains: AttackChain[],
  selected: string,
): { nodes: Node<ChainStepData>[]; edges: Edge[] } {
  const links = chainEdges(chains);
  const positions = layoutSurface(
    findings.map((finding) => finding.id),
    links,
  );

  const nodes: Node<ChainStepData>[] = findings.map((finding) => {
    const role = roleInChains(finding.id, chains, selected);
    const { method, path } = splitEndpoint(finding.endpoint);
    const emphasis =
      selected === ALL ? "normal" : role.inSelected ? "hot" : "dim";
    return {
      id: finding.id,
      type: "chainStep",
      position: positions.get(finding.id) ?? { x: 0, y: 0 },
      data: {
        findingId: finding.id,
        step: role.step,
        method,
        path,
        vulnClass: finding.vuln_class,
        severity: finding.severity_label,
        isEntry: role.isEntry,
        isImpact: role.isImpact,
        emphasis,
      },
      draggable: false,
    };
  });

  const edges: Edge[] = links.map((link) => {
    const hot = selected === ALL || link.chainId === selected;
    return {
      id: link.id,
      source: link.source,
      target: link.target,
      type: "smoothstep",
      animated: hot,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: hot ? EDGE_HOT : EDGE_DIM,
        width: 12,
        height: 12,
      },
      style: {
        stroke: hot ? EDGE_HOT : EDGE_DIM,
        strokeWidth: hot ? 2 : 1.25,
        opacity: hot ? 1 : 0.4,
      },
    };
  });

  return { nodes, edges };
}

function AttackSurfaceCanvas({
  nodes,
  edges,
  onNodeClick,
}: {
  nodes: Node<ChainStepData>[];
  edges: Edge[];
  onNodeClick: (findingId: string) => void;
}) {
  const { fitView } = useReactFlow();
  const fingerprint = nodes.map((node) => node.id).join("|");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      fitView({ padding: 0.2, minZoom: 0.45, maxZoom: 1.05 });
    }, 40);
    return () => window.clearTimeout(timer);
  }, [fingerprint, fitView]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={NODE_TYPES}
      fitView
      fitViewOptions={{ padding: 0.2, minZoom: 0.45, maxZoom: 1.05 }}
      minZoom={0.35}
      maxZoom={1.4}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      proOptions={{ hideAttribution: true }}
      onNodeClick={(_, node) => {
        onNodeClick((node.data as ChainStepData).findingId);
      }}
    >
      <Background color="#2d3340" gap={20} size={1} />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}

export function ChainsPage() {
  const { current, scans, loading, error } = useScans();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string>(ALL);
  const active = current?.chains.find((chain) => chain.id === selected) ?? null;

  const { nodes, edges } = useMemo(() => {
    if (!current) return { nodes: [] as Node<ChainStepData>[], edges: [] as Edge[] };
    return buildGraph(current.findings, current.chains, selected);
  }, [current, selected]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (scans.length === 0) {
    return <EmptyState title="No chains yet" body="Scan ShopAPI to detect account-takeover and data-theft chains." />;
  }
  if (!current) return <LoadingState label="Loading report…" />;

  const findingCount = current.findings.length;
  const chainCount = current.chains.length;
  const criticalPaths = current.chains.filter((chain) => isHighOrCritical(chain.max_severity_label)).length;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-2xs font-medium uppercase tracking-[0.16em] text-inktext-faint">Attack chains</p>
        <h1 className="mt-2 text-[28px] font-semibold tracking-tight text-inktext">Attack chains</h1>
      </div>

      <div className="flex flex-wrap gap-2">
        <span className="inline-flex items-center gap-2 rounded-[8px] border border-line bg-ink-800 px-2.5 py-1 text-2xs font-medium uppercase tracking-[0.12em] text-inktext-faint">
          Findings
          <span className="tabular text-inktext">{findingCount}</span>
        </span>
        <span className="inline-flex items-center gap-2 rounded-[8px] border border-line bg-ink-800 px-2.5 py-1 text-2xs font-medium uppercase tracking-[0.12em] text-inktext-faint">
          Attack chains
          <span className="tabular text-inktext">{chainCount}</span>
        </span>
        <span className="inline-flex items-center gap-2 rounded-[8px] border border-line bg-ink-800 px-2.5 py-1 text-2xs font-medium uppercase tracking-[0.12em] text-inktext-faint">
          Critical paths
          <span className="tabular text-inktext">{criticalPaths}</span>
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setSelected(ALL)}
          className={cn(
            "rounded-[8px] border px-3 py-1.5 text-sm transition-colors duration-150",
            selected === ALL
              ? "border-accent/50 bg-white/[0.06] text-inktext"
              : "border-line bg-ink-800 text-inktext-muted hover:border-accent/40 hover:text-inktext",
          )}
        >
          All
        </button>
        {current.chains.map((chain) => (
          <button
            key={chain.id}
            type="button"
            onClick={() => setSelected(chain.id)}
            className={cn(
              "rounded-[8px] border px-3 py-1.5 text-sm transition-colors duration-150",
              selected === chain.id
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
      ) : (
        <Card className="px-5 py-4">
          <p className="text-2xs font-medium uppercase tracking-[0.14em] text-inktext-faint">Story</p>
          <h2 className="mt-1 text-[15px] font-semibold text-inktext">Full attack surface</h2>
          <p className="mt-3 text-sm leading-relaxed text-inktext-muted">
            Every finding from this scan. Select a chain to light up its path.
          </p>
        </Card>
      )}

      <div className="h-[min(70vh,640px)] min-h-[480px] overflow-hidden rounded-card border border-line bg-ink-800">
        {nodes.length === 0 ? (
          <p className="p-8 text-sm text-inktext-faint">No findings in this scan.</p>
        ) : (
          <ReactFlowProvider>
            <AttackSurfaceCanvas
              nodes={nodes}
              edges={edges}
              onNodeClick={(findingId) => navigate(`/findings/${encodeURIComponent(findingId)}`)}
            />
          </ReactFlowProvider>
        )}
      </div>
    </div>
  );
}
