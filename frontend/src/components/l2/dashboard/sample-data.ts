import type { L2DashboardData } from "./types";

// Sample figures so the dashboard can be reviewed before the complaints module exists.
// Replace this with a fetch when the API does.
export const l2DashboardSample: L2DashboardData = {
  day: { arrived: 4, decided: 3 },
  month: { closed: 64, received: 84, open: 18, overdue: 1 },
  openStages: 4,
  caseToReview: {
    ref: "C-2026-00417",
    severity: "critical",
    title: "Reckless overtaking on Galle road",
    forwardedBy: "Nadeesha K. (Level 1)",
    forwardedAgo: "10 minutes ago",
    decideWithin: "1 day",
    dueIn: "5 h",
    facts: [
      { label: "Complainant", value: "K. Wijesinghe" },
      { label: "Medium", value: "WhatsApp" },
      { label: "Vehicle", value: "NB-4521 · Bus · Route 350" },
      { label: "Complaint about", value: "Driver" },
      { label: "Permit", value: "P/GL/0231 · valid" },
      { label: "Past complaints", value: "3 on record", accent: true },
      { label: "Contact on record", value: "SMS, messages will be sent" },
      { label: "Forwarded", value: "On time, same day" },
    ],
    story:
      "The bus overtook on a blind bend near Galle fort and nearly hit a trishaw. The complainant sent a photo by WhatsApp.",
    attachments: ["photo-bend.jpg · 1.4 MB", "whatsapp-message.png · 240 kB"],
    ai: {
      readyIn: "4 s",
      suggestion:
        "a written warning to the conductor and a 3-day suspension, because a similar complaint was substantiated 4 months ago and this case involves a safety risk to other road users.",
      clauses: ["Conduct Policy §4.2", "Passenger Charter §7", "Disciplinary Rules §11.3"],
    },
    earlier: [
      { ref: "C-2026-00288", title: "Rude behaviour to a passenger", outcome: "Warning", when: "4 mo ago" },
      { ref: "C-2026-00214", title: "Fare overcharge", outcome: "Fine", when: "9 mo ago" },
      { ref: "C-2026-00131", title: "Late departure from stand", outcome: "No action", when: "1 yr ago" },
    ],
  },
  stages: [
    { kind: "forwarded", label: "Forwarded, not opened", count: 3 },
    { kind: "review", label: "Under review", count: 7 },
    { kind: "implementation", label: "Awaiting implementation", count: 6 },
    { kind: "approval", label: "Done, awaiting approval", count: 3 },
    { kind: "escalated", label: "Escalated to Level 3", count: 2 },
  ],
  urgent: [
    { ref: "C-2026-00417", title: "Reckless overtaking on Galle road", severity: "critical", due: "Due in 5 h", overdue: false },
    { ref: "C-2026-00405", title: "Assault allegation at Galle stand", severity: "critical", due: "Overdue by 3 h", overdue: true },
    { ref: "C-2026-00398", title: "Overloading on Route 350, evening", severity: "high", due: "Due in 1 d", overdue: false },
    { ref: "C-2026-00392", title: "Refused to carry an elderly passenger", severity: "high", due: "Due in 2 d", overdue: false },
    { ref: "C-2026-00385", title: "Trishaw fare overcharge", severity: "medium", due: "Due in 6 d", overdue: false },
    { ref: "C-2026-00380", title: "Dirty waiting area at the stand", severity: "low", due: "Due in 12 d", overdue: false },
    { ref: "C-2026-00377", title: "Conductor refused a student concession", severity: "low", due: "Due in 14 d", overdue: false },
  ],
  urgentSolved: { solved: 9, total: 11 },
  averageDays: { actual: 4.1, target: 5 },
  approvals: [
    {
      ref: "C-2026-00376",
      action: "Written warning",
      doneBy: "Kamal S.",
      when: "Stand supervisor, Galle · 1 h ago",
      note: "Warning letter handed over and acknowledged by the conductor.",
    },
    {
      ref: "C-2026-00371",
      action: "Fine of Rs. 5,000",
      doneBy: "Priya W.",
      when: "Revenue section · 3 h ago",
      note: "Fine collected, receipt no. 4417 filed.",
    },
    {
      ref: "C-2026-00366",
      action: "7-day suspension",
      doneBy: "Ruwan T.",
      when: "Galle depot supervisor · yesterday",
      note: "Suspension served from 28 Oct to 3 Nov.",
    },
  ],
  moreWithStaff: 6,
  ages: [
    { label: "0 to 2 days", count: 7, color: "#1f9d63" },
    { label: "3 to 7 days", count: 6, color: "#d9a30b" },
    { label: "8 days or more", count: 5, color: "#b3112f" },
  ],
  overAgeNote: "5 cases are over 8 days old. Follow up on them.",
  messages: [
    { ref: "C-2026-00416", text: "Decision message sent: solution stated", time: "09:31", failed: false },
    { ref: "C-2026-00410", text: "Decision message failed. The case is not blocked.", time: "08:55", failed: true },
    { ref: "C-2026-00406", text: "Closing thank-you message sent", time: "08:12", failed: false },
  ],
  recommendations: [
    { ref: "R-2026-0038", title: "Shaded benches at Matara bus stand", kind: "Improvement suggestion", status: "New" },
    { ref: "R-2026-0036", title: "Extra evening trips on Route 350", kind: "Improvement suggestion", status: "Under consideration" },
    { ref: "R-2026-0035", title: "Fare chart displayed inside trishaws", kind: "Improvement suggestion", status: "Acknowledged" },
    { ref: "R-2026-0034", title: "Conductor praised for helping a wheelchair user", kind: "Commendation", status: "Commendation verified" },
  ],
  escalated: [
    { ref: "C-2026-00330", title: "Legal action recommended against an operator", when: "3 d ago", reason: "Beyond the area officer's powers." },
    { ref: "C-2026-00341", title: "Permit holder disputes the finding", when: "2 d ago", reason: "Conflicting evidence from both sides." },
  ],
  targets: [
    { severity: "critical", forward: "Same day", decide: "1 day", close: "3 days" },
    { severity: "high", forward: "1 day", decide: "3 days", close: "7 days" },
    { severity: "medium", forward: "2 days", decide: "7 days", close: "14 days" },
    { severity: "low", forward: "3 days", decide: "14 days", close: "30 days" },
  ],
  closed: [
    { ref: "C-2026-00388", title: "Bus skipped scheduled stops", outcome: "Warning", when: "closed 08:40" },
    { ref: "C-2026-00383", title: "Driver used phone while driving", outcome: "Suspension", when: "closed yesterday" },
    { ref: "C-2026-00377", title: "Refused to use the meter", outcome: "Fine", when: "closed yesterday" },
    { ref: "C-2026-00370", title: "Conductor shouted at a student", outcome: "Warning", when: "closed 2 d ago" },
  ],
};
