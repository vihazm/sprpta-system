import type { ComplaintStatus } from "@/components/l1/entry/types";

// How a complaint's status is shown to Level 1. Everything that has left Level 1 reads as Forwarded: Level 1 does
// not see how Level 2 or Level 3 are handling it.
export type StatusTone = "info" | "warn" | "ok" | "crit" | "brand";

export function statusLabel(status: string): string {
  switch (status) {
    case "draft":
      return "Draft";
    case "incomplete":
      return "Incomplete";
    case "submitted":
      return "Awaiting your check";
    case "rejected":
      return "Rejected";
    default:
      return "Forwarded";
  }
}

export const STATUS_TONE: Record<string, StatusTone> = {
  Draft: "info",
  Incomplete: "warn",
  "Awaiting your check": "brand",
  Rejected: "crit",
  Forwarded: "ok",
};

/** "20 m", "3 h", "2 d": how long ago, from a number of minutes. */
export function ageText(minutes: number): string {
  if (minutes < 60) return `${minutes} m`;
  if (minutes < 60 * 24) return `${Math.floor(minutes / 60)} h`;
  return `${Math.floor(minutes / (60 * 24))} d`;
}

export type { ComplaintStatus };