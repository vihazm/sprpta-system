import { api, type ApiResult } from "@/lib/api-client";
import type {
  AccusedStatus,
  Attachment,
  ComplainantType,
  BusRecord,
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
  TargetCode,
  VehicleRecord,
} from "./types";
import type { DutyPerson } from "@/components/l1/lookup/types";

// The calls behind the Level 1 complaint and recommendation forms. The API speaks
// snake_case and the components camelCase, so the conversion happens here and nowhere else.

const COMPLAINTS = "/api/l1/complaints";

export type ApiVehicle = {
  id: number;
  vehicle_number: string;
  vehicle_type: VehicleRecord["type"];
  area_id: number;
  area_name: string;
  permit_number: string | null;
  owner_name: string | null;
  owner_person_id: number | null;
  past_complaints: number;
};

type ApiAttachment = { id: number; file_name: string; size_bytes: number };

type ApiDuty = {
  trip_id: number;
  service_date: string;
  bus_number: string;
  permit_number: string;
  route: string;
  origin: string;
  destination: string;
  departure_time: string;
  owner_name: string | null;
  owner_person_id: number | null;
  driver_person_id: number | null;
  driver_name: string | null;
  conductor_person_id: number | null;
  conductor_name: string | null;
  verification_status: BusRecord["verification"];
};

// The snapshot keeps only the names of people Admin verified; an empty one is shown by the overall status.
function dutyPerson(personId: number | null, name: string | null, overall: BusRecord["verification"]): DutyPerson {
  if (name) return { personId, name, status: "verified" };
  return { personId: null, name: null, status: overall === "Unavailable" ? "unavailable" : "unverified" };
}

function toDuty(d: ApiDuty): BusRecord {
  return {
    tripId: d.trip_id,
    date: d.service_date,
    busNumber: d.bus_number,
    permitNumber: d.permit_number,
    route: d.route,
    origin: d.origin,
    destination: d.destination,
    departure: d.departure_time.slice(0, 5),
    owner: d.owner_name,
    ownerId: d.owner_person_id,
    driver: dutyPerson(d.driver_person_id, d.driver_name, d.verification_status),
    conductor: dutyPerson(d.conductor_person_id, d.conductor_name, d.verification_status),
    verification: d.verification_status,
  };
}

type ApiComplaint = {
  id: number;
  reference_number: string | null;
  status: string;
  via_portal: boolean;
  medium_id: number | null;
  is_anonymous: boolean;
  complainant_name: string | null;
  mobile: string | null;
  email: string | null;
  complaint_date: string | null;
  incident_time: string | null;
  incident_location: string | null;
  vehicle_number: string | null;
  vehicle: ApiVehicle | null;
  trip_id: number | null;
  duty: ApiDuty | null;
  subject_person_id: number | null;
  subject_person_name: string | null;
  target_type_id: number | null;
  target_name: string | null;
  complainant_type: ComplainantType | null;
  bus_verification: string | null;
  accused_status: AccusedStatus;
  category_name: string | null;
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

export function toVehicle(v: ApiVehicle): VehicleRecord {
  return {
    id: v.id,
    number: v.vehicle_number,
    type: v.vehicle_type,
    areaId: v.area_id,
    area: v.area_name,
    permit: v.permit_number,
    owner: v.owner_name,
    ownerId: v.owner_person_id,
    pastComplaints: v.past_complaints,
  };
}

function toAttachment(a: ApiAttachment): Attachment {
  return { id: a.id, name: a.file_name, size: a.size_bytes };
}

const KNOWN_STATUS = ["submitted", "draft", "incomplete", "forwarded", "rejected"];

function toComplaint(c: ApiComplaint): SavedComplaint {
  return {
    id: c.id,
    reference: c.reference_number,
    status: (KNOWN_STATUS.includes(c.status) ? c.status : "other") as ComplaintStatus,
    viaPortal: c.via_portal,
    values: {
      anonymous: c.is_anonymous,
      name: c.complainant_name ?? "",
      mobile: c.mobile ?? "",
      email: c.email ?? "",
      date: c.complaint_date ?? "",
      mediumId: c.medium_id,
      vehicleNumber: c.vehicle_number ?? "",
      tripId: c.trip_id,
      incidentTime: c.incident_time?.slice(0, 5) ?? "",
      incidentLocation: c.incident_location ?? "",
      complainantType: c.complainant_type,
      targetId: c.target_type_id,
      personId: c.subject_person_id,
      personName: c.subject_person_name ?? "",
      routeId: c.route_stand_id,
      categoryId: c.category_id,
      severityId: c.severity_id,
      subject: c.subject ?? "",
      description: c.description ?? "",
    },
    vehicle: c.vehicle ? toVehicle(c.vehicle) : null,
    duty: c.duty ? toDuty(c.duty) : null,
    targetName: c.target_name,
    accusedStatus: c.accused_status,
    categoryName: c.category_name,
    busVerification: c.bus_verification,
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
    mobile: blankToNull(f.mobile),
    email: blankToNull(f.email),
    complaint_date: blankToNull(f.date),
    incident_time: blankToNull(f.incidentTime),
    incident_location: blankToNull(f.incidentLocation),
    vehicle_number: blankToNull(f.vehicleNumber),
    trip_id: f.tripId,
    target_type_id: f.targetId,
    complainant_type: f.complainantType,
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
    categories: { id: number; name: string; target_ids: number[] }[];
    targets: { id: number; name: string; code: TargetCode }[];
    severities: { id: number; name: string; forward_days: number }[];
    routes_stands: { id: number; name: string; kind: "route" | "stand"; area_id: number | null }[];
  }>(`${COMPLAINTS}/options`);
  return mapData(result, (body) => ({
    mediums: body.mediums,
    categories: body.categories.map((c) => ({ id: c.id, name: c.name, targetIds: c.target_ids })),
    targets: body.targets,
    severities: body.severities.map((s) => ({ id: s.id, name: s.name, forwardDays: s.forward_days })),
    routes: body.routes_stands.map((r) => ({ id: r.id, name: r.name, kind: r.kind, areaId: r.area_id })),
  }));
}

export async function lookupVehicle(number: string) {
  const result = await api<ApiVehicle>(`${COMPLAINTS}/lookup/vehicle?${new URLSearchParams({ number })}`);
  return mapData(result, toVehicle);
}

export async function lookupPermit(number: string) {
  const result = await api<ApiVehicle>(`${COMPLAINTS}/lookup/permit?${new URLSearchParams({ number })}`);
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
export async function saveComplaint(id: number | null, fields: ComplaintFields, requestId?: string) {
  const result = await api<ApiComplaint>(id === null ? COMPLAINTS : `${COMPLAINTS}/${id}`, {
    method: id === null ? "POST" : "PUT",
    // The key lets the server recognise a retried create and return the complaint it already made.
    body: id === null && requestId ? { ...toBody(fields), client_request_id: requestId } : toBody(fields),
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
  must_decide: boolean;
};

function toCandidates(candidates: ApiCandidate[]): DuplicateCandidate[] {
  return candidates.map((c) => ({
    id: c.id,
    reference: c.reference_number,
    subject: c.subject,
    match: c.match,
    choice: c.link_type,
    mustDecide: c.must_decide,
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
