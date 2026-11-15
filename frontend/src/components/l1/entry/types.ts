// Shapes used by the Level 1 complaint and recommendation forms (UC-L1-01 to UC-L1-11).

import type { DutyPerson } from "@/components/l1/lookup/types";

export type Option = { id: number; name: string };
export type SeverityOption = Option & { forwardDays: number }; // 0 means the same day
export type RouteOption = Option & { kind: "route" | "stand"; areaId: number | null };

// The lists behind the drop-downs and choice buttons. They come from master data.
export type TargetCode = "driver" | "conductor" | "owner" | "bus_service" | "other";
export type TargetOption = Option & { code: TargetCode };
// targetIds lists the targets a category is approved for; empty means it is open to every target.
export type CategoryOption = Option & { targetIds: number[] };

export type FormOptions = {
  mediums: Option[];
  categories: CategoryOption[];
  targets: TargetOption[];
  severities: SeverityOption[];
  routes: RouteOption[];
};

export type ComplainantType = "passenger" | "driver" | "conductor" | "owner" | "other";
export type PersonType = "driver" | "conductor" | "sprpta_staff" | "owner";
export type PersonRecord = { id: number; name: string; type: PersonType };

// A vehicle record, with the permit and owner filled in from master data.
export type VehicleRecord = {
  id: number;
  number: string;
  type: "bus" | "trishaw";
  areaId: number;
  area: string;
  permit: string | null;
  owner: string | null;
  ownerId: number | null; // the registered owner's person record, for confirming an owner complaint
  pastComplaints: number;
};

// The verified daily record shown for a selected bus: from the Bus & Permit Lookup, or as saved with a complaint.
// Nobody is named unless Admin verified them (see DutyPerson).
export type BusRecord = {
  tripId: number;
  date: string; // yyyy-mm-dd
  busNumber: string;
  permitNumber: string; // text: it keeps its leading zeros
  route: string;
  origin: string;
  destination: string;
  departure: string; // HH:MM
  owner: string | null;
  ownerId: number | null;
  tripStatus?: "completed" | "cancelled" | "partial"; // how the trip went (a cancelled trip never ran)
  synthetic?: boolean; // simulated development data, not an official record
  driver: DutyPerson;
  conductor: DutyPerson;
  verification: "Verified" | "Unverified" | "Unavailable";
};

// What L1 types into the complaint form.
export type ComplaintFields = {
  anonymous: boolean;
  name: string;
  mobile: string;
  email: string;
  date: string; // the incident date, yyyy-mm-dd
  mediumId: number | null;
  vehicleNumber: string;
  tripId: number | null; // the daily record chosen in the lookup; the permit, owner and route come from it
  incidentTime: string; // HH:MM, only when it differs from the trip time
  incidentLocation: string;
  complainantType: ComplainantType | null;
  targetId: number | null; // who the complaint is against (driver, conductor, owner, bus or service, other)
  personId: number | null; // the accused person, when a record matches and the officer confirmed it
  personName: string;
  routeId: number | null;
  categoryId: number | null;
  severityId: number | null;
  subject: string;
  description: string;
};

export type ComplaintStatus = "draft" | "incomplete" | "forwarded" | "rejected" | "other";

// How far the accused person is established, worked out by the server and never taken from the form.
export type AccusedStatus = "verified_duty" | "registered_owner" | "directory_only" | "unidentified" | "none";

export type Attachment ={ id: number; name: string; size: number };

export type SavedComplaint = {
  id: number;
  reference: string | null; // a draft has none yet
  status: ComplaintStatus;
  values: ComplaintFields;
  vehicle: VehicleRecord | null;
  duty: BusRecord | null; // the verified record as it was when the complaint was saved
  targetName: string | null;
  accusedStatus: AccusedStatus;
  categoryName: string | null;
  busVerification: string | null; // what checking the bus against the daily records found
  area: string | null;
  officer: string | null; // the Level 2 officer it was forwarded to
  attachments: Attachment[];
};

export type DuplicateChoice = "not_duplicate" | "duplicate_of" | "related";

export type DuplicateCandidate = {
  id: number;
  reference: string;
  subject: string | null;
  match: number; // 0 to 100
  choice: DuplicateChoice | null;
  mustDecide: boolean; // a close match must be decided before forwarding; a weak one is optional
};

export type RejectionType = "invalid" | "spam" | "out_of_jurisdiction" | "duplicate";

export type RecommendationKind = "improvement" | "commendation";

export type RecommendationFields = {
  kind: RecommendationKind;
  details: string;
  mediumId: number | null;
  date: string; // yyyy-mm-dd
  personId: number | null;
};
