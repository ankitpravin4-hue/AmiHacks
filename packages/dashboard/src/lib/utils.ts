import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatWhen(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

const CLASS_LABELS: Record<string, string> = {
  bola: "BOLA",
  excessive_data_exposure: "Excessive Data Exposure",
  broken_authentication: "Broken Authentication",
  missing_rate_limit: "Missing Rate Limit",
  mass_assignment: "Mass Assignment",
  missing_security: "Missing Security",
  sql_injection: "SQL Injection",
};

export function prettyClass(vulnClass: string): string {
  return CLASS_LABELS[vulnClass] ?? vulnClass.replaceAll("_", " ");
}

export function chainTitle(chainId: string): string {
  if (chainId === "account-takeover") return "Account takeover";
  if (chainId === "cross-user-data-theft") return "Cross-user data theft";
  return chainId.replaceAll("-", " ");
}
