import { NavLink, Outlet } from "react-router-dom";
import {
  Crosshair,
  GitGraph,
  History,
  LayoutDashboard,
  Plus,
  Radar,
  ShieldAlert,
  Table2,
} from "lucide-react";
import { useScans } from "@/context/ScanContext";
import { StatusChip } from "@/components/StatusChip";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/new", label: "New Scan", icon: Plus },
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/findings", label: "Findings", icon: ShieldAlert },
  { to: "/matrix", label: "Access Matrix", icon: Table2 },
  { to: "/chains", label: "Attack Chains", icon: GitGraph },
  { to: "/history", label: "History / Diff", icon: History },
];

export function AppShell() {
  const { current } = useScans();

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col border-r border-line bg-ink-900/90">
        <div className="flex items-center gap-2 px-5 py-5">
          <Radar className="h-5 w-5 text-sky-400" />
          <div>
            <p className="text-sm font-bold tracking-wide">SentinelAPI</p>
            <p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Ops console</p>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-3">
          {NAV.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 rounded-md px-3 py-2 text-sm text-slate-400 transition hover:bg-white/5 hover:text-slate-100",
                    isActive && "bg-sky-500/10 text-sky-200",
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
        <p className="px-5 py-4 text-[10px] text-slate-600">Allow-listed targets only</p>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-line bg-ink-900/60 px-6 py-3">
          <div className="flex items-center gap-3 text-sm">
            <Crosshair className="h-4 w-4 text-sky-400" />
            <span className="font-mono text-slate-300">
              {current?.target ?? "No target selected"}
            </span>
            {current ? <StatusChip status={current.status} /> : null}
          </div>
          <p className="font-mono text-[11px] text-slate-500">
            service :8100 · target :8000 · console :5173
          </p>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
