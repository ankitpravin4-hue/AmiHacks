import { useState } from "react";
import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ScanDetail } from "@/lib/api";
import { buildScanReportHtml } from "@/lib/reportHtml";

export function DownloadReportButton({
  scan,
  variant = "outline",
}: {
  scan: ScanDetail;
  variant?: "default" | "outline";
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onClick = async () => {
    setBusy(true);
    setError(null);
    try {
      if (scan.status === "running") {
        throw new Error("This scan is still running. Wait until it finishes, then download the advisory report.");
      }
      if (scan.status === "failed") {
        throw new Error(scan.error || "This scan failed, so there is no complete report to download.");
      }
      await new Promise((resolve) => window.setTimeout(resolve, 80));
      const html = buildScanReportHtml(scan);
      const blob = new Blob([html], { type: "text/html;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `sentinelapi-report-${scan.id}.html`;
      link.rel = "noopener";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate the advisory report.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-w-0 flex-col items-end gap-1">
      <Button type="button" variant={variant} onClick={() => void onClick()} disabled={busy}>
        <Download className="h-4 w-4" />
        {busy ? "Preparing report…" : "Download Report"}
      </Button>
      {error ? <p className="max-w-xs text-right text-xs text-critical">{error}</p> : null}
    </div>
  );
}
