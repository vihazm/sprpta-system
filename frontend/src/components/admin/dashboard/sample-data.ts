import type { SampleDashboardData } from "./types";

// Sample figures for the two tiles whose modules do not exist yet: the policy library (AI) and message delivery
// (SMS and email). Replace each with real figures when its module is built.
export const adminDashboardSample: SampleDashboardData = {
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
};
