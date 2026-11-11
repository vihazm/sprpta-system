import { TIME_ZONE } from "@/components/dashboard/dates";

// Dates are shown in Sri Lankan time, whatever the browser's own zone is.

const dayKey = (date: Date) => date.toLocaleDateString("en-CA", { timeZone: TIME_ZONE });
const clock = (date: Date) =>
  date.toLocaleTimeString("en-GB", { timeZone: TIME_ZONE, hour: "2-digit", minute: "2-digit" });

/** "Today, 09:31", "Yesterday, 16:40", or "12 Aug" for anything older. */
export function formatWhen(iso: string | null) {
  if (!iso) return "Never";
  const date = new Date(iso);
  const now = new Date();
  if (dayKey(date) === dayKey(now)) return `Today, ${clock(date)}`;
  if (dayKey(date) === dayKey(new Date(now.getTime() - 24 * 60 * 60 * 1000))) {
    return `Yesterday, ${clock(date)}`;
  }
  return formatDay(iso);
}

/** "12 Aug 2026" */
export function formatDay(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", {
    timeZone: TIME_ZONE,
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
