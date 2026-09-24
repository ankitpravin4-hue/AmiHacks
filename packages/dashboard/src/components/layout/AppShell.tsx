import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import {
  GitGraph,
  History,
  LayoutDashboard,
  Plus,
  ShieldAlert,
  Sparkles,
  Table2,
} from "lucide-react";
import { useScans } from "@/context/ScanContext";
import { StatusChip } from "@/components/StatusChip";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/new", label: "New Scan", icon: Plus },
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/findings", label: "Findings", icon: ShieldAlert, badge: "findings" as const },
  { to: "/matrix", label: "Access Matrix", icon: Table2 },
  { to: "/chains", label: "Attack Chains", icon: GitGraph, badge: "chains" as const },
  { to: "/ai", label: "AI Pentester", icon: Sparkles },
  { to: "/history", label: "History / Diff", icon: History, badge: "scans" as const },
];

function viewLabel(pathname: string): string {
  if (pathname === "/new") return "New Scan";
  if (pathname.startsWith("/findings/")) return "Finding";
  if (pathname === "/findings") return "Findings";
  if (pathname === "/matrix") return "Access Matrix";
  if (pathname === "/chains") return "Attack Chains";
  if (pathname === "/ai") return "AI Pentester";
  if (pathname === "/history") return "History / Diff";
  return "Overview";
}

export function AppShell() {
  const { current, scans } = useScans();
  const location = useLocation();
  const counts = {
    findings: current?.summary.total_findings,
    chains: current?.chains.length,
    scans: scans.length || undefined,
  };

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col border-r border-line bg-ink-900">
        <div className="px-5 pb-2 pt-5">
          <p className="text-[15px] font-semibold tracking-tight text-inktext">SentinelAPI</p>
        </div>
        <div className="px-3 pb-4">
          <Link
            to="/new"
            className="flex items-center justify-center gap-2 rounded-[8px] bg-accent px-3 py-2 text-sm font-medium text-white transition-colors duration-150 hover:bg-accent-dim"
          >
            <Plus className="h-4 w-4" />
            New scan
          </Link>
        </div>
        <p className="px-5 pb-2 text-2xs font-medium uppercase tracking-[0.14em] text-inktext-faint">
          Workspace
        </p>
        <nav className="flex flex-1 flex-col gap-0.5 px-3">
          {NAV.map((item) => {
            const Icon = item.icon;
            const count = item.badge ? counts[item.badge] : undefined;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 rounded-[8px] px-3 py-2 text-[13px] text-inktext-muted transition-colors duration-150 hover:bg-white/[0.04] hover:text-inktext",
                    isActive && "bg-white/[0.06] text-inktext",
                  )
                }
              >
                <Icon className="h-3.5 w-3.5 shrink-0" />
                <span className="flex-1">{item.label}</span>
                {count !== undefined ? (
                  <span className="tabular text-2xs text-inktext-faint">{count}</span>
                ) : null}
              </NavLink>
            );
          })}
        </nav>
        <p className="px-5 py-4 text-2xs text-inktext-faint">Allow-listed targets only</p>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-ink-900/80 px-6 py-3">
          <p className="text-[13px] text-inktext-faint">
            Workspace
            <span className="mx-2 text-inktext-faint/60">/</span>
            <span className="text-inktext">{viewLabel(location.pathname)}</span>
          </p>
          <div className="flex min-w-0 items-center gap-3 text-[13px]">
            {current ? (
              <>
                <span className="text-2xs uppercase tracking-[0.12em] text-inktext-faint">
                  Scan target
                </span>
                <span className="truncate font-mono text-[12px] text-inktext">
                  {current.target}
                </span>
                <StatusChip status={current.status} />
              </>
            ) : (
              <span className="text-inktext-faint">No target selected</span>
            )}
          </div>
        </header>
        <main className="flex-1 overflow-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
