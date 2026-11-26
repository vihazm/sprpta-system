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
  id: number;
  ref: string | null;
  severity: Severity | null;
  title: string;
  area: string | null;
  when: string; // for example "10 min ago"
  message: "sent" | "not_sent" | "none"; // the registration message: sent, due but not sent, or no contact
};

// The lower cards of the dashboard, from GET /api/l1/dashboard/overview: this officer's own work.
export type DashboardOverview = {
  monthTotal: number;
  sources: Count[]; // complaints this month by medium
  busiestWeek: { medium: string | null; count: number; total: number };
  areas: AreaTotal[]; // forwarded to each area officer this month
  forwardedTotal: number;
  transport: { bus: number; trishaw: number; unknown: number };
  severity: { severity: Severity; count: number }[];
  forwarded: ForwardedCase[];
};
