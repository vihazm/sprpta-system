import type { Role } from "@/lib/roles";

// Shapes used by the administrator's Users page (UI-AD-02).
// A staff account is any role except the complainant, who has a separate portal account.

export type StaffRole = Exclude<Role, "cp">;

export type StaffStatus = "active" | "locked" | "inactive";

export type StaffUser = {
  id: number;
  name: string;
  login: string; // an email address or a phone number
  role: StaffRole;
  areaId: number | null; // only Level 2 officers have one
  area: string | null;
  status: StaffStatus;
  signedIn: boolean; // has a live session right now
  lastSignIn: string | null; // ISO date and time
  created: string; // ISO date and time
};

export type UserPage = {
  users: StaffUser[];
  page: number;
  total: number; // matching the filters, over all pages
  pageSize: number;
  roleCounts: Record<"all" | StaffRole, number>; // matching the search and status
};

// An area and the active Level 2 officer who decides it, if there is one.
export type AreaOfficer = {
  id: number;
  name: string;
  officerId: number | null;
  officerName: string | null;
};

export type UsersSummary = {
  active: number; // includes locked accounts
  signedInNow: number;
  locked: number;
  inactive: number;
  byRole: Record<StaffRole, number>;
  areas: AreaOfficer[];
};

// What the form can set. A new user also gets a first password.
export type UserForm = {
  name: string;
  login: string;
  role: StaffRole;
  areaId: number | null;
  active: boolean;
};
