import type { Severity } from "@/components/dashboard/severity";

// Shapes used by the Level 1 office staff dashboard (UC-L1-12).

export type QueueKind = "portal" | "drafts" | "incomplete" | "duplicates";

// Who a complaint is against, as the Complaints page and the dashboard count it.
export type TargetFilter = "driver" | "conductor" | "owner" | "bus_service" | "other" | "unclassified";

// The numbers on the Level 1 dashboard, from GET /api/l1/dashboard.
export type DashboardSummary = {
  day: { entered: number; forwarded: number; stillOpen: number }; // this officer's own day, in Sri Lankan time
  weekEntered: number;
  monthEntered: number;
  queues: Record<QueueKind, number>; // the shared Level 1 queues
  byTarget: Record<TargetFilter, number>; // this officer's own complaints, by who they are against
  waiting: WaitingCase[];
  portal: PortalSubmission[];
};

export type WaitingCase = {
  id: number;
  reference: string | null; // a draft has no reference number yet
  title: string;
  status: "Draft" | "Incomplete";
  possibleDuplicate: boolean;
  ageMinutes: number;
};

export type PortalSubmission = { id: number; title: string; complainant: string | null; ageMinutes: number };
export type Count = { label: string; count: number };

export type AreaTotal = { name: string; count: number; hasOfficer: boolean };

export type ForwardedCase = {
  ref: string;
  severity: Severity;
  title: string;
  area: string;
  when: string;
  message: "sent" | "none" | "failed"; // the registration message to the complainant
};

export type L1DashboardData = {
  sources: Count[]; // complaints this month by medium
  busiestThisWeek: { medium: string; count: number; total: number };
  lookup: { query: string; rows: { label: string; value: string }[] };
  areas: AreaTotal[]; // forwarded to each area officer this month
  transport: { bus: number; trishaw: number };
  severity: { severity: Severity; count: number }[];
  forwarded: ForwardedCase[];
};
