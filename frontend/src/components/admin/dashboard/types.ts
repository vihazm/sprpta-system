// Shapes of the figures shown on the administrator dashboard.
// They follow the System Flow, UI Flow and Database Structure documents.

export type Tone = "ok" | "warn" | "crit" | "info";

export type Service = { name: string; detail: string; tone: Tone };

export type AttentionItem = {
  title: string;
  detail: string;
  tone: Tone;
  action?: string;
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

// The part of the dashboard the backend already provides. The rest is sample data for now.
export type LiveDashboardData = Pick<
  AdminDashboardData,
  | "sessions"
  | "staffByRole"
  | "portalUsers"
  | "deactivatedUsers"
  | "signInsPerHour"
  | "currentHour"
  | "recentUsage"
>;

export type AdminDashboardData = {
  services: Service[];
  apiResponseMs: number[]; // last 24 hours, oldest first
  lastBackup: { when: string; succeeded: boolean };
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
  messages: { sent: number; failed: number; byType: Count[] };
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
    byStatus: Count[];
    overdue: number;
  };
  timeTargets: TimeTarget[];
  settings: { ratingFormulaVersion: number; aiTimeoutSeconds: number };
};
