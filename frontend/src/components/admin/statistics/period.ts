import { TIME_ZONE } from "@/components/dashboard/dates";

// The quick periods above the statistics. Dates are Sri Lankan calendar days, as the backend counts them.

export type Period = "30d" | "90d" | "12m" | "all" | "custom";

export const PERIODS: { value: Exclude<Period, "custom">; label: string }[] = [
  { value: "30d", label: "Last 30 days" },
  { value: "90d", label: "Last 90 days" },
  { value: "12m", label: "Last 12 months" },
  { value: "all", label: "All time" },
];

/** Today in Sri Lanka, as yyyy-mm-dd. */
export function today(now = new Date()) {
  return now.toLocaleDateString("en-CA", { timeZone: TIME_ZONE });
}

/** The first and last day of a quick period, both included. "All time" has no limits. */
export function periodDates(period: Exclude<Period, "custom">, now = new Date()) {
  if (period === "all") return { from: "", to: "" };
  const to = today(now);
  const start = new Date(`${to}T00:00:00Z`);
  if (period === "12m") {
    start.setUTCFullYear(start.getUTCFullYear() - 1);
    start.setUTCDate(start.getUTCDate() + 1);
  } else {
    start.setUTCDate(start.getUTCDate() - (period === "30d" ? 29 : 89));
  }
  return { from: start.toISOString().slice(0, 10), to };
}
