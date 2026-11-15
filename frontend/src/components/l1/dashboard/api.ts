import { api, type ApiResult } from "@/lib/api-client";
import { statusLabel } from "@/components/l1/status";
import type { DashboardSummary, QueueKind, TargetFilter, WaitingCase } from "./types";

export type { TargetFilter } from "./types";

// The calls behind the Level 1 dashboard and the Complaints page. The API speaks snake_case and the components
// camelCase, so the conversion happens here and nowhere else.

const COMPLAINTS = "/api/l1/complaints";

function mapData<A, B>(result: ApiResult<A>, convert: (data: A) => B): ApiResult<B> {
  return result.ok ? { ok: true, data: convert(result.data) } : result;
}

export async function loadDashboard(): Promise<ApiResult<DashboardSummary>> {
  const result = await api<{
    day: { entered: number; forwarded: number; still_open: number };
    week_entered: number;
    month_entered: number;
    queues: Record<QueueKind, number>;
    waiting: {
      id: number;
      reference_number: string | null;
      subject: string | null;
      status: string;
      possible_duplicate: boolean;
      age_minutes: number;
    }[];
    portal: { id: number; subject: string | null; complainant: string | null; age_minutes: number }[];
    by_target: Record<TargetFilter, number>;
  }>("/api/l1/dashboard");
  return mapData(result, (b) => ({
    day: { entered: b.day.entered, forwarded: b.day.forwarded, stillOpen: b.day.still_open },
    weekEntered: b.week_entered,
    monthEntered: b.month_entered,
    queues: b.queues,
    byTarget: b.by_target,
    waiting: b.waiting.map(
      (w): WaitingCase => ({
        id: w.id,
        reference: w.reference_number,
        title: w.subject ?? "No subject yet",
        status: statusLabel(w.status) as WaitingCase["status"],
        possibleDuplicate: w.possible_duplicate,
        ageMinutes: w.age_minutes,
      }),
    ),
    portal: b.portal.map((p) => ({
      id: p.id,
      title: p.subject ?? "No subject",
      complainant: p.complainant,
      ageMinutes: p.age_minutes,
    })),
  }));
}

export type ReferenceHit = {
  id: number;
  reference: string;
  status: string; // as Level 1 sees it: Draft, Incomplete, Forwarded or Rejected
  editable: boolean;
  subject: string | null;
  area: string | null;
  forwardedTo: string | null;
};

export async function findReference(reference: string): Promise<ApiResult<ReferenceHit>> {
  const result = await api<{
    id: number;
    reference_number: string;
    status: string;
    editable: boolean;
    subject: string | null;
    area_name: string | null;
    forwarded_to: string | null;
  }>(`${COMPLAINTS}/by-reference?${new URLSearchParams({ reference })}`);
  return mapData(result, (h) => ({
    id: h.id,
    reference: h.reference_number,
    status: statusLabel(h.status),
    editable: h.editable,
    subject: h.subject,
    area: h.area_name,
    forwardedTo: h.forwarded_to,
  }));
}

export type ComplaintFilter = "draft" | "incomplete" | "submitted" | "forwarded" | "rejected" | "duplicates";

export type ComplaintRow = {
  id: number;
  reference: string | null;
  status: string; // as Level 1 sees it
  subject: string | null;
  bus: string | null;
  complainant: string | null;
  targetCode: string | null; // who the complaint is against
  target: string | null;
  accused: string | null;
  accusedStatus: string;
  category: string | null; // the issue type
  area: string | null;
  severity: string | null;
  date: string | null;
  updated: string;
  editable: boolean;
  possibleDuplicate: boolean;
};

export type ComplaintPage = {
  rows: ComplaintRow[];
  total: number;
  page: number;
  pageSize: number;
  counts: Record<ComplaintFilter | "all", number>;
  targetCounts: Record<TargetFilter | "all", number>;
};

export async function listComplaints(filters: {
  status: ComplaintFilter | null;
  target: TargetFilter | null;
  scope: "mine" | "all";
  search: string;
  page: number;
}): Promise<ApiResult<ComplaintPage>> {
  const params = new URLSearchParams({ page: String(filters.page), scope: filters.scope });
  if (filters.target) params.set("target", filters.target);
  if (filters.status) params.set("status", filters.status);
  if (filters.search) params.set("search", filters.search);
  const result = await api<{
    items: {
      id: number;
      reference_number: string | null;
      status: string;
      subject: string | null;
      vehicle_number: string | null;
      complainant: string | null;
      target_code: string | null;
      target_name: string | null;
      accused_name: string | null;
      accused_status: string;
      category_name: string | null;
      area_name: string | null;
      severity_name: string | null;
      complaint_date: string | null;
      updated_at: string;
      editable: boolean;
      possible_duplicate: boolean;
    }[];
    total: number;
    page: number;
    page_size: number;
    counts: ComplaintPage["counts"];
    target_counts: ComplaintPage["targetCounts"];
  }>(`${COMPLAINTS}?${params}`);
  return mapData(result, (b) => ({
    rows: b.items.map((c) => ({
      id: c.id,
      reference: c.reference_number,
      status: statusLabel(c.status),
      subject: c.subject,
      bus: c.vehicle_number,
      complainant: c.complainant,
      targetCode: c.target_code,
      target: c.target_name,
      accused: c.accused_name,
      accusedStatus: c.accused_status,
      category: c.category_name,
      area: c.area_name,
      severity: c.severity_name,
      date: c.complaint_date,
      updated: c.updated_at,
      editable: c.editable,
      possibleDuplicate: c.possible_duplicate,
    })),
    total: b.total,
    page: b.page,
    pageSize: b.page_size,
    counts: b.counts,
    targetCounts: b.target_counts,
  }));
}