import type { Severity } from "@/components/dashboard/severity";

// Shapes used by the Level 2 area officer screens (UC-L2-01 to UC-L2-08), in the components' camelCase.

/** The statuses a case can have once it reaches Level 2 (UI Flow 1.2). Overdue is a flag, never a status. */
export type CaseStatus =
  | "forwarded"
  | "under_review"
  | "awaiting_implementation"
  | "done_awaiting_approval"
  | "escalated"
  | "closed";

/** A status to filter the cases by, or Overdue. */
export type CaseFilter = CaseStatus | "overdue";
export type CaseSort = "urgent" | "newest";
export type DueKind = "decide" | "close"; // decide-by while it waits for a decision, close-by after that

export type CaseRow = {
  id: number;
  reference: string;
  status: CaseStatus;
  subject: string | null;
  vehicle: string | null;
  severity: Severity;
  forwardedAt: string | null;
  dueKind: DueKind | null;
  dueAt: string | null;
  overdue: boolean;
};

export type CaseQuery = {
  status: CaseFilter | null;
  severity: Severity | null;
  search: string;
  sort: CaseSort;
  page: number;
};

export type CasePage = {
  items: CaseRow[];
  total: number;
  page: number;
  pageSize: number;
  counts: Record<string, number>; // per status, plus "all" and "overdue"
};

export type TimeTarget = { severity: Severity; forwardDays: number; decideDays: number; closeDays: number };

export type RecommendationType = "improvement" | "commendation";
export type RecommendationStatus =
  | "new"
  | "acknowledged"
  | "under_consideration"
  | "accepted_implemented"
  | "declined"
  | "commendation_verified";

export type RecommendationRow = {
  id: number;
  type: RecommendationType;
  status: RecommendationStatus;
  title: string;
  receivedDate: string | null;
  createdAt: string;
};

export type RecommendationPage = {
  items: RecommendationRow[];
  total: number;
  page: number;
  pageSize: number;
  counts: Record<string, number>; // per status, plus "all"
};

export type RecommendationDetail = RecommendationRow & {
  details: string;
  medium: string | null;
  person: string | null; // the person commended
  enteredBy: string;
  statusChangedAt: string | null;
};

export type DashboardData = {
  counts: Record<string, number>; // the area's cases per status, plus "all" and "overdue"
  arrivedToday: number;
  decidedToday: number;
  closedThisMonth: number;
  urgent: number; // critical cases still waiting for a decision
  nextCaseId: number | null;
  overdue: CaseRow[];
  averageDecideDays: number | null;
  targets: TimeTarget[];
  recommendations: RecommendationRow[];
};

export type DecisionAction = "warning" | "fine" | "suspension" | "legal_action" | "no_action";
export type DecisionOutcome = "substantiated" | "partly_substantiated" | "not_substantiated";

export type HistoryEntry = {
  occurredAt: string;
  actor: string | null;
  role: string;
  action: string;
  fromStatus: string | null;
  toStatus: string | null;
  reason: string | null;
};

export type CaseDetail = CaseRow & {
  description: string | null;
  category: string | null;
  target: string | null; // who the complaint is against
  accused: string | null;
  medium: string | null;
  isAnonymous: boolean;
  complainant: string | null;
  complainantType: string | null; // passenger, driver, conductor, owner or other
  hasContact: boolean;
  complaintDate: string | null;
  incidentTime: string | null;
  incidentLocation: string | null;
  busVerification: string | null; // what Level 1's check of the bus against the daily records found
  driverOnDuty: string | null;
  conductorOnDuty: string | null;
  vehicleType: string | null;
  permit: string | null;
  owner: string | null;
  routeStand: string | null;
  area: string | null;
  registeredAt: string | null;
  forwardedBy: string | null;
  attachments: { id: number; name: string; type: string; size: number }[];
  earlier: {
    id: number;
    reference: string;
    subject: string | null;
    status: string;
    registeredAt: string | null;
    action: DecisionAction | null;
    outcome: DecisionOutcome | null;
  }[];
  duplicates: { reference: string | null; link: "not_duplicate" | "duplicate_of" | "related" }[];
  history: HistoryEntry[];
  decision: {
    action: DecisionAction;
    outcome: DecisionOutcome;
    reasoning: string;
    decidedBy: string;
    decidedAt: string;
  } | null;
  solutionDocument: {
    summary: string;
    verdict: string;
    details: string | null;
    generatedBy: string;
    generatedAt: string;
  } | null;
  escalation: { reason: string; escalatedBy: string; escalatedAt: string } | null;
};
