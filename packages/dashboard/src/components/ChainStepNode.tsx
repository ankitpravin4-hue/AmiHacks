import { Handle, Position, type NodeProps } from "reactflow";
import { prettyClass } from "@/lib/utils";
import { severityColor } from "@/lib/severity";

export interface ChainStepData {
  findingId: string;
  step: number;
  method: string;
  path: string;
  vulnClass: string;
  severity: string;
  isEntry: boolean;
  isImpact: boolean;
}

const METHOD_TONE: Record<string, string> = {
  GET: "bg-accent/15 text-accent",
  POST: "bg-medium/15 text-medium",
  PATCH: "bg-high/15 text-high",
  PUT: "bg-high/15 text-high",
  DELETE: "bg-critical/15 text-critical",
};

export function ChainStepNode({ data }: NodeProps<ChainStepData>) {
  const method = data.method.toUpperCase();
  return (
    <div
      className="w-[248px] cursor-pointer rounded-[10px] border border-line bg-ink-800 px-3 py-3 shadow-card"
      style={{ borderLeftWidth: 3, borderLeftColor: severityColor(data.severity) }}
    >
      <Handle type="target" position={Position.Left} className="!h-2 !w-2 !border-0 !bg-accent" />
      <div className="flex items-center justify-between gap-2">
        <span className="tabular flex h-5 min-w-5 items-center justify-center rounded-full bg-ink-700 text-2xs font-medium text-inktext">
          {data.step}
        </span>
        <div className="flex gap-1">
          {data.isEntry ? (
            <span className="rounded px-1.5 py-0.5 text-2xs font-medium uppercase tracking-wide text-accent">
              Entry
            </span>
          ) : null}
          {data.isImpact ? (
            <span className="rounded px-1.5 py-0.5 text-2xs font-medium uppercase tracking-wide text-high">
              Impact
            </span>
          ) : null}
        </div>
      </div>
      <div className="mt-2.5 flex items-center gap-2">
        <span
          className={`rounded px-1.5 py-0.5 font-mono text-2xs font-medium ${METHOD_TONE[method] ?? "bg-ink-700 text-inktext-muted"}`}
        >
          {method}
        </span>
      </div>
      <p className="mt-2 font-mono text-[12px] leading-snug text-inktext">{data.path}</p>
      {data.vulnClass ? (
        <p className="mt-1.5 text-2xs text-inktext-faint">{prettyClass(data.vulnClass)}</p>
      ) : null}
      <Handle type="source" position={Position.Right} className="!h-2 !w-2 !border-0 !bg-accent" />
    </div>
  );
}
