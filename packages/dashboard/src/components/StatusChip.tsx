import { cn } from "@/lib/utils";

export function StatusChip({ status }: { status: string }) {
  const tone =
    status === "completed"
      ? "bg-emerald-500/15 text-emerald-300 border-emerald-500/30"
      : status === "running"
        ? "bg-sky-500/15 text-sky-300 border-sky-500/30"
        : status === "failed"
          ? "bg-critical/15 text-critical border-critical/30"
          : "bg-slate-500/15 text-slate-300 border-slate-500/30";
  return (
    <span className={cn("rounded-full border px-2 py-0.5 text-[11px] font-medium uppercase", tone)}>
      {status}
    </span>
  );
}
