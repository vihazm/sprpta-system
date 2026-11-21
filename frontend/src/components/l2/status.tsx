import type { CaseStatus } from "./types";

// How each case status looks: its name (UI Flow 1.2), and the soft colours used on tiles and tags.
export const STATUS_ORDER: CaseStatus[] = [
  "forwarded",
  "under_review",
  "awaiting_implementation",
  "done_awaiting_approval",
  "escalated",
  "closed",
];

export const STATUS_LABEL: Record<CaseStatus, string> = {
  forwarded: "Forwarded",
  under_review: "Under review",
  awaiting_implementation: "Awaiting implementation",
  done_awaiting_approval: "Done, awaiting approval",
  escalated: "Escalated",
  closed: "Closed",
};

export const STATUS_STYLE: Record<CaseStatus, string> = {
  forwarded: "bg-slate-100 text-slate-700",
  under_review: "bg-sky-50 text-sky-800",
  awaiting_implementation: "bg-crimson/10 text-crimson-hover",
  done_awaiting_approval: "bg-emerald-50 text-emerald-800",
  escalated: "bg-amber-50 text-amber-800",
  closed: "bg-gray-200 text-gray-700",
};

/** Cases the officer still has to decide; only these can be decided or escalated. */
export const isDeciding = (status: CaseStatus) => status === "forwarded" || status === "under_review";

/** The status tag shown on every case (shared component, UI Flow 7). */
export function StatusTag({ status }: { status: CaseStatus }) {
  return (
    <span
      className={`inline-flex whitespace-nowrap rounded-full px-[0.7rem] py-[0.25rem] text-[0.72rem] font-bold ${STATUS_STYLE[status]}`}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}
