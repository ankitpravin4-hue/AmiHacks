import { cn } from "@/lib/utils";

export function Card({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("rounded-card border border-line bg-ink-800 shadow-card", className)}>
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
      <div>
        <h2 className="text-[13px] font-semibold tracking-wide text-inktext">{title}</h2>
        {subtitle ? <p className="mt-1 text-xs text-inktext-muted">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}
