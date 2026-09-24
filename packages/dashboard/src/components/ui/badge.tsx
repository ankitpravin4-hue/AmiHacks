import { cn } from "@/lib/utils";
import { severityBadgeClass } from "@/lib/severity";

export function Badge({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function SeverityBadge({ label }: { label: string }) {
  return <Badge className={severityBadgeClass(label)}>{label}</Badge>;
}
