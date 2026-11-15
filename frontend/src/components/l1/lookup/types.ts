import type { VehicleRecord } from "@/components/l1/entry/types";

// Shapes used by the Level 1 Bus & Permit Lookup (Date + Bus Number).

// Nobody on a record is guessed: a person is named only when Admin verified the duty record.
export type DutyStatus = "verified" | "unverified" | "unavailable";
export type DutyPerson = { personId: number | null; name: string | null; status: DutyStatus };

export type TripStatus = "completed" | "cancelled" | "partial";
// What the records say about the bus on the date. Only "no_record" means nothing is on file.
export type OperationStatus = "operated" | "cancelled" | "did_not_operate" | "no_record";

export type TripSummary = {
  id: number;
  busNumber: string;
  permitNumber: string;
  route: string;
  departure: string; // HH:MM
  tripStatus: TripStatus;
  direction: string | null;
  synthetic: boolean; // simulated development data, not an official record
};

export type BusSearch = {
  date: string;
  vehicle: VehicleRecord;
  trips: TripSummary[];
  operationStatus: OperationStatus;
  nonOperationReason: string | null;
};

export type VerificationStatus = "Verified" | "Unverified" | "Unavailable";

// The selected record. The ids are what the New complaint form is filled in from.
export type TripDetails = {
  id: number;
  date: string; // yyyy-mm-dd
  vehicleId: number;
  busNumber: string;
  area: string;
  permitId: number;
  permitNumber: string;
  routeId: number;
  route: string;
  origin: string;
  destination: string;
  departure: string; // HH:MM
  arrival: string | null;
  actualDeparture: string | null;
  actualArrival: string | null;
  tripStatus: TripStatus;
  direction: string | null;
  synthetic: boolean;
  owner: { personId: number | null; name: string | null; source: "assignment" | "vehicle_record" | null };
  driver: DutyPerson;
  conductor: DutyPerson;
  verification: VerificationStatus;
};
