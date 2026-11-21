import { TIME_ZONE } from "@/components/dashboard/dates";
import type {
  CaseRow,
  DecisionAction,
  DecisionOutcome,
  HistoryEntry,
  RecommendationStatus,
  RecommendationType,
} from "./types";

// Words and dates for the Level 2 screens.

export const ACTION_LABEL: Record<DecisionAction, string> = {
  warning: "Warning",
  fine: "Fine",
  suspension: "Suspension",
  legal_action: "Legal action",
  no_action: "No action",
};

export const OUTCOME_LABEL: Record<DecisionOutcome, string> = {
  substantiated: "Substantiated",
  partly_substantiated: "Partly substantiated",
  not_substantiated: "Not substantiated",
};

// The longest text the server accepts in each box (see app/schemas/l2_cases.py).
export const LIMITS = { reasoning: 5000, summary: 2000, solution: 5000, escalation: 1000 };

/** What Level 1's check of the bus against the daily records found. */
export const BUS_CHECK_LABEL: Record<string, string> = {
  verified: "Verified against the daily record",
  corrected: "Corrected after the check",
  not_found: "Bus not found in the daily record",
  not_operated: "Bus did not operate that day",
  trip_cancelled: "Trip was cancelled",
  unverified: "Not verified",
};

export const RECOMMENDATION_TYPE_LABEL: Record<RecommendationType, string> = {
  improvement: "Improvement suggestion",
  commendation: "Commendation",
};

export const RECOMMENDATION_STATUS_LABEL: Record<RecommendationStatus, string> = {
  new: "New",
  acknowledged: "Acknowledged",
  under_consideration: "Under consideration",
  accepted_implemented: "Accepted, implemented",
  declined: "Declined",
  commendation_verified: "Commendation verified",
};

export const RECOMMENDATION_TONE: Record<RecommendationStatus, "info" | "ok" | "warn" | "brand" | "crit"> = {
  new: "info",
  acknowledged: "ok",
  under_consideration: "warn",
  accepted_implemented: "ok",
  declined: "crit",
  commendation_verified: "brand",
};

/** "21 Nov 2026" */
export function shortDate(iso: string | null): string {
  if (!iso) return "–";
  return new Date(iso).toLocaleDateString("en-GB", { timeZone: TIME_ZONE, day: "numeric", month: "short", year: "numeric" });
}

/** "21 Nov" */
export function dayMonth(iso: string | null): string {
  if (!iso) return "–";
  return new Date(iso).toLocaleDateString("en-GB", { timeZone: TIME_ZONE, day: "numeric", month: "short" });
}

/** "21 Nov, 17:00" */
export function dayMonthTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    timeZone: TIME_ZONE,
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** "21 Nov 2026, 09:40" */
export function dateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    timeZone: TIME_ZONE,
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** "40 min", "5 h", "3 d" */
function span(ms: number): string {
  const minutes = Math.max(1, Math.round(Math.abs(ms) / 60000));
  if (minutes < 60) return `${minutes} min`;
  if (minutes < 60 * 24) return `${Math.round(minutes / 60)} h`;
  return `${Math.round(minutes / (60 * 24))} d`;
}

/** The next time target in words: "Decide in 5 h", "Overdue by 3 h", "With Level 3". */
export function dueText(c: Pick<CaseRow, "status" | "dueKind" | "dueAt" | "overdue">): string {
  if (!c.dueKind || !c.dueAt) return c.status === "escalated" ? "With Level 3" : c.status === "closed" ? "Closed" : "–";
  const left = new Date(c.dueAt).getTime() - Date.now();
  if (c.overdue || left < 0) return `Overdue by ${span(left)}`;
  return `${c.dueKind === "decide" ? "Decide" : "Close"} in ${span(left)}`;
}

/** "Same day", "1 day", "7 days" */
export function days(count: number): string {
  return count === 0 ? "Same day" : `${count} ${count === 1 ? "day" : "days"}`;
}

export function fileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} kB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const HISTORY_TEXT: Record<string, string> = {
  "complaint.create": "Complaint entered",
  "complaint.incomplete": "Saved as incomplete",
  "complaint.forward": "Forwarded to the area officer",
  "complaint.review": "Opened, now under review",
  "complaint.escalate": "Escalated to Level 3",
  "decision.create": "Decision recorded",
  "decision.update": "Decision changed",
  "solution_document.create": "Solution document created",
  "attachment.add": "Attachment added",
  "attachment.remove": "Attachment removed",
  "duplicate.decide": "Duplicate check decided",
  "complaint.bus_selected": "Bus confirmed against the daily records",
  "complaint.bus_cleared": "Bus selection cleared",
};

/** What happened, in words, for the History panel. */
export function historyText(entry: HistoryEntry): string {
  return HISTORY_TEXT[entry.action] ?? entry.action.replace(/[._]/g, " ").replace(/^\w/, (l) => l.toUpperCase());
}
