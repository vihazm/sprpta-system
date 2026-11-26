// Shapes of the figures shown on the administrator dashboard.
// They follow the System Flow, UI Flow and Database Structure documents.

import type { Tone } from "@/components/dashboard/ui";
import type { Backup, FileStorage } from "../system-health/types";

export type { Tone };

export type Service = { name: string; detail: string; tone: Tone };

export type AttentionItem = {
  title: string;
  detail: string;
  tone: Tone;
  href: string; // the page where it is dealt with
  action: string; // the label of the button that opens it
};

export type Count = { label: string; count: number };

export type UsageEvent = {
  time: string;
  who: string; // already masked, the administrator never sees personal data
  role: string;
  event: "signed in" | "signed out" | "failed sign-in";
};

export type AreaStatus = { name: string; vehicles: number; hasOfficer: boolean };

export type TimeTarget = {
  severity: string;
  forwardDays: number;
  decideDays: number;
  closeDays: number;
};

// The one tile still on sample data, until the policy library exists.
export type SampleDashboardData = Pick<AdminDashboardData, "policy">;

// Everything else comes from the backend.
export type LiveDashboardData = Omit<AdminDashboardData, keyof SampleDashboardData>;

export type AdminDashboardData = {
  services: Service[];
  apiResponseMs: number[]; // last 24 hours, oldest first
  fileStorage: FileStorage;
  lastBackup: Backup | null; // null until the backup script has run once
  attention: AttentionItem[]; // most urgent first
  sessions: {
    signedInNow: number;
    signInsToday: number;
    failedToday: number;
    lockedAccounts: number;
  };
  staffByRole: Count[];
  portalUsers: { total: number; unverified: number };
  deactivatedUsers: number;
  signInsPerHour: number[]; // last 24 hours, oldest first, the last one is the current hour
  currentHour: number; // 0 to 23
  recentUsage: UsageEvent[];
  policy: {
    activeVersions: number;
    clauses: number;
    draftsWaiting: number;
    failedScans: number;
    aiRequests: number;
    aiTimeouts: number;
  };
  messages: { sent: number; failed: number; byType: Count[] }; // last 24 hours
  areas: AreaStatus[];
  masterData: {
    people: number;
    vehicles: number;
    permits: number;
    routesAndStands: number;
    categories: number;
    vehiclesWithoutPermit: number;
  };
  complaints: {
    perDay: number[]; // last 30 days, oldest first
    byArea: Count[];
    byStatus: Count[]; // labelled with the status's name, for example "Under review"
    overdue: number; // open cases past a time target now
  };
  timeTargets: TimeTarget[];
};
