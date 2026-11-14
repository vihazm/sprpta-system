// Shapes used by the Level 1 complaint and recommendation forms (UC-L1-01 to UC-L1-11).

export type Option = { id: number; name: string };
export type SeverityOption = Option & { forwardDays: number }; // 0 means the same day
export type RouteOption = Option & { kind: "route" | "stand"; areaId: number | null };

// The lists behind the drop-downs and choice buttons. They come from master data.
export type FormOptions = {
  mediums: Option[];
  categories: Option[];
  severities: SeverityOption[];
  routes: RouteOption[];
};

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
  pastComplaints: number;
};

// What L1 types into the complaint form.
export type ComplaintFields = {
  anonymous: boolean;
  name: string;
  contact: string;
  date: string; // yyyy-mm-dd
  mediumId: number | null;
  vehicleNumber: string;
  personId: number | null; // the driver, conductor or staff member, when a record matches
  personName: string;
  routeId: number | null;
  categoryId: number | null;
  severityId: number | null;
  subject: string;
  description: string;
};

export type ComplaintStatus = "draft" | "incomplete" | "forwarded" | "rejected" | "other";

export type Attachment = { id: number; name: string; size: number };

export type SavedComplaint = {
  id: number;
  reference: string | null; // a draft has none yet
  status: ComplaintStatus;
  values: ComplaintFields;
  vehicle: VehicleRecord | null;
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
