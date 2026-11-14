import type { Severity } from "@/components/dashboard/severity";

// Shapes used by the Level 1 office staff dashboard (UC-L1-12).

export type QueueKind = "portal" | "drafts" | "incomplete" | "duplicates";

export type QueueCount = { kind: QueueKind; title: string; note: string; count: number };

export type WaitingCase = {
  ref: string | null; // a draft has no reference number yet
  title: string;
  status: "Draft" | "Incomplete" | "Possible duplicate";
  age: string;
};

export type PortalSubmission = { title: string; meta: string };

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
  day: { entered: number; forwarded: number; stillOpen: number; thisWeek: number; thisMonth: number };
  queues: QueueCount[];
  waiting: WaitingCase[];
  portal: PortalSubmission[];
  sources: Count[]; // complaints this month by medium
  busiestThisWeek: { medium: string; count: number; total: number };
  lookup: { query: string; rows: { label: string; value: string }[] };
  areas: AreaTotal[]; // forwarded to each area officer this month
  transport: { bus: number; trishaw: number };
  severity: { severity: Severity; count: number }[];
  forwarded: ForwardedCase[];
};
