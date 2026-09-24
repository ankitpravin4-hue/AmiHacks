import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, api, connectProgress, type ProgressEvent } from "@/lib/api";
import { useScans } from "@/context/ScanContext";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";

export function NewScanPage() {
  const navigate = useNavigate();
  const { setCurrentId, refreshList, refreshCurrent } = useScans();
  const [target, setTarget] = useState("http://127.0.0.1:8000");
  const [preset, setPreset] = useState("shopapi");
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    return () => socketRef.current?.close();
  }, []);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setProgress({ percent: 0, step: "Queuing scan…" });
    setRunning(true);
    try {
      const accepted = await api.startScan({
        target_base_url: target.trim(),
        identities_preset: preset,
      });
      setCurrentId(accepted.scan_id);

      let settled = false;
      const settle = async () => {
        if (settled) return;
        settled = true;
        socketRef.current?.close();
        await refreshList();
        setCurrentId(accepted.scan_id);
        await refreshCurrent(accepted.scan_id);
        setRunning(false);
        navigate("/");
      };

      socketRef.current = connectProgress(
        accepted.scan_id,
        (frame) => {
          setProgress(frame);
          if (frame.status === "completed" || frame.status === "failed" || frame.percent >= 100) {
            void settle();
          }
        },
        () => undefined,
      );

      for (let attempt = 0; attempt < 90 && !settled; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 400));
        try {
          const detail = await api.getScan(accepted.scan_id);
          setProgress((prev) =>
            prev && prev.percent > 0
              ? prev
              : {
                  percent: detail.status === "completed" ? 100 : Math.min(95, 8 + attempt * 3),
                  step: detail.status === "running" ? "Scanning allow-listed target…" : detail.status,
                  status: detail.status,
                },
          );
          if (detail.status === "completed" || detail.status === "failed") {
            await settle();
          }
        } catch {
          /* keep polling — the live socket may still be the source of truth */
        }
      }
    } catch (err) {
      setRunning(false);
      setProgress(null);
      if (err instanceof ApiError && err.status === 400) {
        setError(err.detail);
        return;
      }
      setError(err instanceof Error ? err.message : "Scan failed to start");
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <p className="text-xs uppercase tracking-[0.25em] text-sky-400">Launch</p>
      <h1 className="mt-2 text-3xl font-semibold">New scan</h1>
      <p className="mt-2 text-sm text-slate-400">
        Paste an allow-listed base URL. The scanner refuses anything else.
      </p>
      <Card className="mt-8">
        <CardHeader title="Target" subtitle="ShopAPI demo is pre-filled." />
        <form onSubmit={onSubmit} className="space-y-5 px-5 py-5">
          <label className="block text-sm">
            <span className="mb-1.5 block text-slate-400">Target base URL</span>
            <input
              value={target}
              onChange={(event) => setTarget(event.target.value)}
              className="w-full rounded-md border border-line bg-ink-800 px-3 py-2 font-mono text-sm outline-none ring-sky-500/40 focus:ring-2"
              placeholder="http://127.0.0.1:8000"
              required
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1.5 block text-slate-400">Identities</span>
            <select
              value={preset}
              onChange={(event) => setPreset(event.target.value)}
              className="w-full rounded-md border border-line bg-ink-800 px-3 py-2 text-sm outline-none ring-sky-500/40 focus:ring-2"
            >
              <option value="shopapi">shopapi — alice / bob / admin / anonymous</option>
            </select>
          </label>
          {error ? (
            <p className="rounded-md border border-critical/30 bg-critical/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </p>
          ) : null}
          {progress ? (
            <div>
              <div className="mb-2 flex justify-between font-mono text-xs text-slate-400">
                <span>{progress.step}</span>
                <span>{progress.percent}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-ink-800">
                <div
                  className="h-full bg-gradient-to-r from-sky-500 to-cyan-300 transition-all duration-300"
                  style={{ width: `${progress.percent}%` }}
                />
              </div>
            </div>
          ) : null}
          <Button type="submit" disabled={running} className="w-full py-3">
            {running ? "Scanning…" : "Start scan"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
