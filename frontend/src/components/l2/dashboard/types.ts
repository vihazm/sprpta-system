import type { Approval } from "@/components/dashboard/ApprovalList";
import type { Severity } from "@/components/dashboard/severity";

// Shapes used by the Level 2 area officer dashboard (UC-L2-01 to UC-L2-08).

export type StageKind = "forwarded" | "review" | "implementation" | "approval" | "escalated";

export type StageCount = { kind: StageKind; label: string; count: number };

export type ReviewedCase = {
  ref: string;
  severity: Severity;
  title: string;
  forwardedBy: string;
  forwardedAgo: string;
  decideWithin: string; // the time target, for example "1 day"
  dueIn: string;
  facts: { label: string; value: string; accent?: boolean }[];
  story: string;
  attachments: string[];
  ai: { readyIn: string; suggestion: string; clauses: string[] };
  earlier: { ref: string; title: string; outcome: string; when: string }[];
};

export type UrgentCase = {
  ref: string;
  title: string;
  severity: Severity;
  due: string;
  overdue: boolean;
};

type SentMessage = { ref: string; text: string; time: string; failed: boolean };

export type RecommendationItem = { ref: string; title: string; kind: string; status: string };

export type EscalatedCase = { ref: string; title: string; when: string; reason: string };

export type TimeTarget = { severity: Severity; forward: string; decide: string; close: string };

export type ClosedCase = { ref: string; title: string; outcome: string; when: string };

export type L2DashboardData = {
  day: { arrived: number; decided: number };
  month: { closed: number; received: number; open: number; overdue: number };
  openStages: number;
  caseToReview: ReviewedCase;
  stages: StageCount[];
  urgent: UrgentCase[];
  urgentSolved: { solved: number; total: number };
  averageDays: { actual: number; target: number };
  approvals: Approval[];
  moreWithStaff: number;
  ages: { label: string; count: number; color: string }[];
  overAgeNote: string;
  messages: SentMessage[];
  recommendations: RecommendationItem[];
  escalated: EscalatedCase[];
  targets: TimeTarget[];
  closed: ClosedCase[];
};
