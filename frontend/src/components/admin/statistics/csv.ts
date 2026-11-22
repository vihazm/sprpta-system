import type { Statistics, Stage } from "./api";

// The export of the Statistics and reports page: the figures on screen, as CSV. Like the page, it holds counts and
// days only, so nothing personal leaves the system.

function cell(value: string | number | null) {
  const text = value === null ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

const line = (values: (string | number | null)[]) => values.map(cell).join(",");

export function statisticsCsv(stats: Statistics, filters: string[], labels: { status: (key: string) => string }) {
  const lines = [line(["SPRPTA statistics and reports (personal data masked)"]), line(["Filters", ...filters]), ""];

  lines.push(line(["Measure", "Group", "Complaints"]));
  lines.push(line(["Total", "Registered complaints", stats.total]));
  const groups: [string, { key: string; count: number }[], (key: string) => string][] = [
    ["Status", stats.byStatus, labels.status],
    ["Area", stats.byArea, String],
    ["Category", stats.byCategory, String],
    ["Severity", stats.bySeverity, String],
    ["Medium", stats.byMedium, String],
    ["Month", stats.byMonth, String],
  ];
  for (const [measure, rows, label] of groups) {
    for (const row of rows) lines.push(line([measure, label(row.key), row.count]));
  }
  lines.push(line(["Overdue now", "Past decide-by", stats.overdue.awaitingDecision]));
  lines.push(line(["Overdue now", "Past close-by", stats.overdue.awaitingClose]));
  lines.push("");

  lines.push(line(["Time target", "Severity", "Target days", "Finished", "On time", "Average days"]));
  for (const row of stats.timeTargets) {
    for (const [stage, s] of [["Forward by", row.forward], ["Decide by", row.decide], ["Close by", row.close]] as [string, Stage][]) {
      lines.push(line([stage, row.severity, s.targetDays, s.finished, s.onTime, s.averageDays]));
    }
  }
  return lines.join("\r\n");
}

/** Hands the text to the browser as a file to save. The byte order mark lets Excel read Sinhala and Tamil names. */
export function download(text: string, fileName: string) {
  const url = URL.createObjectURL(new Blob(["﻿", text], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}
