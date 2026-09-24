import { cn } from "@/lib/utils";

export function StatusChip({ status }: { status: string }) {
  const tone =
    status === "completed"
      ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/25"
      : status === "running"
        ? "bg-accent/10 text-accent border-accent/25"
        : status === "failed"
          ? "bg-critical/10 text-critical border-critical/25"
          : "bg-ink-700 text-inktext-muted border-line";
  return (
    <span className={cn("rounded-full border px-2 py-0.5 text-2xs font-medium uppercase tracking-wide", tone)}>
      {status}
    </span>
  );
}
