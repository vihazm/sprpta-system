import { api, type ApiResult } from "@/lib/api-client";
import type {
  Attachment,
  ComplaintFields,
  ComplaintStatus,
  DuplicateCandidate,
  DuplicateChoice,
  FormOptions,
  PersonRecord,
  PersonType,
  RecommendationFields,
  RejectionType,
  SavedComplaint,
  VehicleRecord,
} from "./types";

// The calls behind the Level 1 complaint and recommendation forms. The API speaks
// snake_case and the components camelCase, so the conversion happens here and nowhere else.

const COMPLAINTS = "/api/l1/complaints";

type ApiVehicle = {
  id: number;
  vehicle_number: string;
  vehicle_type: VehicleRecord["type"];
  area_id: number;
  area_name: string;
  permit_number: string | null;
  owner_name: string | null;
  past_complaints: number;
};

type ApiAttachment = { id: number; file_name: string; size_bytes: number };

type ApiComplaint = {
  id: number;
  reference_number: string | null;
  status: string;
  medium_id: number | null;
  is_anonymous: boolean;
  complainant_name: string | null;
  contact: string | null;
  complaint_date: string | null;
  vehicle_number: string | null;
  vehicle: ApiVehicle | null;
  subject_person_id: number | null;
  subject_person_name: string | null;
  route_stand_id: number | null;
  category_id: number | null;
  severity_id: number | null;
  subject: string | null;
  description: string | null;
  area_name: string | null;
  assigned_l2_name: string | null;
  attachments: ApiAttachment[];
};

function mapData<A, B>(result: ApiResult<A>, convert: (data: A) => B): ApiResult<B> {
  return result.ok ? { ok: true, data: convert(result.data) } : result;
}

function toVehicle(v: ApiVehicle): VehicleRecord {
  return {
    id: v.id,
    number: v.vehicle_number,
    type: v.vehicle_type,
    areaId: v.area_id,
    area: v.area_name,
    permit: v.permit_number,
    owner: v.owner_name,
    pastComplaints: v.past_complaints,
  };
}

function toAttachment(a: ApiAttachment): Attachment {
  return { id: a.id, name: a.file_name, size: a.size_bytes };
}

const KNOWN_STATUS = ["draft", "incomplete", "forwarded", "rejected"];

function toComplaint(c: ApiComplaint): SavedComplaint {
  return {
    id: c.id,
    reference: c.reference_number,
    status: (KNOWN_STATUS.includes(c.status) ? c.status : "other") as ComplaintStatus,
    values: {
      anonymous: c.is_anonymous,
      name: c.complainant_name ?? "",
      contact: c.contact ?? "",
      date: c.complaint_date ?? "",
      mediumId: c.medium_id,
      vehicleNumber: c.vehicle_number ?? "",
      personId: c.subject_person_id,
      personName: c.subject_person_name ?? "",
      routeId: c.route_stand_id,
      categoryId: c.category_id,
      severityId: c.severity_id,
      subject: c.subject ?? "",
      description: c.description ?? "",
    },
    vehicle: c.vehicle ? toVehicle(c.vehicle) : null,
    area: c.area_name,
    officer: c.assigned_l2_name,
    attachments: c.attachments.map(toAttachment),
  };
}

function blankToNull(text: string) {
  return text.trim() === "" ? null : text.trim();
}

function toBody(f: ComplaintFields) {
  return {
    medium_id: f.mediumId,
    is_anonymous: f.anonymous,
    complainant_name: blankToNull(f.name),
    contact: blankToNull(f.contact),
    complaint_date: blankToNull(f.date),
    vehicle_number: blankToNull(f.vehicleNumber),
    subject_person_id: f.personId,
    subject_person_text: f.personId === null ? blankToNull(f.personName) : null,
    route_stand_id: f.routeId,
    category_id: f.categoryId,
    severity_id: f.severityId,
    subject: blankToNull(f.subject),
    description: blankToNull(f.description),
  };
}

// ---------------------------------------------------------------- lists and lookups

export async function loadOptions(): Promise<ApiResult<FormOptions>> {
  const result = await api<{
    mediums: { id: number; name: string }[];
    categories: { id: number; name: string }[];
    severities: { id: number; name: string; forward_days: number }[];
    routes_stands: { id: number; name: string; kind: "route" | "stand"; area_id: number | null }[];
  }>(`${COMPLAINTS}/options`);
  return mapData(result, (body) => ({
    mediums: body.mediums,
    categories: body.categories,
    severities: body.severities.map((s) => ({ id: s.id, name: s.name, forwardDays: s.forward_days })),
    routes: body.routes_stands.map((r) => ({ id: r.id, name: r.name, kind: r.kind, areaId: r.area_id })),
  }));
}

export async function lookupVehicle(number: string) {
  const result = await api<ApiVehicle>(`${COMPLAINTS}/lookup/vehicle?${new URLSearchParams({ number })}`);
  return mapData(result, toVehicle);
}

export async function searchPeople(search: string, type?: PersonType) {
  const params = new URLSearchParams({ search });
  if (type) params.set("person_type", type);
  const result = await api<{ id: number; full_name: string; person_type: PersonType }[]>(
    `${COMPLAINTS}/lookup/people?${params}`,
  );
  return mapData(result, (people): PersonRecord[] =>
    people.map((p) => ({ id: p.id, name: p.full_name, type: p.person_type })),
  );
}

// ---------------------------------------------------------------- the complaint

export async function loadComplaint(id: number) {
  return mapData(await api<ApiComplaint>(`${COMPLAINTS}/${id}`), toComplaint);
}

/** Saves the form as a draft the first time, and updates the same complaint after that. */
export async function saveComplaint(id: number | null, fields: ComplaintFields) {
  const result = await api<ApiComplaint>(id === null ? COMPLAINTS : `${COMPLAINTS}/${id}`, {
    method: id === null ? "POST" : "PUT",
    body: toBody(fields),
  });
  return mapData(result, toComplaint);
}

export async function keepIncomplete(id: number) {
  return mapData(await api<ApiComplaint>(`${COMPLAINTS}/${id}/incomplete`, { method: "POST" }), toComplaint);
}

export async function forwardComplaint(id: number) {
  return mapData(await api<ApiComplaint>(`${COMPLAINTS}/${id}/forward`, { method: "POST" }), toComplaint);
}

export async function rejectComplaint(
  id: number,
  rejection: { type: RejectionType; reason: string; earlierReference: string },
) {
  const result = await api<ApiComplaint>(`${COMPLAINTS}/${id}/reject`, {
    method: "POST",
    body: {
      rejection_type: rejection.type,
      reason: rejection.reason,
      duplicate_of_reference: rejection.type === "duplicate" ? blankToNull(rejection.earlierReference) : null,
    },
  });
  return mapData(result, toComplaint);
}

// ---------------------------------------------------------------- duplicate check

type ApiCandidate = {
  id: number;
  reference_number: string;
  subject: string | null;
  match: number;
  link_type: DuplicateChoice | null;
};

function toCandidates(candidates: ApiCandidate[]): DuplicateCandidate[] {
  return candidates.map((c) => ({
    id: c.id,
    reference: c.reference_number,
    subject: c.subject,
    match: c.match,
    choice: c.link_type,
  }));
}

export async function loadDuplicates(id: number) {
  return mapData(await api<ApiCandidate[]>(`${COMPLAINTS}/${id}/duplicates`), toCandidates);
}

export async function decideDuplicate(id: number, candidateId: number, choice: DuplicateChoice) {
  const result = await api<ApiCandidate[]>(`${COMPLAINTS}/${id}/duplicates/${candidateId}`, {
    method: "PUT",
    body: { link_type: choice },
  });
  return mapData(result, toCandidates);
}

// ---------------------------------------------------------------- evidence

export async function uploadAttachment(id: number, file: File) {
  const body = new FormData();
  body.append("file", file);
  return mapData(await api<ApiAttachment>(`${COMPLAINTS}/${id}/attachments`, { method: "POST", body }), toAttachment);
}

export function removeAttachment(id: number, attachmentId: number) {
  return api<null>(`${COMPLAINTS}/${id}/attachments/${attachmentId}`, { method: "DELETE" });
}

// ---------------------------------------------------------------- recommendation

export function saveRecommendation(f: RecommendationFields) {
  return api<{ id: number }>("/api/l1/recommendations", {
    method: "POST",
    body: {
      recommendation_type: f.kind,
      details: f.details.trim(),
      medium_id: f.mediumId,
      received_date: blankToNull(f.date),
      subject_person_id: f.kind === "commendation" ? f.personId : null,
    },
  });
}
