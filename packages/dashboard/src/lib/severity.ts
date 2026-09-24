export type SeverityLabel = "Critical" | "High" | "Medium" | "Low" | string;

export const SEVERITY_ORDER: Record<string, number> = {
  Critical: 4,
  High: 3,
  Medium: 2,
  Low: 1,
};

export function severityColor(label: SeverityLabel): string {
  switch (label) {
    case "Critical":
      return "#e5484d";
    case "High":
      return "#e67a2e";
    case "Medium":
      return "#d4a017";
    default:
      return "#8b93a7";
  }
}

export function severityBadgeClass(label: SeverityLabel): string {
  switch (label) {
    case "Critical":
      return "bg-critical/15 text-critical border-critical/30";
    case "High":
      return "bg-high/15 text-high border-high/30";
    case "Medium":
      return "bg-medium/15 text-medium border-medium/30";
    default:
      return "bg-slate-500/15 text-low border-slate-500/30";
  }
}

export function riskFromFindings(scores: number[]): { score: number; label: SeverityLabel } {
  if (scores.length === 0) return { score: 0, label: "Low" };
  const score = Math.max(...scores);
  if (score >= 9) return { score, label: "Critical" };
  if (score >= 7) return { score, label: "High" };
  if (score >= 4) return { score, label: "Medium" };
  return { score, label: "Low" };
}
