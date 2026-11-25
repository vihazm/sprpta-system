// What the complainant portal shows. The API speaks snake_case; api.ts converts it to this.

export type Outcome = "open" | "closed" | "not_accepted";

export type PortalAttachment = {
  id: number;
  fileName: string;
  mimeType: string;
  sizeBytes: number;
};

export type PortalVehicle = {
  vehicleNumber: string;
  vehicleType: string;
  areaId: number;
  areaName: string;
};

export type PortalComplaint = {
  id: number;
  referenceNumber: string | null; // none until Level 1 has registered it
  subject: string;
  complaintDate: string | null;
  submittedAt: string;
  step: 1 | 2 | 3 | 4;
  statusLabel: string;
  outcome: Outcome;
  stepDates: (string | null)[]; // when each of the four steps was reached
  targetName: string | null;
  categoryName: string | null;
  areaName: string | null;
  routeStandName: string | null;
  vehicleNumber: string | null;
  description: string | null;
  attachments: PortalAttachment[];
  canDelete: boolean; // only while Level 1 has not checked it yet
};

export type Named = { id: number; name: string };

export type PortalOptions = {
  areas: Named[];
  targets: (Named & { code: string })[];
  categories: (Named & { targetIds: number[] })[]; // the targets a category is approved for; empty means all
  routesStands: (Named & { kind: string; areaId: number | null })[];
};

export type ComplaintFields = {
  complaintDate: string;
  targetTypeId: number;
  subject: string;
  vehicleNumber: string;
  areaId: number;
  routeStandId: number | null;
  categoryId: number;
  description: string;
};
