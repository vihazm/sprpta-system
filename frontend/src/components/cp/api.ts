import { api, type ApiResult } from "@/lib/api-client";
import type { ComplaintFields, Outcome, PortalComplaint, PortalOptions } from "./types";

// The calls behind the complainant portal. The API speaks snake_case and the components camelCase, so the
// conversion happens here and nowhere else.

const COMPLAINTS = "/api/cp/complaints";

type ApiComplaint = {
  id: number;
  reference_number: string | null;
  subject: string;
  complaint_date: string | null;
  submitted_at: string;
  step: PortalComplaint["step"];
  status_label: string;
  outcome: Outcome;
  step_dates: (string | null)[];
  target_name: string | null;
  category_name: string | null;
  area_name: string | null;
  route_stand_name: string | null;
  vehicle_number: string | null;
  description: string | null;
};

function toComplaint(c: ApiComplaint): PortalComplaint {
  return {
    id: c.id,
    referenceNumber: c.reference_number,
    subject: c.subject,
    complaintDate: c.complaint_date,
    submittedAt: c.submitted_at,
    step: c.step,
    statusLabel: c.status_label,
    outcome: c.outcome,
    stepDates: c.step_dates,
    targetName: c.target_name,
    categoryName: c.category_name,
    areaName: c.area_name,
    routeStandName: c.route_stand_name,
    vehicleNumber: c.vehicle_number,
    description: c.description,
  };
}

function mapData<A, B>(result: ApiResult<A>, convert: (data: A) => B): ApiResult<B> {
  return result.ok ? { ok: true, data: convert(result.data) } : result;
}

export async function loadComplaints(): Promise<ApiResult<PortalComplaint[]>> {
  return mapData(await api<ApiComplaint[]>(COMPLAINTS), (rows) => rows.map(toComplaint));
}

export async function loadOptions(): Promise<ApiResult<PortalOptions>> {
  const result = await api<{
    areas: PortalOptions["areas"];
    targets: PortalOptions["targets"];
    categories: { id: number; name: string; target_ids: number[] }[];
    routes_stands: { id: number; name: string; kind: string; area_id: number | null }[];
  }>(`${COMPLAINTS}/options`);
  return mapData(result, (o) => ({
    areas: o.areas,
    targets: o.targets,
    categories: o.categories.map((c) => ({ id: c.id, name: c.name, targetIds: c.target_ids })),
    routesStands: o.routes_stands.map((p) => ({ id: p.id, name: p.name, kind: p.kind, areaId: p.area_id })),
  }));
}

export async function submitComplaint(fields: ComplaintFields): Promise<ApiResult<PortalComplaint>> {
  const result = await api<ApiComplaint>(COMPLAINTS, {
    method: "POST",
    body: {
      complaint_date: fields.complaintDate,
      target_type_id: fields.targetTypeId,
      subject: fields.subject.trim(),
      vehicle_number: fields.vehicleNumber.trim() || null,
      area_id: fields.areaId,
      route_stand_id: fields.routeStandId,
      category_id: fields.categoryId,
      description: fields.description.trim(),
    },
  });
  return mapData(result, toComplaint);
}
