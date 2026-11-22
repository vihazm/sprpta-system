import { api, type ApiResult } from "@/lib/api-client";
import type { Severity } from "@/components/dashboard/severity";
import type {
  AreaStatistics,
  CaseDetail,
  CasePage,
  CaseQuery,
  CaseRow,
  CaseStatus,
  DashboardData,
  DecisionAction,
  DecisionOutcome,
  RecommendationDetail,
  RecommendationPage,
  RecommendationRow,
  RecommendationStatus,
  RecommendationType,
} from "./types";

// The calls behind the Level 2 screens. The API speaks snake_case and the components camelCase, so the
// conversion happens here and nowhere else.

const CASES = "/api/l2/cases";

type CaseRowIn = {
  id: number;
  reference_number: string;
  status: CaseStatus;
  subject: string | null;
  vehicle_number: string | null;
  severity: string;
  forwarded_at: string | null;
  due_kind: CaseRow["dueKind"];
  due_at: string | null;
  overdue: boolean;
};

type RecommendationIn = {
  id: number;
  recommendation_type: RecommendationType;
  status: RecommendationStatus;
  title: string;
  received_date: string | null;
  created_at: string;
};

function mapData<A, B>(result: ApiResult<A>, convert: (data: A) => B): ApiResult<B> {
  return result.ok ? { ok: true, data: convert(result.data) } : result;
}

function toRow(r: CaseRowIn): CaseRow {
  return {
    id: r.id,
    reference: r.reference_number,
    status: r.status,
    subject: r.subject,
    vehicle: r.vehicle_number,
    severity: r.severity as Severity,
    forwardedAt: r.forwarded_at,
    dueKind: r.due_kind,
    dueAt: r.due_at,
    overdue: r.overdue,
  };
}

function toRecommendation(r: RecommendationIn): RecommendationRow {
  return {
    id: r.id,
    type: r.recommendation_type,
    status: r.status,
    title: r.title,
    receivedDate: r.received_date,
    createdAt: r.created_at,
  };
}

// ---------------------------------------------------------------- dashboard and list

export async function loadDashboard(): Promise<ApiResult<DashboardData>> {
  const result = await api<{
    counts: Record<string, number>;
    arrived_today: number;
    decided_today: number;
    closed_this_month: number;
    urgent: number;
    next_case_id: number | null;
    overdue: CaseRowIn[];
    average_decide_days: number | null;
    targets: { severity: string; forward_days: number; decide_days: number; close_days: number }[];
    recommendations: RecommendationIn[];
    statistics: AreaStatistics;
  }>("/api/l2/dashboard");
  return mapData(result, (b) => ({
    counts: b.counts,
    arrivedToday: b.arrived_today,
    decidedToday: b.decided_today,
    closedThisMonth: b.closed_this_month,
    urgent: b.urgent,
    nextCaseId: b.next_case_id,
    overdue: b.overdue.map(toRow),
    averageDecideDays: b.average_decide_days,
    targets: b.targets.map((t) => ({
      severity: t.severity as Severity,
      forwardDays: t.forward_days,
      decideDays: t.decide_days,
      closeDays: t.close_days,
    })),
    recommendations: b.recommendations.map(toRecommendation),
    statistics: b.statistics, // its fields are single words, so the shape is the same on both sides
  }));
}

export async function listCases(query: CaseQuery): Promise<ApiResult<CasePage>> {
  const params = new URLSearchParams({ sort: query.sort, page: String(query.page) });
  if (query.status) params.set("status", query.status);
  if (query.severity) params.set("severity", query.severity);
  if (query.search) params.set("search", query.search);
  const result = await api<{ items: CaseRowIn[]; total: number; page: number; page_size: number; counts: Record<string, number> }>(
    `${CASES}?${params}`,
  );
  return mapData(result, (b) => ({ items: b.items.map(toRow), total: b.total, page: b.page, pageSize: b.page_size, counts: b.counts }));
}

// ---------------------------------------------------------------- one case

type CaseDetailIn = CaseRowIn & {
  description: string | null;
  category: string | null;
  target: string | null;
  accused: string | null;
  medium: string | null;
  is_anonymous: boolean;
  complainant: string | null;
  has_contact: boolean;
  complainant_type: string | null;
  complaint_date: string | null;
  incident_time: string | null;
  incident_location: string | null;
  bus_verification: string | null;
  driver_on_duty: string | null;
  conductor_on_duty: string | null;
  vehicle_type: string | null;
  permit_number: string | null;
  owner: string | null;
  route_stand: string | null;
  area: string | null;
  registered_at: string | null;
  forwarded_by: string | null;
  attachments: { id: number; file_name: string; mime_type: string; size_bytes: number }[];
  earlier: {
    id: number;
    reference_number: string;
    subject: string | null;
    status: string;
    registered_at: string | null;
    area: string | null;
    own_area: boolean;
    action: DecisionAction | null;
    outcome: DecisionOutcome | null;
  }[];
  duplicates: { reference_number: string | null; link_type: CaseDetail["duplicates"][number]["link"] }[];
  history: {
    occurred_at: string;
    actor_name: string | null;
    actor_role: string;
    action: string;
    from_status: string | null;
    to_status: string | null;
    reason: string | null;
  }[];
  decision: {
    action: DecisionAction;
    outcome: DecisionOutcome;
    reasoning: string;
    decided_by: string;
    decided_at: string;
  } | null;
  solution_document: {
    summary_text: string;
    verdict_text: string;
    solution_details: string | null;
    generated_by: string;
    generated_at: string;
  } | null;
  escalation: { reason: string; escalated_by: string; escalated_at: string } | null;
};

function toDetail(c: CaseDetailIn): CaseDetail {
  return {
    ...toRow(c),
    description: c.description,
    category: c.category,
    target: c.target,
    accused: c.accused,
    medium: c.medium,
    isAnonymous: c.is_anonymous,
    complainant: c.complainant,
    hasContact: c.has_contact,
    complainantType: c.complainant_type,
    complaintDate: c.complaint_date,
    incidentTime: c.incident_time,
    incidentLocation: c.incident_location,
    busVerification: c.bus_verification,
    driverOnDuty: c.driver_on_duty,
    conductorOnDuty: c.conductor_on_duty,
    vehicleType: c.vehicle_type,
    permit: c.permit_number,
    owner: c.owner,
    routeStand: c.route_stand,
    area: c.area,
    registeredAt: c.registered_at,
    forwardedBy: c.forwarded_by,
    attachments: c.attachments.map((a) => ({ id: a.id, name: a.file_name, type: a.mime_type, size: a.size_bytes })),
    earlier: c.earlier.map((e) => ({
      id: e.id,
      reference: e.reference_number,
      subject: e.subject,
      status: e.status,
      registeredAt: e.registered_at,
      area: e.area,
      ownArea: e.own_area,
      action: e.action,
      outcome: e.outcome,
    })),
    duplicates: c.duplicates.map((d) => ({ reference: d.reference_number, link: d.link_type })),
    history: c.history.map((h) => ({
      occurredAt: h.occurred_at,
      actor: h.actor_name,
      role: h.actor_role,
      action: h.action,
      fromStatus: h.from_status,
      toStatus: h.to_status,
      reason: h.reason,
    })),
    decision: c.decision && {
      action: c.decision.action,
      outcome: c.decision.outcome,
      reasoning: c.decision.reasoning,
      decidedBy: c.decision.decided_by,
      decidedAt: c.decision.decided_at,
    },
    solutionDocument: c.solution_document && {
      summary: c.solution_document.summary_text,
      verdict: c.solution_document.verdict_text,
      details: c.solution_document.solution_details,
      generatedBy: c.solution_document.generated_by,
      generatedAt: c.solution_document.generated_at,
    },
    escalation: c.escalation && {
      reason: c.escalation.reason,
      escalatedBy: c.escalation.escalated_by,
      escalatedAt: c.escalation.escalated_at,
    },
  };
}

export async function loadCase(id: number): Promise<ApiResult<CaseDetail>> {
  return mapData(await api<CaseDetailIn>(`${CASES}/${id}`), toDetail);
}

/** Opening a Forwarded case moves it to Under review; any other case comes back unchanged. */
export async function startReview(id: number): Promise<ApiResult<CaseDetail>> {
  return mapData(await api<CaseDetailIn>(`${CASES}/${id}/review`, { method: "POST" }), toDetail);
}

export async function recordDecision(
  id: number,
  decision: { action: DecisionAction; outcome: DecisionOutcome; reasoning: string },
): Promise<ApiResult<CaseDetail>> {
  return mapData(await api<CaseDetailIn>(`${CASES}/${id}/decision`, { method: "PUT", body: decision }), toDetail);
}

export async function createSolutionDocument(
  id: number,
  document: { summary: string; solutionDetails: string },
): Promise<ApiResult<CaseDetail>> {
  const body = { summary: document.summary, solution_details: document.solutionDetails };
  return mapData(await api<CaseDetailIn>(`${CASES}/${id}/solution-document`, { method: "POST", body }), toDetail);
}

export async function escalateCase(id: number, reason: string): Promise<ApiResult<CaseDetail>> {
  return mapData(await api<CaseDetailIn>(`${CASES}/${id}/escalate`, { method: "POST", body: { reason } }), toDetail);
}

/** Where the browser opens a file of the case: an attachment, or the solution document PDF. */
export const attachmentUrl = (caseId: number, attachmentId: number) => `${CASES}/${caseId}/attachments/${attachmentId}`;
export const solutionDocumentUrl = (caseId: number) => `${CASES}/${caseId}/solution-document`;

// ---------------------------------------------------------------- recommendations

export async function listRecommendations(query: {
  type: RecommendationType | null;
  status: RecommendationStatus | null;
  search: string;
  page: number;
}): Promise<ApiResult<RecommendationPage>> {
  const params = new URLSearchParams({ page: String(query.page) });
  if (query.type) params.set("type", query.type);
  if (query.status) params.set("status", query.status);
  if (query.search) params.set("search", query.search);
  const result = await api<{
    items: RecommendationIn[];
    total: number;
    page: number;
    page_size: number;
    counts: Record<string, number>;
  }>(`/api/l2/recommendations?${params}`);
  return mapData(result, (b) => ({
    items: b.items.map(toRecommendation),
    total: b.total,
    page: b.page,
    pageSize: b.page_size,
    counts: b.counts,
  }));
}

export async function loadRecommendation(id: number): Promise<ApiResult<RecommendationDetail>> {
  const result = await api<
    RecommendationIn & {
      details: string;
      medium: string | null;
      person: string | null;
      entered_by: string;
      status_changed_at: string | null;
    }
  >(`/api/l2/recommendations/${id}`);
  return mapData(result, (r) => ({
    ...toRecommendation(r),
    details: r.details,
    medium: r.medium,
    person: r.person,
    enteredBy: r.entered_by,
    statusChangedAt: r.status_changed_at,
  }));
}
