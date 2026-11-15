import type { L1DashboardData } from "./types";

// Sample figures so the dashboard can be reviewed before the complaints module exists.
// Replace this with a fetch when the API does.
export const l1DashboardSample: L1DashboardData = {
  sources: [
    { label: "WhatsApp", count: 46 },
    { label: "Email", count: 31 },
    { label: "SMS", count: 28 },
    { label: "Letter", count: 19 },
    { label: "Phone call", count: 10 },
    { label: "Walk-in", count: 8 },
  ],
  busiestThisWeek: { medium: "WhatsApp", count: 14, total: 38 },
  lookup: {
    query: "NB-4521",
    rows: [
      { label: "Transport", value: "Bus" },
      { label: "Route", value: "350 · Galle to Matara" },
      { label: "Permit no.", value: "P/GL/0231 · valid" },
      { label: "Owner", value: "K. Silva" },
      { label: "Registered area", value: "Galle" },
      { label: "Past complaints", value: "3 on record" },
    ],
  },
  areas: [
    { name: "Galle", count: 58, hasOfficer: true },
    { name: "Matara", count: 41, hasOfficer: true },
    { name: "Hambantota", count: 32, hasOfficer: false },
  ],
  transport: { bus: 118, trishaw: 24 },
  severity: [
    { severity: "critical", count: 6 },
    { severity: "high", count: 29 },
    { severity: "medium", count: 71 },
    { severity: "low", count: 36 },
  ],
  forwarded: [
    { ref: "C-2026-00417", severity: "critical", title: "Reckless overtaking on Galle road", area: "Galle", when: "10 min ago", message: "sent" },
    { ref: "C-2026-00414", severity: "high", title: "Trishaw refused to use the meter", area: "Matara", when: "1 h ago", message: "sent" },
    { ref: "C-2026-00411", severity: "medium", title: "Bus skipped scheduled stops", area: "Matara", when: "2 h ago", message: "none" },
    { ref: "C-2026-00410", severity: "low", title: "Dirty waiting area at the stand", area: "Galle", when: "3 h ago", message: "failed" },
  ],
};
