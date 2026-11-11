import type { Approval } from "@/components/dashboard/ApprovalList";
import type { Segment } from "@/components/dashboard/Donut";
import type { Severity } from "@/components/dashboard/severity";

// Shapes used by the Level 3 chairman dashboard (UC-L3-01 to UC-L3-09).

export type EscalatedCase = {
  ref: string;
  severity: Severity;
  title: string;
  escalatedAgo: string;
  reason: string; // why Level 2 passed it up
  officer: string; // the area and the officer who escalated it
};

export type AiAnswer = { question: string; answer: string; basedOn: string[]; suggestions: string[] };

export type MonthVolume = { label: string; received: number; closed: number };

export type TransportMode = { label: string; cases: number; closedPercent: number; averageDays: number; color: string };

export type Count = { label: string; count: number };

export type OverdueCase = {
  ref: string;
  title: string;
  area: string;
  step: string; // which target passed
  severity: Severity;
  overdueBy: string;
};

export type RatingBand = "Excellent" | "Good" | "Needs improvement" | "Poor";

export type RatingRow = {
  name: string;
  role: string;
  substantiated: number;
  pending: number;
  commendations: number;
  score: number;
  band: RatingBand;
};

export type Appeal = { title: string; when: string; detail: string; action: string };

export type RecommendationToManage = {
  ref: string;
  title: string;
  kind: string;
  enteredBy: string;
  status: string;
};

export type AuditEntry = { time: string; user: string; text: string; ref: string };

export type L3DashboardData = {
  month: { received: number; closed: number; open: number; rejected: number; overdue: number };
  escalatedTotal: number;
  escalated: EscalatedCase[];
  ai: AiAnswer;
  volume: MonthVolume[];
  statuses: Segment[]; // where this month's cases stand
  overdueAtLevel2: number;
  transport: TransportMode[];
  areas: Count[];
  sources: Count[];
  rejections: Count[];
  overdue: OverdueCase[];
  onTime: { label: string; percent: number }[];
  approvals: Approval[];
  ratings: RatingRow[];
  bands: { band: RatingBand; range: string; count: number }[];
  appeals: Appeal[];
  recommendationStatuses: Count[];
  recommendations: RecommendationToManage[];
  audit: AuditEntry[];
};
