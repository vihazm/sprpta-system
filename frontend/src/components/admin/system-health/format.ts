import { TIME_ZONE } from "../users/format";

// Small formatters for the System health page. Times are shown in Sri Lankan time.

const dayKey = (date: Date) => date.toLocaleDateString("en-CA", { timeZone: TIME_ZONE });
const isToday = (date: Date) => dayKey(date) === dayKey(new Date());
const clock = (date: Date) =>
  date.toLocaleTimeString("en-GB", { timeZone: TIME_ZONE, hour: "2-digit", minute: "2-digit" });
const dayMonth = (date: Date) =>
  date.toLocaleDateString("en-GB", { timeZone: TIME_ZONE, day: "numeric", month: "short" });

/** "09:12" for today, "10 Nov, 09:12" for earlier days. */
export function formatEventTime(iso: string) {
  const date = new Date(iso);
  return isToday(date) ? clock(date) : `${dayMonth(date)}, ${clock(date)}`;
}

/** "today 10:30", or "10 Nov, 10:30" for an earlier day. */
export function formatSince(iso: string) {
  const date = new Date(iso);
  return isToday(date) ? `today ${clock(date)}` : `${dayMonth(date)}, ${clock(date)}`;
}

/** "10 Nov" */
export function formatShortDay(iso: string) {
  return dayMonth(new Date(iso));
}

/** "52 seconds ago", "3 minutes ago", "2 hours ago". */
export function formatAgo(iso: string) {
  const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return `${seconds} second${seconds === 1 ? "" : "s"} ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.round(minutes / 60);
  return `${hours} hour${hours === 1 ? "" : "s"} ago`;
}

export function formatDuration(minutes: number) {
  return `${minutes} minute${minutes === 1 ? "" : "s"}`;
}

/** "9.1 MB", "1.8 GB" */
export function formatBytes(bytes: number) {
  const units = ["B", "kB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1000 && unit < units.length - 1) {
    value /= 1000;
    unit += 1;
  }
  return `${unit === 0 ? value : value.toFixed(1)} ${units[unit]}`;
}
