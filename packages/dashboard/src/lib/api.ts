/** Typed client for the Phase 5 scanner service. */

export const API_BASE = import.meta.env.VITE_API_BASE ?? "";
export const WS_BASE =
  import.meta.env.VITE_WS_BASE ??
  `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;

export type ScanStatus = "running" | "completed" | "failed" | string;

export interface SummaryStats {
  total_findings: number;
  by_severity: Record<string, number>;
  by_vuln_class: Record<string, number>;
}

export interface ScanListItem {
  id: number;
  target: string;
  started_at: string | null;
  finished_at: string | null;
  status: ScanStatus;
  summary: SummaryStats;
  error: string | null;
}

export interface ScoreFactor {
  name: string;
  score: number;
  max_score: number;
  reason: string;
}

export interface SeverityBreakdown {
  impact: number;
  exploitability: number;
  score: number;
  label: string;
  factors: ScoreFactor[];
}

export interface RequestEvidence {
  method: string;
  url: string;
  headers: Record<string, string>;
  body: unknown;
}

export interface ResponseEvidence {
  status: number;
  body: string;
}

export interface Evidence {
  request: RequestEvidence;
  response: ResponseEvidence;
}

export interface Finding {
  id: string;
  title: string;
  vuln_class: string;
  endpoint: string;
  severity_score: number;
  severity_label: string;
  confidence: number;
  evidence: Evidence[];
  poc_curl: string;
  remediation: string;
  business_impact: string;
  chain_id: string | null;
  detector_confidence: number;
  access_matrix: Record<string, Record<string, string>> | null;
  severity_breakdown: SeverityBreakdown | null;
}

export interface AttackChain {
  id: string;
  finding_ids: string[];
  narrative: string;
  max_severity_score: number;
  max_severity_label: string;
}

export interface SkippedCheck {
  check: string;
  reason: string;
}

export interface ScanDetail {
  id: number;
  target: string;
  started_at: string | null;
  finished_at: string | null;
  status: ScanStatus;
  error: string | null;
  findings: Finding[];
  chains: AttackChain[];
  access_matrix: Record<string, Record<string, string>> | null;
  summary: SummaryStats;
  skipped_checks?: SkippedCheck[];
}

export interface ScanAccepted {
  scan_id: number;
  status: ScanStatus;
}

export interface ReplayResult {
  request: RequestEvidence;
  response: ResponseEvidence;
  still_vulnerable: boolean;
}

export interface ScanDiff {
  a: number;
  b: number;
  new: string[];
  fixed: string[];
  persisting: string[];
}

export interface ProgressEvent {
  percent: number;
  step: string;
  status?: string | null;
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

export interface AIAnswer {
  text: string;
  configured: boolean;
  ai_generated: boolean;
}

async function request<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const { timeoutMs, ...rest } = init ?? {};
  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    signal: rest.signal ?? AbortSignal.timeout(timeoutMs ?? 15000),
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) detail = payload.detail;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export const api = {
  listScans: () => request<ScanListItem[]>("/scans"),

  getScan: (id: number) => request<ScanDetail>(`/scans/${id}`),

  getFinding: (scanId: number, findingKey: string) =>
    request<Finding>(`/scans/${scanId}/findings/${encodeURIComponent(findingKey)}`),

  startScan: (body: {
    target_base_url?: string;
    spec_text?: string;
    identities_preset: string;
  }) => request<ScanAccepted>("/scans", { method: "POST", body: JSON.stringify(body) }),

  replay: (scanId: number, findingKey: string) =>
    request<ReplayResult>(
      `/scans/${scanId}/findings/${encodeURIComponent(findingKey)}/replay`,
      { method: "POST" },
    ),

  diff: (a: number, b: number) => request<ScanDiff>(`/scans/diff?a=${a}&b=${b}`),

  explainFinding: (scanId: number, findingKey: string) =>
    request<AIAnswer>(`/scans/${scanId}/findings/${encodeURIComponent(findingKey)}/explain`, {
      method: "POST",
      timeoutMs: 45000,
    }),

  askScan: (scanId: number, question: string) =>
    request<AIAnswer>(`/scans/${scanId}/ask`, {
      method: "POST",
      body: JSON.stringify({ question }),
      timeoutMs: 45000,
    }),
};

export function connectProgress(
  scanId: number,
  onEvent: (event: ProgressEvent) => void,
  onClose: () => void,
): WebSocket {
  const socket = new WebSocket(`${WS_BASE}/scans/${scanId}/progress`);
  socket.onmessage = (message) => {
    try {
      onEvent(JSON.parse(message.data as string) as ProgressEvent);
    } catch {
      /* ignore malformed frames */
    }
  };
  socket.onclose = () => onClose();
  return socket;
}
