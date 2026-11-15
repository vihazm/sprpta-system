import { api, type ApiResult } from "@/lib/api-client";

// The calls behind "Add Daily Bus Record" and "My Daily Bus Records". The API speaks snake_case and the
// components camelCase, so the conversion happens here and nowhere else.

const BASE = "/api/l1/daily-records";

export type DailyRecordStatus = "draft" | "approved" | "published";

// What the officer types. People are kept as { id, name }: only a person found in the records can be saved.
export type PersonChoice = { id: number | null; name: string };

export type DailyRecordFields = {
  date: string; // yyyy-mm-dd
  busNumber: string;
  routeId: number | null;
  departure: string; // HH:MM
  end: string;
  origin: string;
  destination: string;
  owner: PersonChoice;
  driver: PersonChoice;
  driverStart: string;
  driverEnd: string;
  conductor: PersonChoice;
  conductorStart: string;
  conductorEnd: string;
  remarks: string;
};

export type DailyRecord = {
  id: number;
  status: DailyRecordStatus;
  statusLabel: string; // Pending Verification, Verified, not published, or Published
  verification: string;
  permit: string;
  route: string;
  area: string | null;
  enteredBy: string | null;
  createdAt: string;
  editable: boolean;
  fields: DailyRecordFields;
};

export type DailyRecordPage = { items: DailyRecord[]; total: number; page: number; pageSize: number };

type ApiRecord = {
  id: number;
  status: DailyRecordStatus;
  status_label: string;
  service_date: string;
  vehicle_number: string;
  permit_number: string;
  route_stand_id: number;
  route: string;
  origin: string;
  destination: string;
  area_name: string | null;
  departure_time: string;
  end_time: string | null;
  owner_person_id: number | null;
  owner_name: string | null;
  driver_person_id: number | null;
  driver_name: string | null;
  driver_start: string | null;
  driver_end: string | null;
  conductor_person_id: number | null;
  conductor_name: string | null;
  conductor_start: string | null;
  conductor_end: string | null;
  remarks: string | null;
  entered_by: string | null;
  created_at: string;
  verification_status: string;
  editable: boolean;
};

const clock = (time: string | null) => (time ? time.slice(0, 5) : "");
const orNull = (text: string) => (text.trim() === "" ? null : text.trim());

function toRecord(r: ApiRecord): DailyRecord {
  return {
    id: r.id,
    status: r.status,
    statusLabel: r.status_label,
    verification: r.verification_status,
    permit: r.permit_number,
    route: r.route,
    area: r.area_name,
    enteredBy: r.entered_by,
    createdAt: r.created_at,
    editable: r.editable,
    fields: {
      date: r.service_date,
      busNumber: r.vehicle_number,
      routeId: r.route_stand_id,
      departure: clock(r.departure_time),
      end: clock(r.end_time),
      origin: r.origin,
      destination: r.destination,
      owner: { id: r.owner_person_id, name: r.owner_name ?? "" },
      driver: { id: r.driver_person_id, name: r.driver_name ?? "" },
      driverStart: clock(r.driver_start),
      driverEnd: clock(r.driver_end),
      conductor: { id: r.conductor_person_id, name: r.conductor_name ?? "" },
      conductorStart: clock(r.conductor_start),
      conductorEnd: clock(r.conductor_end),
      remarks: r.remarks ?? "",
    },
  };
}

function toBody(f: DailyRecordFields) {
  return {
    service_date: f.date,
    vehicle_number: f.busNumber.trim(),
    route_stand_id: f.routeId,
    departure_time: f.departure,
    end_time: orNull(f.end),
    origin: f.origin.trim(),
    destination: f.destination.trim(),
    owner_person_id: f.owner.id,
    driver_person_id: f.driver.id,
    driver_start: f.driver.id === null ? null : orNull(f.driverStart),
    driver_end: f.driver.id === null ? null : orNull(f.driverEnd),
    conductor_person_id: f.conductor.id,
    conductor_start: f.conductor.id === null ? null : orNull(f.conductorStart),
    conductor_end: f.conductor.id === null ? null : orNull(f.conductorEnd),
    remarks: orNull(f.remarks),
  };
}

function mapData<A, B>(result: ApiResult<A>, convert: (data: A) => B): ApiResult<B> {
  return result.ok ? { ok: true, data: convert(result.data) } : result;
}

export async function saveDailyRecord(id: number | null, fields: DailyRecordFields) {
  const result = await api<ApiRecord>(id === null ? BASE : `${BASE}/${id}`, {
    method: id === null ? "POST" : "PUT",
    body: toBody(fields),
  });
  return mapData(result, toRecord);
}

export async function loadDailyRecord(id: number) {
  return mapData(await api<ApiRecord>(`${BASE}/${id}`), toRecord);
}

export async function listDailyRecords(filters: { date: string; search: string; page: number }) {
  const params = new URLSearchParams({ page: String(filters.page) });
  if (filters.date) params.set("service_date", filters.date);
  if (filters.search) params.set("search", filters.search);
  const result = await api<{ items: ApiRecord[]; total: number; page: number; page_size: number }>(`${BASE}?${params}`);
  return mapData(
    result,
    (b): DailyRecordPage => ({ items: b.items.map(toRecord), total: b.total, page: b.page, pageSize: b.page_size }),
  );
}
