import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, api, connectProgress, type ProgressEvent } from "@/lib/api";
import { useScans } from "@/context/ScanContext";
import { Button } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type InputMode = "url" | "upload" | "paste";

const SPEC_EXT = new Set([".json", ".yaml", ".yml"]);
const SPEC_MAX_BYTES = 2 * 1024 * 1024;

const VULN_CHIPS = [
  { label: "BOLA/IDOR", needsLive: true },
  { label: "Excessive Data Exposure", needsLive: false },
  { label: "Auth Issues", needsLive: false },
  { label: "Rate Limiting", needsLive: true },
] as const;

function fileExtension(name: string): string {
  const index = name.lastIndexOf(".");
  return index >= 0 ? name.slice(index).toLowerCase() : "";
}

export function NewScanPage() {
  const navigate = useNavigate();
  const { setCurrentId, refreshList, refreshCurrent } = useScans();
  const [mode, setMode] = useState<InputMode>("url");
  const [target, setTarget] = useState("http://127.0.0.1:8000");
  const [optionalTarget, setOptionalTarget] = useState("");
  const [preset, setPreset] = useState("shopapi");
  const [specText, setSpecText] = useState("");
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    return () => socketRef.current?.close();
  }, []);

  const onFile = async (file: File | undefined) => {
    setError(null);
    setFileName(null);
    setSpecText("");
    if (!file) return;
    const ext = fileExtension(file.name);
    if (!SPEC_EXT.has(ext)) {
      setError("That file is not YAML or JSON. Upload a .yaml, .yml, or .json OpenAPI/Swagger spec.");
      if (fileRef.current) fileRef.current.value = "";
      return;
    }
    if (file.size > SPEC_MAX_BYTES) {
      setError("Spec file is too large (max 2 MB).");
      if (fileRef.current) fileRef.current.value = "";
      return;
    }
    const text = await file.text();
    if (!text.trim()) {
      setError("The selected spec file is empty.");
      if (fileRef.current) fileRef.current.value = "";
      return;
    }
    setFileName(file.name);
    setSpecText(text);
  };

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    const liveUrl = mode === "url" ? target.trim() : optionalTarget.trim();
    const spec = mode === "url" ? "" : specText.trim();

    if (mode === "url" && !liveUrl) {
      setError("Enter an allow-listed target base URL.");
      return;
    }
    if (mode === "upload" && !spec) {
      setError("Choose a .yaml, .yml, or .json OpenAPI/Swagger spec.");
      return;
    }
    if (mode === "paste" && !spec) {
      setError("Paste an OpenAPI/Swagger document (JSON or YAML).");
      return;
    }

    setProgress({ percent: 0, step: "Queuing scan…" });
    setRunning(true);
    try {
      const accepted = await api.startScan({
        identities_preset: preset,
        ...(liveUrl ? { target_base_url: liveUrl } : {}),
        ...(spec ? { spec_text: spec } : {}),
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
                  step: detail.status === "running" ? "Scanning…" : detail.status,
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

  const liveEnabled = mode === "url" || Boolean(optionalTarget.trim());

  return (
    <div className="mx-auto max-w-2xl">
      <p className="text-2xs font-medium uppercase tracking-[0.16em] text-inktext-faint">New scan</p>
      <h1 className="mt-2 text-[28px] font-semibold tracking-tight text-inktext">Target</h1>
      <p className="mt-1 text-sm text-inktext-muted">
        Live allow-listed URL, or an OpenAPI/Swagger spec (JSON or YAML).
      </p>

      <p className="mt-6 rounded-[8px] border border-accent/35 bg-accent/10 px-4 py-3 text-sm leading-relaxed text-inktext">
        Only scan APIs you own or are authorized to test.
      </p>

      <div className="mt-5 flex flex-wrap gap-2">
        {VULN_CHIPS.map((chip) => (
          <span
            key={chip.label}
            className="inline-flex items-center gap-2 rounded-[8px] border border-line bg-ink-800 px-2.5 py-1 text-2xs font-medium text-inktext-muted"
          >
            {chip.label}
            {chip.needsLive ? (
              <span className="text-inktext-faint">needs live target</span>
            ) : (
              <span className="text-inktext-faint">spec or live</span>
            )}
          </span>
        ))}
      </div>

      <Card className="mt-8">
        <CardHeader title="Scan" />
        <form onSubmit={onSubmit} className="space-y-5 px-5 py-5">
          <div className="flex flex-wrap gap-2">
            {(
              [
                ["url", "Live URL"],
                ["upload", "Upload spec"],
                ["paste", "Paste spec"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => {
                  setMode(id);
                  setError(null);
                }}
                className={cn(
                  "rounded-[8px] border px-3 py-1.5 text-sm transition-colors duration-150",
                  mode === id
                    ? "border-accent/50 bg-white/[0.06] text-inktext"
                    : "border-line bg-ink-800 text-inktext-muted hover:border-accent/40 hover:text-inktext",
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {mode === "url" ? (
            <label className="block text-sm">
              <span className="mb-1.5 block text-inktext-muted">Target base URL</span>
              <input
                value={target}
                onChange={(event) => setTarget(event.target.value)}
                className="w-full rounded-[8px] border border-line bg-ink-900 px-3 py-2 font-mono text-sm text-inktext outline-none ring-accent/30 focus:ring-2"
                placeholder="http://127.0.0.1:8000"
                required
              />
              <span className="mt-1.5 block text-xs text-inktext-faint">
                Scanner fetches /openapi.json from this allow-listed host.
              </span>
            </label>
          ) : null}

          {mode === "upload" ? (
            <label className="block text-sm">
              <span className="mb-1.5 block text-inktext-muted">OpenAPI / Swagger file</span>
              <input
                ref={fileRef}
                type="file"
                accept=".yaml,.yml,.json,application/json,application/yaml,text/yaml"
                onChange={(event) => void onFile(event.target.files?.[0])}
                className="block w-full text-sm text-inktext-muted file:mr-3 file:rounded-[8px] file:border file:border-line file:bg-ink-800 file:px-3 file:py-1.5 file:text-sm file:text-inktext"
              />
              {fileName ? (
                <span className="mt-1.5 block font-mono text-xs text-inktext-muted">{fileName}</span>
              ) : (
                <span className="mt-1.5 block text-xs text-inktext-faint">Accepts .yaml, .yml, or .json.</span>
              )}
            </label>
          ) : null}

          {mode === "paste" ? (
            <label className="block text-sm">
              <span className="mb-1.5 block text-inktext-muted">Raw OpenAPI / Swagger</span>
              <textarea
                value={specText}
                onChange={(event) => setSpecText(event.target.value)}
                rows={12}
                className="w-full resize-y rounded-[8px] border border-line bg-ink-900 px-3 py-2 font-mono text-[12px] text-inktext outline-none ring-accent/30 focus:ring-2"
                placeholder={'{"openapi":"3.0.0","info":{"title":"…"},"paths":{}}'}
              />
              <span className="mt-1.5 block text-xs text-inktext-faint">JSON or YAML. Parsed by the same SpecParser as URL/file.</span>
            </label>
          ) : null}

          {mode !== "url" ? (
            <label className="block text-sm">
              <span className="mb-1.5 block text-inktext-muted">Live target (optional)</span>
              <input
                value={optionalTarget}
                onChange={(event) => setOptionalTarget(event.target.value)}
                className="w-full rounded-[8px] border border-line bg-ink-900 px-3 py-2 font-mono text-sm text-inktext outline-none ring-accent/30 focus:ring-2"
                placeholder="http://127.0.0.1:8000"
              />
              <span className="mt-1.5 block text-xs text-inktext-faint">
                Required to run BOLA, live auth probes, rate-limit, and mass assignment. Spec-only
                runs static checks and marks the rest as skipped.
              </span>
            </label>
          ) : null}

          {liveEnabled ? (
            <label className="block text-sm">
              <span className="mb-1.5 block text-inktext-muted">Identities</span>
              <select
                value={preset}
                onChange={(event) => setPreset(event.target.value)}
                className="w-full rounded-[8px] border border-line bg-ink-800 px-3 py-2 text-sm text-inktext outline-none ring-accent/30 focus:ring-2"
              >
                <option value="shopapi">shopapi — alice / bob / admin / anonymous</option>
              </select>
            </label>
          ) : null}

          {error ? (
            <p className="rounded-md border border-critical/30 bg-critical/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </p>
          ) : null}
          {progress ? (
            <div>
              <div className="mb-2 flex justify-between font-mono text-xs text-inktext-muted">
                <span>{progress.step}</span>
                <span className="tabular">{progress.percent}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-ink-700">
                <div
                  className="h-full bg-accent transition-all duration-150"
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
