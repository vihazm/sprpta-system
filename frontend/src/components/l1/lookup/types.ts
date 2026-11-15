import type { VehicleRecord } from "@/components/l1/entry/types";

// Shapes used by the Level 1 Bus & Permit Lookup (Date + Bus Number).

// Nobody on a record is guessed: a person is named only when Admin verified the duty record.
export type DutyStatus = "verified" | "unverified" | "unavailable";
export type DutyPerson = { personId: number | null; name: string | null; status: DutyStatus };

export type TripSummary = {
  id: number;
  busNumber: string;
  permitNumber: string;
  route: string;
  departure: string; // HH:MM
};

export type BusSearch = { date: string; vehicle: VehicleRecord; trips: TripSummary[] };

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
  owner: { personId: number | null; name: string | null; source: "assignment" | "vehicle_record" | null };
  driver: DutyPerson;
  conductor: DutyPerson;
  verification: VerificationStatus;
};
