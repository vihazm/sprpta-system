import { api, type ApiResult } from "@/lib/api-client";
import { toVehicle, type ApiVehicle } from "@/components/l1/entry/api";
import type { BusRecord } from "@/components/l1/entry/types";
import type { BusSearch, DutyPerson, OperationStatus, TripDetails, TripStatus, VerificationStatus } from "./types";

// The calls behind the Bus & Permit Lookup. The API speaks snake_case and the components
// camelCase, so the conversion happens here and nowhere else.

const BASE = "/api/l1/bus-lookup";

type ApiDutyPerson = { person_id: number | null; name: string | null; status: DutyPerson["status"] };

function mapData<A, B>(result: ApiResult<A>, convert: (data: A) => B): ApiResult<B> {
  return result.ok ? { ok: true, data: convert(result.data) } : result;
}

const clock = (time: string) => time.slice(0, 5); // 06:30:00 becomes 06:30

const person = (p: ApiDutyPerson): DutyPerson => ({ personId: p.person_id, name: p.name, status: p.status });

export async function searchTrips(date: string, busNumber: string): Promise<ApiResult<BusSearch>> {
  const params = new URLSearchParams({ service_date: date, bus_number: busNumber });
  const result = await api<{
    service_date: string;
    vehicle: ApiVehicle;
    trips: {
      id: number;
      bus_number: string;
      permit_number: string;
      route: string;
      departure_time: string;
      trip_status: TripStatus;
      direction: string | null;
      synthetic: boolean;
    }[];
    operation_status: OperationStatus;
    non_operation_reason: string | null;
  }>(`${BASE}/trips?${params}`);
  return mapData(result, (body) => ({
    date: body.service_date,
    vehicle: toVehicle(body.vehicle),
    trips: body.trips.map((t) => ({
      id: t.id,
      busNumber: t.bus_number,
      permitNumber: t.permit_number,
      route: t.route,
      departure: clock(t.departure_time),
      tripStatus: t.trip_status,
      direction: t.direction,
      synthetic: t.synthetic,
    })),
    operationStatus: body.operation_status,
    nonOperationReason: body.non_operation_reason,
  }));
}

export async function loadTrip(id: number): Promise<ApiResult<TripDetails>> {
  const result = await api<{
    trip_id: number;
    service_date: string;
    vehicle_id: number;
    bus_number: string;
    area_name: string;
    permit_id: number;
    permit_number: string;
    route_stand_id: number;
    route: string;
    origin: string;
    destination: string;
    departure_time: string;
    arrival_time: string | null;
    actual_departure: string | null;
    actual_arrival: string | null;
    trip_status: TripStatus;
    direction: string | null;
    synthetic: boolean;
    owner: { person_id: number | null; name: string | null; source: TripDetails["owner"]["source"] };
    driver: ApiDutyPerson;
    conductor: ApiDutyPerson;
    verification_status: VerificationStatus;
  }>(`${BASE}/trips/${id}`);
  return mapData(result, (t) => ({
    id: t.trip_id,
    date: t.service_date,
    vehicleId: t.vehicle_id,
    busNumber: t.bus_number,
    area: t.area_name,
    permitId: t.permit_id,
    permitNumber: t.permit_number,
    routeId: t.route_stand_id,
    route: t.route,
    origin: t.origin,
    destination: t.destination,
    departure: clock(t.departure_time),
    arrival: t.arrival_time ? clock(t.arrival_time) : null,
    actualDeparture: t.actual_departure ? clock(t.actual_departure) : null,
    actualArrival: t.actual_arrival ? clock(t.actual_arrival) : null,
    tripStatus: t.trip_status,
    direction: t.direction,
    synthetic: t.synthetic,
    owner: { personId: t.owner.person_id, name: t.owner.name, source: t.owner.source },
    driver: person(t.driver),
    conductor: person(t.conductor),
    verification: t.verification_status,
  }));
}

/** The selected trip in the shape the complaint form and its Selected bus card use. */
export function toBusRecord(t: TripDetails): BusRecord {
  return {
    tripId: t.id,
    date: t.date,
    busNumber: t.busNumber,
    permitNumber: t.permitNumber,
    route: t.route,
    origin: t.origin,
    destination: t.destination,
    departure: t.departure,
    owner: t.owner.name,
    ownerId: t.owner.personId,
    tripStatus: t.tripStatus,
    synthetic: t.synthetic,
    driver: t.driver,
    conductor: t.conductor,
    verification: t.verification,
  };
}