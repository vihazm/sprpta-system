import type { AdminDashboardData } from "./types";

// Sample figures so the dashboard can be designed and reviewed before the
// backend provides the real ones. Replace this with a fetch when the API exists.
export const adminDashboardSample: AdminDashboardData = {
  services: [
    { name: "Web app", detail: "41 ms", tone: "ok" },
    { name: "API", detail: "118 ms", tone: "ok" },
    { name: "Database", detail: "6 ms", tone: "ok" },
    { name: "File storage", detail: "68% free", tone: "ok" },
    { name: "AI service", detail: "slow", tone: "warn" },
    { name: "SMS and email", detail: "sending", tone: "ok" },
  ],
  apiResponseMs: [
    118, 112, 121, 108, 115, 104, 120, 98, 110, 117, 95, 106, 92, 112, 104, 118, 90, 108, 102,
    114, 86, 104, 96, 110,
  ],
  lastBackup: { when: "today 02:00", succeeded: true },
  attention: [
    {
      title: "Hambantota has no active Level 2 officer",
      detail: "Complaints for this area cannot be forwarded.",
      tone: "crit",
      action: "Assign officer",
    },
    { title: "The AI service is slow", detail: "Average 21 s, limit 30 s", tone: "warn" },
    { title: "3 messages failed to send", detail: "2 SMS and 1 email today", tone: "warn" },
    { title: "A policy scan failed to index", detail: "Route Permit Conditions v2", tone: "warn" },
    { title: "1 account is locked", detail: "Unlocks at 09:42", tone: "info" },
  ],
  sessions: { signedInNow: 9, signInsToday: 142, failedToday: 7, lockedAccounts: 1 },
  staffByRole: [
    { label: "Level 1 office staff", count: 4 },
    { label: "Level 2 area officers", count: 2 },
    { label: "Level 3 chairman", count: 1 },
    { label: "Administrators", count: 2 },
    { label: "Implementing staff", count: 13 },
  ],
  portalUsers: { total: 238, unverified: 14 },
  deactivatedUsers: 3,
  signInsPerHour: [
    13, 17, 10, 12, 14, 9, 6, 4, 2, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 1, 2, 7, 24, 18,
  ],
  currentHour: 9,
  recentUsage: [
    { time: "09:31", who: "K*** P*****", role: "Level 1", event: "signed in" },
    { time: "09:28", who: "A*** F******", role: "Implementing staff", event: "signed in" },
    { time: "09:24", who: "Unknown login", role: "No account", event: "failed sign-in" },
    { time: "09:17", who: "M*** S*****", role: "Level 2", event: "signed out" },
    { time: "09:12", who: "R*** D*****", role: "Level 3", event: "signed in" },
    { time: "09:05", who: "Portal user ***21", role: "Portal", event: "signed in" },
  ],
  policy: {
    activeVersions: 6,
    clauses: 842,
    draftsWaiting: 1,
    failedScans: 1,
    aiRequests: 18,
    aiTimeouts: 1,
  },
  messages: {
    sent: 96,
    failed: 3,
    byType: [
      { label: "Registered (MSG-1)", count: 38 },
      { label: "Decided (MSG-2)", count: 21 },
      { label: "Closed (MSG-3)", count: 17 },
      { label: "One-time codes", count: 23 },
    ],
  },
  areas: [
    { name: "Galle", vehicles: 301, hasOfficer: true },
    { name: "Matara", vehicles: 188, hasOfficer: true },
    { name: "Hambantota", vehicles: 123, hasOfficer: false },
  ],
  masterData: {
    people: 1204,
    vehicles: 612,
    permits: 598,
    routesAndStands: 58,
    categories: 14,
    vehiclesWithoutPermit: 14,
  },
  complaints: {
    perDay: [
      2, 3, 2, 4, 5, 3, 4, 5, 3, 2, 4, 5, 3, 4, 6, 3, 4, 6, 5, 3, 5, 7, 4, 5, 3, 6, 4, 4, 2, 2,
    ],
    byArea: [
      { label: "Galle", count: 51 },
      { label: "Matara", count: 38 },
      { label: "Hambantota", count: 29 },
    ],
    byStatus: [
      { label: "Closed", count: 54 },
      { label: "Forwarded", count: 21 },
      { label: "Under review", count: 17 },
      { label: "Awaiting implementation", count: 12 },
      { label: "Rejected", count: 6 },
      { label: "Done, awaiting approval", count: 5 },
      { label: "Escalated", count: 3 },
    ],
    overdue: 6,
  },
  timeTargets: [
    { severity: "Critical", forwardDays: 0, decideDays: 1, closeDays: 3 },
    { severity: "High", forwardDays: 1, decideDays: 3, closeDays: 7 },
    { severity: "Medium", forwardDays: 2, decideDays: 7, closeDays: 14 },
    { severity: "Low", forwardDays: 3, decideDays: 14, closeDays: 30 },
  ],
  settings: { ratingFormulaVersion: 1, aiTimeoutSeconds: 30 },
};
