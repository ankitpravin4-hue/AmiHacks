import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

export function EmptyState({
  title,
  body,
}: {
  title: string;
  body: string;
}) {
  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center rounded-card border border-dashed border-line bg-ink-800/40 px-6 text-center">
      <p className="text-lg font-semibold text-inktext">{title}</p>
      <p className="mt-2 max-w-md text-sm text-inktext-muted">{body}</p>
      <Link to="/new" className="mt-5">
        <Button>Run your first scan</Button>
      </Link>
    </div>
  );
}

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex min-h-[30vh] items-center justify-center text-sm text-inktext-muted">
      <span className="mr-2 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
      {label}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-critical/30 bg-critical/10 px-4 py-3 text-sm text-rose-200">
      {message}
    </div>
  );
}
