import type { L1DashboardData } from "./types";

// Sample figures so the dashboard can be reviewed before the complaints module exists.
// Replace this with a fetch when the API does.
export const l1DashboardSample: L1DashboardData = {
  day: { entered: 7, forwarded: 5, stillOpen: 2, thisWeek: 38, thisMonth: 142 },
  draft: {
    name: "K. Wijesinghe",
    contact: "077 123 4567",
    received: "Today · 11 Nov 2026, 07:42",
    medium: "SMS",
    transport: "Bus",
    vehicle: "NB-4521",
    about: "Driver",
    route: "Route 350 · Galle to Matara",
    area: "Galle",
    lookup: { permit: "P/GL/0231", owner: "K. Silva", pastComplaints: 3 },
    subject: "Conductor was rude to an elderly passenger",
    category: "Staff behaviour",
    description:
      "The complainant says the conductor shouted at an elderly woman at Galle stand for being slow to board, and refused to help with her bag.",
    severity: "medium",
    attachments: ["whatsapp-message.png · 240 kB", "voice-note.m4a · 1.1 MB"],
    duplicate: { ref: "C-2026-00397", summary: "rude conductor, Route 350, 3 days ago", match: 88 },
  },
  queues: [
    { kind: "portal", title: "Portal submissions", note: "Awaiting your check", count: 4 },
    { kind: "drafts", title: "Drafts", note: "Started, no reference yet", count: 3 },
    { kind: "incomplete", title: "Incomplete", note: "Details missing, clock paused", count: 5 },
    { kind: "duplicates", title: "Possible duplicates", note: "Compare before forwarding", count: 2 },
  ],
  waiting: [
    { ref: "C-2026-00401", title: "Staff misconduct at Galle stand", status: "Draft", age: "2 d" },
    { ref: "C-2026-00406", title: "Trishaw driver refused a hire", status: "Incomplete", age: "1 d" },
    { ref: "C-2026-00409", title: "Reckless driving near Weligama", status: "Incomplete", age: "1 d" },
    { ref: "C-2026-00412", title: "Bus left stand before time", status: "Possible duplicate", age: "3 h" },
    { ref: "C-2026-00415", title: "Overcharging on fare", status: "Incomplete", age: "2 h" },
    { ref: null, title: "Rude behaviour by conductor", status: "Draft", age: "20 m" },
  ],
  portal: [
    { title: "Bus skipped scheduled stops", meta: "M. Perera · NB-3310 · 12 min ago" },
    { title: "Trishaw driver refused the meter", meta: "S. Fernando · TW-8827 · 38 min ago" },
    { title: "Conductor used abusive language", meta: "A. Kumari · NB-2204 · 1 h ago" },
    { title: "Overloaded bus on Route 349", meta: "R. Jayasinghe · NB-5105 · 2 h ago" },
  ],
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
